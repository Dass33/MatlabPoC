use crate::config::{OutlierFiltering, ThresholdValue};
use crate::trajectory::{std_modified, TrajectoryResult};

/// Postprocessed collection per sweep
#[derive(Debug, Clone)]
pub struct CollectionPostprocessed {
    pub sweep_legend: String,
    pub ioc: Vec<f64>,
    pub d: Vec<f64>,
    pub velocity: Vec<f64>,
    pub n: Vec<f64>,
    pub std_ioc: Vec<f64>,
    pub position_start: Vec<f64>,
    pub position_end: Vec<f64>,
    pub position_refined: Vec<Vec<f64>>,
    pub ioc_profile: Vec<Vec<f64>>,
}

impl CollectionPostprocessed {
    pub fn from_trajectory_results(results: &[TrajectoryResult], legend: &str) -> Self {
        CollectionPostprocessed {
            sweep_legend: legend.to_string(),
            ioc: results.iter().map(|r| r.ioc).collect(),
            d: results.iter().map(|r| r.d).collect(),
            velocity: results.iter().map(|r| r.velocity).collect(),
            n: results.iter().map(|r| r.n).collect(),
            std_ioc: results.iter().map(|r| r.std_ioc).collect(),
            position_start: results.iter().map(|r| r.position_start).collect(),
            position_end: results.iter().map(|r| r.position_end).collect(),
            position_refined: results.iter().map(|r| r.position_refined.clone()).collect(),
            ioc_profile: results.iter().map(|r| r.ioc_profile.clone()).collect(),
        }
    }

    pub fn len(&self) -> usize {
        self.ioc.len()
    }

    pub fn get_field(&self, name: &str) -> Option<Vec<f64>> {
        match name {
            "iOC" => Some(self.ioc.clone()),
            "D" => Some(self.d.clone()),
            "velocity" => Some(self.velocity.clone()),
            "N" => Some(self.n.clone()),
            "STDiOC" => Some(self.std_ioc.clone()),
            "positionStart" => Some(self.position_start.clone()),
            "positionEnd" => Some(self.position_end.clone()),
            _ => None,
        }
    }
}

/// Apply outlier filtering and optionally iOC calibration.
/// Returns (filtered_collection, calibrated_collection).
pub fn collection_postprocessing(
    collection: CollectionPostprocessed,
    outlier_filtering: &OutlierFiltering,
    ioc_calibration: &str,
) -> (CollectionPostprocessed, CollectionPostprocessed) {
    if ioc_calibration == "off" {
        let not_outlier = find_trajectory_outliers(&collection, outlier_filtering);
        let filtered = filter_collection(&collection, &not_outlier);
        (filtered, collection)
    } else {
        // Iterative iOC calibration + outlier filtering
        let n = collection.len();
        let mut calibrated = collection.clone();
        let mut not_outlier = vec![false; n];
        let mut not_outlier0 = vec![true; n];

        while not_outlier != not_outlier0 {
            not_outlier0 = not_outlier.clone();
            not_outlier = find_trajectory_outliers(&calibrated, outlier_filtering);

            // Run iOC calibration
            let cal_ioc_profiles: Vec<&Vec<f64>> = (0..n)
                .filter(|&i| not_outlier[i])
                .map(|i| &calibrated.ioc_profile[i])
                .collect();
            let cal_positions: Vec<&Vec<f64>> = (0..n)
                .filter(|&i| not_outlier[i])
                .map(|i| &calibrated.position_refined[i])
                .collect();

            if cal_ioc_profiles.is_empty() {
                break;
            }

            let calibration = ioc_calibration_fn(&cal_ioc_profiles, &cal_positions);

            // Recalculate iOC for all tracks
            for i in 0..n {
                let pos_refined = &collection.position_refined[i];
                let ioc_prof = &collection.ioc_profile[i];
                let a_int: Vec<f64> = pos_refined
                    .iter()
                    .map(|&p| interp1_clamped(&calibration.x, &calibration.a, p))
                    .collect();
                let y: Vec<f64> = ioc_prof
                    .iter()
                    .zip(a_int.iter())
                    .map(|(&ioc_v, &a)| if a.abs() > 1e-15 { ioc_v / a } else { ioc_v })
                    .collect();
                let (std_v, mean_v, sel) = std_modified(&y, true, true);
                calibrated.ioc[i] = mean_v;
                calibrated.std_ioc[i] = std_v;
                calibrated.n[i] = sel.iter().filter(|&&v| v).count() as f64;
            }
        }

        let filtered = filter_collection(&calibrated, &not_outlier);
        (filtered, calibrated)
    }
}

