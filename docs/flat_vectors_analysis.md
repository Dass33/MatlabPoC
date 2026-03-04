# Flat Vectors Performance Analysis

**Scope**: Estimate the performance gain from replacing `Vec<Vec<f64>>` (2D jagged vectors) with
flat `Vec<f64>` (row-major, `index = t * nx + x`) across the Rust NSM algorithm.

---

## Current state: where `Vec<Vec<T>>` is used

The central kymograph matrix `c[t][x]` (dimensions `Nt × Nx`) is represented as `Vec<Vec<f64>>`
and flows through every major module.

| File | Allocations (per kymograph) | Notes |
|------|-----------------------------|-------|
| `tiff_loader.rs:98` | `Nt` | `flat.chunks(nx).map(row.to_vec())` fragments immediately |
| `preprocess.rs` | `5 × Nt + Nx` | `i0`, `i_smooth`, `c1`, `c1_col` (transposed → `Nx` rows), `c` |
| `detection.rs` | `3–4 × Nt` | `thresholded`, `local_min`, `local_max`, `local_opt` (bool masks) |
| `render.rs` | `Nt` + 1 flat copy | `c[t][x]` loop + extra `flat` copy for vmin/vmax |
| `linking.rs` | `Ns + Nt` per frame-pair | cost matrix (small, `ns × nt` spots); less critical |

For a representative kymograph (`Nt = 1 000`, `Nx = 512`):

- **Total heap allocations**: ≈ 8 500 per sweep (vs. ~10 with flat vectors)
- **Matrix size**: 1 000 × 512 × 8 B = **4.1 MB** per `Vec<Vec<f64>>`

---

## Identified waste: unnecessary copies

Three hot paths flatten 2D data back into a contiguous buffer just to do a simple pass over all
values. With flat input this copy is entirely free.

### 1. TIFF loader — `tiff_loader.rs:98`

```rust
// Decoder already produces a contiguous flat Vec<f64>:
let flat: Vec<f64> = match result { … };
// Then immediately re-fragments it:
let im: Vec<Vec<f64>> = flat.chunks(nx).map(|row| row.to_vec()).collect();
```

This performs one redundant full copy of the image data and creates `Nt` heap allocations just to
throw away the perfectly good flat buffer. With flat vectors the decoder output is used as-is.

### 2. Detection noise estimation — `detection.rs:21`

```rust
let flat: Vec<f64> = c.iter().flat_map(|row| row.iter().copied()).collect();
let (sigma, med) = noise_stats(&flat);
```

A 4.1 MB copy of the entire contrast matrix is made solely to obtain a contiguous slice. With a
flat input `c`, `noise_stats(c)` is called directly.

### 3. Render vmin/vmax — `render.rs:30`

```rust
let flat: Vec<f64> = c.iter().flat_map(|r| r.iter().copied()).collect();
let vmin = flat.iter().cloned().fold(f64::INFINITY, f64::min);
let vmax = flat.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
```

Another 4.1 MB copy to compute two scalars. With flat input: one inline fold over the slice.

**These three copies alone account for ~12 MB of unnecessary data movement per kymograph sweep.**
At a memory bandwidth of 20 GB/s, eliminating them saves ~0.6 ms/file in pure memory traffic (
negligible in isolation but it also evicts hot working-set data from L3 cache).

---

## Main cache problem: the transpose in `preprocess.rs`

`remove_background` must divide each column by its temporal moving median, so it transposes the
matrix first:

```rust
// c1 is [Nt × Nx] row-major
let mut c1_col: Vec<Vec<f64>> = vec![vec![0.0f64; nt]; nx];  // Nx allocations of size Nt
for t in 0..nt {
    for x in 0..nx {
        c1_col[x][t] = c1[t][x];   // ← writes to Nx different heap buffers per t
    }
}
```

**Read side** (`c1[t][x]`): sequential — cache-friendly ✓
**Write side** (`c1_col[x][t]`): for each `t`, jumps across `Nx = 512` separate allocations.
Each allocation is `Nt × 8 = 8 000 B`. Working set of `c1_col` = 512 × 8 KB = **4 MB** — fits in
L3 (typically 6–32 MB) but not L2 (typically 256–512 KB), so every write during the inner `x`
loop is an L2 miss after the first pass.

**With flat vectors** (`c1_col[x * nt + t]`):

```rust
let mut c1_col = vec![0.0f64; nx * nt];
for t in 0..nt {
    for x in 0..nx {
        c1_col[x * nt + t] = c1[t * nx + x];   // strided write, sequential read
    }
}
```

- Read side: perfectly sequential (inner x loop, stride 1) ✓
- Write side: stride = `Nt = 1 000` (8 000 B) — still strided, but:
  - **No pointer indirection**: no extra load of `c1_col[x]` pointer before the store
  - **Single TLB entry** for the entire 4 MB block vs. 512 separate TLB entries
  - Hardware prefetcher tracks simple constant strides; it does not track pointer-chased targets

On modern microarchitectures (AMD Zen4 as used in production) strided stores to a contiguous block
are significantly better than random stores across hundreds of allocations. Expected improvement:
**20–35% on the `remove_background` function**.

---

## Inner loop pointer indirection

Every access to `c[t][x]` in the 2D representation is a two-pointer dereference:

```
Load  outer_ptr + t*24  → row_ptr   (inner Vec header)
Load  row_ptr + x*8     → f64 value
```

The outer vector of `Nt = 1 000` pointers occupies 8 KB (24 B × 1 000), which fits in L1 (32 KB).
After the first scan this array stays hot. However, the indirection still adds one extra load
instruction per element and prevents the compiler from freely vectorising loops that span multiple
rows, because the aliasing rules for `Vec<Vec<T>>` are more conservative.

