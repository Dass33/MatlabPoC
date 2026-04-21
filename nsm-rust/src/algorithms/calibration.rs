/// Port of std_modified.m, iOCcalibration.m / algorithms/calibration.py

use crate::models::{CalibrationResult, Collection};

/// Robust standard deviation with iterative 3σ clipping.
/// Returns (std, mean, selected_mask).
///
/// fun_mean=false: zero-mean mode (RMS std)
/// fun_mean=true:  standard mean + std (most common)
/// fun_stabil=true: iteratively tighten by removing > 3σ outliers
pub fn std_modified(x: &[f64], fun_mean: bool, fun_stabil: bool) -> (f64, f64, Vec<bool>) {
    let mut selected: Vec<bool> = x.iter().map(|v| v.is_finite()).collect();
    let count_selected = |s: &[bool]| s.iter().filter(|&&b| b).count();

    let (mut std_v, mut mean_v) = if !fun_mean {
        // Zero-mean RMS
        let n = count_selected(&selected).max(1);
        let s = (x.iter().zip(&selected)
            .filter(|(_, &k)| k)
            .map(|(&v, _)| v * v)
            .sum::<f64>()
            / (n - 1).max(1) as f64)
            .sqrt();
        (s, 0.0_f64)
    } else {
        let vals: Vec<f64> = x.iter().zip(&selected).filter(|(_, &k)| k).map(|(&v, _)| v).collect();
        let m = nanmean_vec(&vals);
        let s = nanstd_ddof1_vec(&vals, m);
        (s, m)
    };

    if fun_stabil && count_selected(&selected) > 1 {
        loop {
            let prev_count = count_selected(&selected);
            selected = if !fun_mean {
                x.iter().map(|&v| v.abs() < 3.0 * std_v).collect()
            } else {
                x.iter().map(|&v| (v - mean_v).abs() < 3.0 * std_v).collect()
            };

            let new_count = count_selected(&selected);
            if new_count >= prev_count {
                break; // converged
            }

            if !fun_mean {
                let n = new_count.max(1);
                std_v = (x.iter().zip(&selected)
                    .filter(|(_, &k)| k)
                    .map(|(&v, _)| v * v)
                    .sum::<f64>()
                    / (n - 1).max(1) as f64)
                    .sqrt();
            } else {
                let vals: Vec<f64> = x.iter().zip(&selected).filter(|(_, &k)| k).map(|(&v, _)| v).collect();
                mean_v = nanmean_vec(&vals);
                std_v  = nanstd_ddof1_vec(&vals, mean_v);
            }
        }
    }

    (std_v, mean_v, selected)
}