/// Returns a mask of non-outlier trajectories.
fn find_trajectory_outliers(
    collection: &CollectionPostprocessed,
    setting: &OutlierFiltering,
) -> Vec<bool> {
    let n = collection.len();
    if n == 0 {
        return vec![];
    }

    let ref_prop = setting
        .reference_property
        .as_str();
    let ref_vals = collection.get_field(ref_prop).unwrap_or_else(|| vec![f64::NAN; n]);

    // Initialize: all non-NaN
    let mut not_outlier: Vec<bool> = (0..n)
        .map(|i| {
            setting.filter_properties.iter().all(|fp| {
                collection
                    .get_field(fp)
                    .map(|v| v[i].is_finite())
                    .unwrap_or(false)
            })
        })
        .collect();

    let mut not_outlier0: Vec<bool> = not_outlier.iter().map(|&v| !v).collect();

    while not_outlier != not_outlier0 {
        not_outlier0 = not_outlier.clone();

        let mut per_prop_masks: Vec<Vec<bool>> = Vec::new();

        for (fp_idx, fp) in setting.filter_properties.iter().enumerate() {
            let vals = match collection.get_field(fp) {
                Some(v) => v,
                None => continue,
            };

            let (lower, upper) = compute_thresholds(
                &vals,
                &ref_vals,
                &not_outlier0,
                &setting.threshold_value[fp_idx],
                &setting.threshold_direction[fp_idx],
            );

            let mask: Vec<bool> = (0..n)
                .map(|i| vals[i] > lower[i] && vals[i] < upper[i])
                .collect();
            per_prop_masks.push(mask);
        }

        if per_prop_masks.is_empty() {
            break;
        }

        not_outlier = (0..n)
            .map(|i| per_prop_masks.iter().all(|m| m[i]))
            .collect();
    }

    not_outlier
}

fn compute_thresholds(
    vals: &[f64],
    ref_vals: &[f64],
    mask: &[bool],
    threshold_value: &ThresholdValue,
    threshold_direction: &str,
) -> (Vec<f64>, Vec<f64>) {
    let n = vals.len();
    let selected_vals: Vec<f64> = vals
        .iter()
        .zip(mask.iter())
        .filter(|(_, &m)| m)
        .map(|(&v, _)| v)
        .collect();

    match threshold_value {
        ThresholdValue::Named(name) if name == "3std" => {
            let mean = if selected_vals.is_empty() {
                0.0
            } else {
                selected_vals.iter().sum::<f64>() / selected_vals.len() as f64
            };
            let std = if selected_vals.len() > 1 {
                (selected_vals.iter().map(|&v| (v - mean).powi(2)).sum::<f64>()
                    / selected_vals.len() as f64)
                    .sqrt()
            } else {
                0.0
            };
            make_directional_thresholds(n, mean - 3.0 * std, mean + 3.0 * std, threshold_direction)
        }
        ThresholdValue::Named(name) if name == "3std_conditional" => {
            // Linear regression: vals ≈ a * ref_vals + b, then threshold on residuals
            let selected_ref: Vec<f64> = ref_vals
                .iter()
                .zip(mask.iter())
                .filter(|(_, &m)| m)
                .map(|(&v, _)| v)
                .collect();
            let (a, b) = linear_regression(&selected_ref, &selected_vals);
            let predicted: Vec<f64> = ref_vals.iter().map(|&r| a * r + b).collect();
            let residuals: Vec<f64> = vals
                .iter()
                .zip(mask.iter())
                .filter(|(_, &m)| m)
                .zip(predicted.iter().zip(mask.iter()).filter(|(_, &m)| m))
                .map(|((&v, _), (&pred, _))| if pred.abs() > 1e-15 { v / pred } else { v })
                .collect();
            let c_mean = if residuals.is_empty() {
                1.0
            } else {
                residuals.iter().sum::<f64>() / residuals.len() as f64
            };
            let c_std = if residuals.len() > 1 {
                (residuals.iter().map(|&v| (v - c_mean).powi(2)).sum::<f64>()
                    / residuals.len() as f64)
                    .sqrt()
            } else {
                0.0
            };
            let lower: Vec<f64> = predicted.iter().map(|&p| (c_mean - 3.0 * c_std) * p).collect();
            let upper: Vec<f64> = predicted.iter().map(|&p| (c_mean + 3.0 * c_std) * p).collect();
            match threshold_direction {
                "both" => (lower, upper),
                "lower" => (lower, vec![f64::INFINITY; n]),
                "upper" => (vec![f64::NEG_INFINITY; n], upper),
                _ => (vec![f64::NEG_INFINITY; n], vec![f64::INFINITY; n]),
            }
        }
        ThresholdValue::Fixed(v) => {
            make_directional_thresholds(n, *v, *v, threshold_direction)
        }
        ThresholdValue::FixedPair(pair) => {
            let lo = pair.first().copied().unwrap_or(f64::NEG_INFINITY);
            let hi = pair.get(1).copied().unwrap_or(f64::INFINITY);
            make_directional_thresholds(n, lo, hi, threshold_direction)
        }
        _ => (vec![f64::NEG_INFINITY; n], vec![f64::INFINITY; n]),
    }
}

