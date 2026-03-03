# IO and Rendering Performance Analysis

## Is IO the bottleneck?

Not on its own. Pure disk reads for 30 × 7 MB TIFFs at SSD speeds (~500 MB/s) would take
~0.4 s. The observed 2.3 s wall-clock means CPU (preprocess, detect, link) accounts for
most of the runtime. The files ARE read in parallel because rayon submits all 30 tasks at
once and the OS overlaps disk reads across threads.

However, there are two places where we do sequential work that doesn't need to be:

---

## 1. Double allocation in TIFF loading (`tiff_loader.rs:decode_tiff`)

Current code:
```rust
let result = decoder.read_image()?;          // decoded into flat Vec<u16>
let flat: Vec<f64> = match result {
    DecodingResult::U16(v) => v.into_iter().map(|x| x as f64).collect(),  // second flat Vec
    ...
};
let im: Vec<Vec<f64>> = flat.chunks(nx).map(|row| row.to_vec()).collect(); // Nt row copies
```

For a 7 MB TIFF with U16 pixels (Nt=300, Nx=1024):
- Step 1: ~2 MB flat `Vec<u16>` from the tiff crate
- Step 2: ~8 MB flat `Vec<f64>` from the type conversion (the u16 vec is still alive)
- Step 3: ~8 MB again split into 300 separate row allocations (the flat f64 vec is dropped)
- Peak: ~18 MB held simultaneously for a single 7 MB file

**Fix**: convert and chunk in one pass — skip the intermediate flat `Vec<f64>`:
```rust
let im: Vec<Vec<f64>> = match result {
    DecodingResult::U16(v) => v.chunks(nx).map(|row| row.iter().map(|&x| x as f64).collect()).collect(),
    ...
};
```
This holds only ~10 MB at peak (u16 source + one row at a time). The improvement is modest
(less GC pressure) but eliminates a full redundant copy of every TIFF.

---

## 2. Kymograph rendering draws pixel-by-pixel (`render.rs`)

Current code draws Nt × Nx individual rectangles through the plotters API:
```rust
for t in 0..nt {
    for x in 0..nx {
        root.draw(&Rectangle::new([...], ShapeStyle...))?;  // ~300,000 calls
    }
}
```

Each `draw` call has overhead for coordinate transformation, style lookup, and bounds
checking. For a 300×1024 image that is 307,200 API calls before PNG encoding even starts.

There is also an unnecessary heap allocation for vmin/vmax:
```rust
let flat: Vec<f64> = c.iter().flat_map(|r| r.iter().copied()).collect();  // full copy
let vmin = flat.iter()...
let vmax = flat.iter()...
```

**Fix**: build a raw RGB pixel buffer directly, then encode as PNG with the `image` crate:
```rust
// No plotters needed for the heatmap
let vmin = c.iter().flat_map(|r| r.iter()).cloned().fold(f64::INFINITY, f64::min);
let vmax = c.iter().flat_map(|r| r.iter()).cloned().fold(f64::NEG_INFINITY, f64::max);

let mut buf = vec![0u8; nt * nx * 3];
for t in 0..nt {
    for x in 0..nx {
        let val = (c[t][x] - vmin) / range;
        let (r, g, b) = viridis(val);
        let idx = (t * nx + x) * 3;
        buf[idx] = r; buf[idx+1] = g; buf[idx+2] = b;
    }
}
image::RgbImage::from_raw(nx as u32, nt as u32, buf)
    .unwrap()
    .save(output_path)?;
```

This replaces 300K plotters calls with one contiguous buffer fill and one PNG encode.
Track overlays still need plotters or manual Bresenham line drawing on the buffer.

---

## 3. TODO: Structural: Vec<Vec<f64>> memory layout

Every matrix in the pipeline is `Vec<Vec<f64>>` — each row is a separate heap allocation.
Accessing temporal columns (e.g., in the movmedian pass) requires jumping between 300
separate allocations, causing cache misses.

The column-major transpose we added in `preprocess.rs` (`c1_col`) mitigates this for the
movmedian step, but it adds a full extra copy of the data.

**Bigger fix**: switch to a flat `Vec<f64>` with stride-based 2D indexing (or `ndarray::Array2`)
throughout the pipeline. This would:
- Reduce per-matrix allocations from Nt to 1
- Make temporal column access cache-friendly without needing a transpose copy
- Enable SIMD-friendly memory layout for future vectorization

This is a significant refactor touching every module but would likely give another
2-3× speedup on memory-bandwidth-limited workloads (preprocess and detection).

---

## Summary

| Issue | Location | Effort | Expected gain |
| ----- | -------- | ------ | ------------- |
| Double allocation in TIFF decode | `tiff_loader.rs` | Low | Modest (less memory pressure) |
| Plotters per-pixel draw calls | `render.rs` | Low | Meaningful (rendering is ~20% of runtime) |
| Vec<Vec<f64>> layout | All modules | High | 2-3× on preprocessing |