/// Core iOC calibration algorithm.
/// Iteratively normalises iOC profiles across trajectories using spatial binning.
pub fn ioc_calibration_core(
    ioc_profiles: &[Vec<f64>],
    positions:    &[Vec<f64>],
    dx:           f64,
    threshold:    f64,
) -> CalibrationResult {
    let n_traj = ioc_profiles.len();
    if n_traj == 0 {
        return CalibrationResult { x: vec![], a: vec![], a_std: vec![], a_n: vec![] };
    }

    let pos_start = positions.iter()
        .map(|p| p.iter().cloned().filter(|x| x.is_finite()).fold(f64::NEG_INFINITY, f64::max))
        .fold(f64::NEG_INFINITY, f64::max);
    let pos_end = positions.iter()
        .map(|p| p.iter().cloned().filter(|x| x.is_finite()).fold(f64::INFINITY, f64::min))
        .fold(f64::INFINITY, f64::min);

    // Build trajectory slices into concatenated arrays
    let mut slices: Vec<std::ops::Range<usize>> = Vec::with_capacity(n_traj);
    let mut a_start = 0;
    for p in positions {
        slices.push(a_start..a_start + p.len());
        a_start += p.len();
    }
    let total = a_start;

    let all_pos: Vec<f64> = positions.iter().flat_map(|p| p.iter().cloned()).collect();
    let all_ioc: Vec<f64> = ioc_profiles.iter().flat_map(|p| p.iter().cloned()).collect();

    // Bin centres
    let x_bins = arange(pos_start + dx / 2.0, pos_end - dx / 2.0 + 1.0, dx);
    let x_bins = if x_bins.is_empty() {
        vec![(pos_start + pos_end) / 2.0]
    } else {
        x_bins
    };
    let nb = x_bins.len();

    // Precompute bin membership for each bin
    let ind_x: Vec<Vec<usize>> = x_bins.iter()
        .map(|&xi| {
            (0..total)
                .filter(|&j| all_pos[j] >= xi - dx / 2.0 && all_pos[j] <= xi + dx / 2.0)
                .collect()
        })
        .collect();

    // Initial frame outlier mask
    let x_lo = x_bins[0];
    let x_hi = x_bins[nb - 1];
    let mut not_outlier_frame: Vec<bool> = all_pos.iter().map(|&p| p >= x_lo && p <= x_hi).collect();
    let mut not_outlier_frame0: Vec<bool> = not_outlier_frame.iter().map(|&b| !b).collect();

    let mut aint    = vec![1.0_f64; total];
    let mut ioc_norm = vec![1.0_f64; total];
    let mut a_vec    = vec![0.0_f64; nb];
    let mut a_old    = vec![f64::INFINITY; nb];
    let mut a_std_vec = vec![0.0_f64; nb];
    let mut a_n_vec   = vec![0.0_f64; nb];

    for _ in 0..100 {
        let converged_frames = not_outlier_frame == not_outlier_frame0;
        let converged_a = a_vec.iter().zip(&a_old).all(|(a, a0)| (a - a0).abs() <= threshold);
        if converged_frames && converged_a { break; }
        not_outlier_frame0 = not_outlier_frame.clone();
        a_old = a_vec.clone();

        // Normalise each trajectory by its mean iOC
        let y: Vec<f64> = all_ioc.iter().zip(&aint).map(|(ioc, ai)| ioc / ai).collect();
        for i in 0..n_traj {
            let sl = slices[i].clone();
            let valid_idx: Vec<usize> = sl.clone()
                .filter(|&j| not_outlier_frame[j])
                .collect();
            if valid_idx.is_empty() { continue; }
            let mean_ioc = nanmean(&valid_idx.iter().map(|&j| y[j]).collect::<Vec<_>>());
            if mean_ioc.is_finite() && mean_ioc.abs() > 1e-12 {
                for j in sl {
                    ioc_norm[j] = all_ioc[j] / mean_ioc;
                }
            }
        }

        // Outlier rejection on normalised iOC
        let in_frame_ioc_ratio: Vec<f64> = not_outlier_frame.iter()
            .enumerate()
            .filter(|(_, &k)| k)
            .map(|(j, _)| ioc_norm[j] / aint[j])
            .collect();
        let (_, _, sel_mask) = std_modified(&in_frame_ioc_ratio, true, true);

        // Map sel_mask back to the original frame indices
        let in_frame_indices: Vec<usize> = (0..total).filter(|&j| not_outlier_frame[j]).collect();
        for (local_i, global_j) in in_frame_indices.iter().enumerate() {
            not_outlier_frame[*global_j] = sel_mask.get(local_i).copied().unwrap_or(false);
        }

        // Compute per-bin statistics
        let mut a_new = vec![f64::NAN; nb];
        a_std_vec = vec![f64::NAN; nb];
        a_n_vec   = vec![0.0; nb];
        for (bi, ix) in ind_x.iter().enumerate() {
            let valid: Vec<f64> = ix.iter()
                .filter(|&&j| not_outlier_frame[j])
                .map(|&j| ioc_norm[j])
                .collect();
            if valid.is_empty() { continue; }
            a_new[bi]     = nanmean(&valid);
            a_std_vec[bi] = if valid.len() > 1 { nanstd_ddof1(&valid, a_new[bi]) } else { 0.0 };
            a_n_vec[bi]   = valid.len() as f64;
        }

        let a_mean = nanmean(&a_new.iter().filter(|x| x.is_finite()).cloned().collect::<Vec<_>>());
        a_vec = if a_mean.is_finite() && a_mean.abs() > 1e-12 {
            a_new.iter().map(|v| v / a_mean).collect()
        } else {
            a_new
        };

        // Interpolate Aint for all positions
        aint = interp_linear(&all_pos, &x_bins, &a_vec);
    }

    CalibrationResult {
        x:     x_bins,
        a:     a_vec,
        a_std: a_std_vec,
        a_n:   a_n_vec,
    }
}