With flat indexing (`c[t * nx + x]`) the access compiles to a single address computation and load.
LLVM can auto-vectorise the resulting pointer-arithmetic loops more freely.

Benefit in inner loops (detection masks, refinement centroid, trajectory iOC): **5–15%** speedup
in each of these functions.

---

## Allocation / deallocation overhead

Using `jemalloc` or glibc `ptmalloc` at ~100 ns per call:

```
8 500 allocs × 2 (free) × 100 ns ≈ 1.7 ms per kymograph × 30 files = 51 ms (single-thread)
```

On the 4-core production server (2.3 s wall, 13.6 s single-core equivalent for 30 files):
this is ~0.4% of single-thread time — small but not zero. More importantly, high allocation rates
fragment the heap, increasing subsequent allocation latency and worsening cache behaviour.

---

## Estimated performance gain by component

Assumptions: `Nt = 1 000`, `Nx = 512`, release build with LTO (`opt-level = 3`).

| Phase | % of single-thread time (est.) | Speedup from flat vectors | Net contribution |
|-------|--------------------------------|--------------------------|-----------------|
| TIFF load + `i0` copy | 5% | Eliminate 1 copy + 1 000 allocs → **30–50%** faster | ~1.5–2.5% |
| `preprocess` (move-mean + move-median) | 45% | Copy elim. + transpose + pointer chase → **15–25%** faster | ~7–11% |
| `detect` (threshold masks + local opt) | 25% | Copy elim. + bool-mask allocs + inner loop → **15–25%** faster | ~4–6% |
| `refine` + `gap_fill` + `trajectory` | 15% | Read-only `c[t][x]` access → **5–10%** faster | ~1–1.5% |
| `render` | 5% | Eliminate vmin/vmax copy + inner loop → **15–25%** faster | ~0.75–1.25% |
| `linking` (LAP cost matrices) | 5% | Small matrices, already nearly flat-allocated; minimal | ~0–1% |

**Total estimated speedup on single-thread time: 14–23%**

On the 4-core production server (`2.3 s` for 30 files):

| Scenario | Estimated wall time | Improvement |
|----------|---------------------|-------------|
| Current (`Vec<Vec<f64>>`) | 2.3 s | — |
| Conservative (14%) | ~2.0 s | −0.3 s |
| Moderate (18%) | ~1.9 s | −0.4 s |
| Optimistic (23%) | ~1.8 s | −0.5 s |

For **larger kymographs** (e.g. `Nt = 5 000`, `Nx = 1 024`), the total matrix size is ~40 MB,
L3 thrashing during the transpose becomes severe, and the gain scales up to **25–35%**.

---

## What flat vectors do NOT help

- `movmean_shrink` / `movmedian_shrink`: already operate on 1D `&[f64]` slices; cache-optimal
  regardless of outer representation.
- `sliding_window_min/max`: same — 1D deque, no 2D access.
- `spot_linking` / `tracklet_linking` LAP matrices: `ns`, `nt` are typically < 50 (sparse frames).
  The matrices fit entirely in L1/L2; flattening saves nothing measurable.
- Rayon parallelism: flat vs. 2D has no effect on the parallel-file outer loop.

---

## Implementation notes

The refactor requires:

1. **`RawData::im` type change**: `Vec<Vec<f64>>` → `Vec<f64>` + stored `nx`.
2. **All function signatures**: `c: &[Vec<f64>]` → `c: &[f64], nx: usize` (or a thin wrapper
   struct `KymoMatrix { data: Vec<f64>, nx: usize }`).
3. **All indexing sites**: `c[t][x]` → `c[t * nx + x]`.
4. **Transpose in `remove_background`**: already exists, just switch to flat arithmetic.
5. **`Vec<Vec<bool>>` masks in `detection.rs`**: same pattern, `mask[t * nx + x]`.
6. **`postprocess.rs` / `population.rs`** `Vec<Vec<f64>>` per-trajectory: these are short (track
   length × properties) and allocated/freed per trajectory — lower priority; keep as-is initially.

A `KymoMatrix` thin wrapper (zero-cost) would preserve ergonomics without changing all call sites
at once:

```rust
pub struct KymoMatrix {
    pub data: Vec<f64>,
    pub nt: usize,
    pub nx: usize,
}

impl KymoMatrix {
    #[inline(always)]
    pub fn get(&self, t: usize, x: usize) -> f64 {
        self.data[t * self.nx + x]
    }

    #[inline(always)]
    pub fn row(&self, t: usize) -> &[f64] {
        &self.data[t * self.nx..(t + 1) * self.nx]
    }
}
```

`row(t)` returns a `&[f64]` slice — all existing 1D functions (`movmean_shrink`,
`movmedian_shrink`, `sliding_window_min/max`) continue to work unchanged.

---

## Conclusion

Switching from `Vec<Vec<f64>>` to flat vectors addresses three distinct inefficiencies:

1. **Three unnecessary full-matrix copies** (TIFF loader, noise_stats, render vmin/vmax) —
   mechanically eliminable with zero algorithmic change.
2. **~8 500 heap allocations per kymograph** collapsed to ~10 — reduces allocator pressure and
   heap fragmentation.
3. **Cache-unfriendly transpose** in `remove_background` improved via elimination of pointer
   chasing and better TLB utilisation.

**Expected net reduction in end-to-end wall time: 14–23% on the production server**, rising to
25–35% on larger datasets. The refactor is purely mechanical — it does not affect numerical output
— and is straightforward to validate by running the existing fidelity check against the MATLAB
reference.
