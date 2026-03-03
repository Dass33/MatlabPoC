# Rust Pipeline — Production Readiness Recommendations

## Must Fix Before Trusting Results

### 1. Investigate the N discrepancy (+6.6 frames/track)

Rust tracks are consistently ~6.6 frames longer than MATLAB tracks. This affects iOC (1.2% error)
and D (3.0% error) because the dip integration and diffusivity estimator both depend on track length.

Likely cause: the boundary walk in `analyze_minima` (`trajectory.rs`) finds slightly wider
dip boundaries than MATLAB's `analyzeMinimas.m`. The left/right walk stops at the first pixel
that exceeds the threshold — a one-pixel difference at the boundary shifts the sub-pixel
interpolation and can change how gap-filling places new spots.

**To investigate**: add a debug mode that prints per-track frame counts for both Rust and MATLAB
on the same input, then diff the tracks that diverge.

---

### 2. Kymograph naming in sweep mode

In `main.rs:123` the kymograph is written as `{file_stem}.png` regardless of sweep index.
With a single sweep (the common case) this is fine. With multiple sweeps (parameter grid),
each sweep overwrites the same file and only the last sweep's kymograph survives.

Fix: include the sweep legend in the filename, e.g. `{file_stem}_Wx15_Wt50.png`.

---

## Should Do Before Wider Use

### 3. Unit tests for core numerical functions

Zero tests exist. The most critical functions — `movmedian_shrink`, `movmean_shrink`,
`analyze_minima`, and the LAP cost matrix augmentation — have only been verified by
end-to-end comparison against MATLAB. A silent regression in any of them would be
impossible to catch without tests.

Minimum test set:
- `movmedian_shrink`: compare against a known sequence at window edges and in the middle
- `analyze_minima`: known dip shape, verify iOC and base_length
- `match_pairs_lap`: 3x3 cost matrix with known optimal assignment

### 4. Skip bad files instead of failing the whole job

If one TIFF in a batch is corrupt or missing its `.txt`, the entire job fails and no output
is written. The `?` on `file_result` in `main.rs:137` propagates the first file error upward.

Fix: log a warning and skip the file. This is especially important for batch jobs where
the user uploaded 30 files and one has a metadata issue.

### 5. Downgrade empty-sweep bail to a warning

`main.rs:147` calls `bail!()` when a sweep produces zero trajectories. This can happen
with a misconfigured `pfa` or wrong `peakSign`, and the user currently gets a failed job
with no partial output. A warning with a clear message ("no detections in sweep 1 — check
pfa and peakSign") and graceful continuation would be more useful.

---

## Nice to Have

### 6. Config range validation

The serde deserializer accepts any JSON number. A `pfa` of `0`, `1.5`, or a negative
`cutOffDistance` will produce silently wrong results. Add explicit range checks with clear
error messages after parsing.

---

## IO and Rendering Performance (separate topic — see notes below)

The pipeline is already fast enough for production (2.3s / 30 files on the server), but
there are two structural inefficiencies worth knowing about for future work.
See `docs/io_analysis.md` for details.