/// Apply iOC calibration to a collection and return the updated one.
pub fn run_ioc_calibration(
    collection: &Collection,
    keep_mask: &[bool],
) -> anyhow::Result<(CalibrationResult, Collection)> {
    let kept_idx: Vec<usize> = keep_mask.iter().enumerate()
        .filter(|(_, &k)| k)
        .map(|(i, _)| i)
        .collect();

    let ioc_profiles: Vec<Vec<f64>> = kept_idx.iter().map(|&i| collection.ioc_profile[i].clone()).collect();
    let positions:    Vec<Vec<f64>> = kept_idx.iter().map(|&i| collection.position_refined[i].clone()).collect();

    let cal = ioc_calibration_core(&ioc_profiles, &positions, 1.0, 1e-3);

    // Update iOC, STDiOC, N for all trajectories
    let n = collection.len();
    let mut new_ioc     = collection.ioc.clone();
    let mut new_std_ioc = collection.std_ioc.clone();
    let mut new_n       = collection.n.clone();

    for i in 0..n {
        let pos_i = &collection.position_refined[i];
        let ioc_i = &collection.ioc_profile[i];
        let y: Vec<f64> = ioc_i.iter().zip(pos_i.iter())
            .map(|(&ioc, &pos)| ioc / interp_point(pos, &cal.x, &cal.a))
            .collect();
        let (std_v, mean_v, selected) = std_modified(&y, true, true);
        new_std_ioc[i] = std_v;
        new_ioc[i]     = mean_v;
        new_n[i]       = selected.iter().filter(|&&b| b).count() as f64;
    }

    let mut updated = collection.clone();
    updated.ioc     = new_ioc;
    updated.std_ioc = new_std_ioc;
    updated.n       = new_n;

    Ok((cal, updated))
}

// ── Numerical helpers ─────────────────────────────────────────────────────────

fn nanmean(v: &[f64]) -> f64 {
    let vals: Vec<f64> = v.iter().cloned().filter(|x| x.is_finite()).collect();
    if vals.is_empty() { return f64::NAN; }
    vals.iter().sum::<f64>() / vals.len() as f64
}

fn nanmean_vec(v: &[f64]) -> f64 { nanmean(v) }

fn nanstd_ddof1(v: &[f64], mean: f64) -> f64 {
    let n = v.iter().filter(|x| x.is_finite()).count();
    if n < 2 { return 1.0; }
    let sum_sq = v.iter().filter(|x| x.is_finite()).map(|x| (x - mean).powi(2)).sum::<f64>();
    (sum_sq / (n - 1) as f64).sqrt()
}

fn nanstd_ddof1_vec(v: &[f64], mean: f64) -> f64 { nanstd_ddof1(v, mean) }

fn arange(start: f64, stop: f64, step: f64) -> Vec<f64> {
    if step <= 0.0 || start >= stop { return vec![]; }
    let n = ((stop - start) / step).ceil() as usize;
    (0..n).map(|i| start + i as f64 * step).collect()
}

/// 1D linear interpolation, clamping at boundary values (like np.interp).
pub fn interp_linear(xq: &[f64], xp: &[f64], yp: &[f64]) -> Vec<f64> {
    xq.iter().map(|&x| interp_point(x, xp, yp)).collect()
}

pub fn interp_point(x: f64, xp: &[f64], yp: &[f64]) -> f64 {
    let n = xp.len();
    if n == 0 { return f64::NAN; }
    if n == 1 { return yp[0]; }
    if x <= xp[0]     { return yp[0]; }
    if x >= xp[n - 1] { return yp[n - 1]; }
    let i = xp.partition_point(|&v| v <= x).saturating_sub(1).min(n - 2);
    let t = (x - xp[i]) / (xp[i + 1] - xp[i]);
    yp[i] + t * (yp[i + 1] - yp[i])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_std_modified_basic() {
        let x = vec![1.0, 2.0, 1.5, 1.8, 100.0];
        let (std_v, mean_v, sel) = std_modified(&x, true, true);
        assert!(!sel[4], "outlier should be excluded");
        assert!(std_v > 0.0);
        assert!(mean_v.is_finite());
    }

    #[test]
    fn test_interp_linear_boundary() {
        let xp = vec![0.0, 1.0, 2.0];
        let yp = vec![0.0, 1.0, 4.0];
        assert!((interp_point(-1.0, &xp, &yp) - 0.0).abs() < 1e-10);
        assert!((interp_point(3.0,  &xp, &yp) - 4.0).abs() < 1e-10);
        assert!((interp_point(1.5,  &xp, &yp) - 2.5).abs() < 1e-10);
    }

    #[test]
    fn test_calibration_uniform_profiles() {
        // All profiles constant → A should be ~1.0 everywhere
        let ioc_profiles = vec![vec![1.0; 10], vec![1.0; 10]];
        let positions    = vec![
            (0..10).map(|i| i as f64).collect::<Vec<_>>(),
            (0..10).map(|i| i as f64).collect::<Vec<_>>(),
        ];
        let cal = ioc_calibration_core(&ioc_profiles, &positions, 1.0, 1e-3);
        for &a in &cal.a {
            if a.is_finite() {
                assert!((a - 1.0).abs() < 0.1, "A should be ~1 for uniform profiles, got {a}");
            }
        }
    }
}