fn make_directional_thresholds(
    n: usize,
    lo: f64,
    hi: f64,
    direction: &str,
) -> (Vec<f64>, Vec<f64>) {
    match direction {
        "both" => (vec![lo; n], vec![hi; n]),
        "lower" => (vec![lo; n], vec![f64::INFINITY; n]),
        "upper" => (vec![f64::NEG_INFINITY; n], vec![hi; n]),
        _ => (vec![f64::NEG_INFINITY; n], vec![f64::INFINITY; n]),
    }
}

fn filter_collection(col: &CollectionPostprocessed, mask: &[bool]) -> CollectionPostprocessed {
    let idx: Vec<usize> = mask
        .iter()
        .enumerate()
        .filter(|(_, &m)| m)
        .map(|(i, _)| i)
        .collect();
    CollectionPostprocessed {
        sweep_legend: col.sweep_legend.clone(),
        ioc: idx.iter().map(|&i| col.ioc[i]).collect(),
        d: idx.iter().map(|&i| col.d[i]).collect(),
        velocity: idx.iter().map(|&i| col.velocity[i]).collect(),
        n: idx.iter().map(|&i| col.n[i]).collect(),
        std_ioc: idx.iter().map(|&i| col.std_ioc[i]).collect(),
        position_start: idx.iter().map(|&i| col.position_start[i]).collect(),
        position_end: idx.iter().map(|&i| col.position_end[i]).collect(),
        position_refined: idx.iter().map(|&i| col.position_refined[i].clone()).collect(),
        ioc_profile: idx.iter().map(|&i| col.ioc_profile[i].clone()).collect(),
    }
}

/// Linear regression via closed-form 2×2 normal equations.
fn linear_regression(x: &[f64], y: &[f64]) -> (f64, f64) {
    let n = x.len() as f64;
    if n < 2.0 {
        return (0.0, y.first().copied().unwrap_or(0.0));
    }
    let sum_x: f64 = x.iter().sum();
    let sum_y: f64 = y.iter().sum();
    let sum_xx: f64 = x.iter().map(|&v| v * v).sum();
    let sum_xy: f64 = x.iter().zip(y.iter()).map(|(&xi, &yi)| xi * yi).sum();
    let det = n * sum_xx - sum_x * sum_x;
    if det.abs() < 1e-15 {
        return (0.0, sum_y / n);
    }
    let a = (n * sum_xy - sum_x * sum_y) / det;
    let b = (sum_y - a * sum_x) / n;
    (a, b)
}

pub struct CalibrationResult {
    pub x: Vec<f64>,
    pub a: Vec<f64>,
}

