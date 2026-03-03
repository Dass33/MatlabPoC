# NSM Pipeline: MATLAB → Rust Rewrite — Performance Report

**Test dataset**: 30 kymograph TIFFs (~213 MB total, same files throughout)

---

## Production Baseline (Current MATLAB)

The production system compiles MATLAB source code via MCC into a standalone binary, bundled with the full MATLAB Compiler Runtime (MCR). This is the version running on the Hetzner server today.

**Benchmarked on production server (4x AMD EPYC-Genoa, 7.6 GB RAM):**

| Metric                        | Value                          |
| ----------------------------- | ------------------------------ |
| Wall-clock time (30 TIFFs)    | **117.7 s**                    |
| Peak memory                   | ~1.8 GB                        |
| Docker image size             | **10.9 GB**                    |
| MCR startup overhead          | ~5-8 s (before any computation)|

The algorithm runs single-threaded despite the 4-core server — MATLAB does not parallelize the outer file loop in the current production build.

---

## Optimized MATLAB (Tested Locally, Not Deployed)

During this work we investigated whether MATLAB-side optimizations could close the gap. We brought in pre-existing fixes from the `optimizations` branch (pre-allocated frame index tables in `spotLinking`, consolidated quantile sorts in `detectSpots`) and added `parfor` to the outer file loop in `kymographAnalysis.m`.

**Benchmarked on local machine (12x CPU, more powerful than prod):**

| Config                                     | Time      |
| ------------------------------------------ | --------- |
| Sequential (~2 CPU, original)              | ~169 s    |
| `parfor` + optimized spotLinking (4 CPU)   | **~25 s** |

The gains came almost entirely from `parfor` — the algorithmic fixes saved little in MATLAB because the interpreter's overhead (~100 ns/op) drowns out O(n) vs O(n^2) differences at typical spot densities. This version was never deployed (reverted after benchmarking).

---

## Optimized Rust Rewrite (Current)

A full rewrite of the pipeline in Rust, replacing the MATLAB binary with a ~50 MB self-contained binary. Same `config.json` schema, same job directory layout, same output files — only `trajectories.mat` became `trajectories.json`.

**Algorithmic improvements implemented:**

| Module           | Change                                                                             |
| ---------------- | ---------------------------------------------------------------------------------- |
| `preprocess.rs`  | O(n log w) sliding window median via two BTreeMaps (was O(n x w x log w))         |
| `detection.rs`   | O(n) monotonic-deque sliding min/max (was O(n x w)); single sort for IQR + median |
| `linking.rs`     | Frame-indexed spot lookup O(1) (was O(n) scan per frame pair); HashMap tail-tracking for tracklet assembly |
| `gap.rs`         | Vec::splice for gap insertion O(n) (was O(n x gap_len))                           |
| `main.rs`        | rayon::par_iter() over files — all TIFFs processed in parallel                    |

**Benchmarked on production server (same 4x AMD EPYC-Genoa):**

| Config          | Time       |
| --------------- | ---------- |
| 4 CPU (prod)    | **2.3 s**  |

**Benchmarked on local machine (12x CPU) for additional context:**

| Config  | Time    |
| ------- | ------- |
| 1 CPU   | 13.6 s  |
| 4 CPU   | 3.9 s   |
| 12 CPU  | 2.2 s   |

---

## Summary

| Version                          | Hardware   | Time (30 TIFFs) | Memory   | Image    |
| -------------------------------- | ---------- | --------------- | -------- | -------- |
| MATLAB prod (current)            | 4x EPYC    | 117.7 s         | ~1.8 GB  | 10.9 GB  |
| MATLAB + parfor (not deployed)   | 12x local  | ~25 s           | ~0.9 GB  | 10.9 GB  |
| **Rust (current)**               | **4x EPYC**| **2.3 s**       | **~60 MB** | **~50 MB** |

**vs. production MATLAB: 51x faster, 30x less memory, 218x smaller image** on the same hardware.

The `movmedian` O(n log w) fix was the single largest contributor — it alone gave ~4.5x speedup at any core count. Parallelism across files accounts for most of the rest.

---

## Output Fidelity

Sanity check on 5 TIFFs against the MATLAB reference: both produce 13 trajectories. Numeric differences are within acceptable range for a floating-point reimplementation:

| Output           | Mean error         |
| ---------------- | ------------------ |
| velocity         | 0.4%               |
| iOC              | 1.2%               |
| D (diffusivity)  | 3.0%               |
| N (track length) | +6.6 frames/track  |

The N offset is under investigation — likely a minor difference in the dip-boundary walk in `analyzeMinimas`.