/// iOC spatial calibration: iterative estimation of A(x) such that iOC(t,x) = meaniOC(t) * A(x).
fn ioc_calibration_fn(
    ioc_profiles: &[&Vec<f64>],
    positions: &[&Vec<f64>],
) -> CalibrationResult {
    let threshold = 1e-3;
    let dx = 1.0;

    let n_traj = ioc_profiles.len();

    // Flatten all positions and iOC values
    let all_positions: Vec<f64> = positions.iter().flat_map(|p| p.iter().copied()).collect();
    let all_ioc: Vec<f64> = ioc_profiles
        .iter()
        .flat_map(|p| p.iter().copied())
        .collect();
    let total = all_positions.len();

    // Per-trajectory index ranges
    let mut ind_i: Vec<std::ops::Range<usize>> = Vec::with_capacity(n_traj);
    let mut a = 0;
    for pos in positions.iter() {
        ind_i.push(a..a + pos.len());
        a += pos.len();
    }

    // Position grid
    let pos_start = all_positions
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, f64::max); // max of per-traj mins
    let pos_end = all_positions
        .iter()
        .copied()
        .fold(f64::INFINITY, f64::min); // min of per-traj maxs

    if pos_start >= pos_end {
        return CalibrationResult { x: vec![], a: vec![] };
    }

    let x_grid: Vec<f64> = {
        let mut v = vec![];
        let mut xi = pos_start + dx / 2.0;
        while xi < pos_end - dx / 2.0 {
            v.push(xi);
            xi += dx;
        }
        v
    };

    if x_grid.is_empty() {
        return CalibrationResult { x: vec![], a: vec![] };
    }

    let mut a_vec: Vec<f64> = vec![1.0; x_grid.len()];
    let mut a_old: Vec<f64> = vec![f64::INFINITY; x_grid.len()];
    let mut not_outlier_frame = vec![true; total];
    let not_outlier_frame0 = vec![false; total];
    let mut a_int: Vec<f64> = vec![1.0; total];
    let mut ioc_norm: Vec<f64> = vec![1.0; total];

    let mut iter_count = 0;
    while not_outlier_frame != not_outlier_frame0
        || a_vec.iter().zip(a_old.iter()).any(|(a, b)| (a - b).abs() > threshold)
    {
        if iter_count > 200 {
            break;
        }
        iter_count += 1;
        a_old = a_vec.clone();

        // Calculate meaniOC and iOCnorm
        let y: Vec<f64> = all_ioc
            .iter()
            .zip(a_int.iter())
            .map(|(&ioc_v, &ai)| if ai.abs() > 1e-15 { ioc_v / ai } else { ioc_v })
            .collect();

        for (ti, range) in ind_i.iter().enumerate() {
            let ind: Vec<usize> = range
                .clone()
                .filter(|&k| not_outlier_frame[k])
                .collect();
            if ind.is_empty() {
                continue;
            }
            let mean_ioc = ind.iter().map(|&k| y[k]).sum::<f64>() / ind.len() as f64;
            for k in range.clone() {
                ioc_norm[k] = if mean_ioc.abs() > 1e-15 {
                    all_ioc[k] / mean_ioc
                } else {
                    all_ioc[k]
                };
            }
        }

        // Remove outliers from iOCnorm / Aint
        let y_check: Vec<f64> = ioc_norm
            .iter()
            .zip(a_int.iter())
            .map(|(&n, &ai)| if ai.abs() > 1e-15 { n / ai } else { n })
            .collect();
        let active: Vec<f64> = (0..total)
            .filter(|&k| not_outlier_frame[k])
            .map(|k| y_check[k])
            .collect();
        let (_std_v, _mean_v, sel) = std_modified(&active, true, true);
        let mut active_idx = active.iter().enumerate();
        let mut sel_iter = sel.iter();
        for k in 0..total {
            if not_outlier_frame[k] {
                let keep = sel_iter.next().copied().unwrap_or(true);
                not_outlier_frame[k] = keep;
            }
        }

        // Compute A(x)
        let mut a_sum = vec![0.0f64; x_grid.len()];
        let mut a_count = vec![0usize; x_grid.len()];
        for k in 0..total {
            if not_outlier_frame[k] {
                let pos = all_positions[k];
                if let Some(xi) = x_grid.iter().position(|&xg| (pos - xg).abs() <= dx / 2.0) {
                    a_sum[xi] += ioc_norm[k];
                    a_count[xi] += 1;
                }
            }
        }

        a_vec = a_sum
            .iter()
            .zip(a_count.iter())
            .map(|(&s, &c)| if c > 0 { s / c as f64 } else { 1.0 })
            .collect();

        let a_mean = {
            let finite: Vec<f64> = a_vec.iter().copied().filter(|v| v.is_finite()).collect();
            if finite.is_empty() {
                1.0
            } else {
                finite.iter().sum::<f64>() / finite.len() as f64
            }
        };
        if a_mean.abs() > 1e-15 {
            for v in &mut a_vec {
                *v /= a_mean;
            }
        }

        // Interpolate A at all positions (clamped)
        a_int = all_positions
            .iter()
            .map(|&p| interp1_clamped(&x_grid, &a_vec, p))
            .collect();
    }

    CalibrationResult { x: x_grid, a: a_vec }
}

/// Linear interpolation clamped to grid bounds.
pub fn interp1_clamped(x: &[f64], y: &[f64], xi: f64) -> f64 {
    if x.is_empty() {
        return 1.0;
    }
    if xi <= x[0] {
        return y[0];
    }
    if xi >= x[x.len() - 1] {
        return *y.last().unwrap();
    }
    let idx = x.partition_point(|&v| v < xi);
    let lo = idx - 1;
    let hi = idx;
    let t = (xi - x[lo]) / (x[hi] - x[lo]);
    y[lo] + t * (y[hi] - y[lo])
}
