/// Port of findTrajectoryOutliers.m / algorithms/outlier_filtering.py
///
/// Returns a Vec<bool> where true = not an outlier (keep).
use std::collections::HashMap;
use crate::models::{Collection, OutlierFilteringConfig, ThresholdConfig, DEFAULT_SIGMA};

pub fn find_outliers(
    collection: &Collection,
    filt_config: &OutlierFilteringConfig,
    thresholds:  &HashMap<String, ThresholdConfig>,
) -> Vec<bool> {
    let ref_prop  = &filt_config.reference_property;
    let filter_props = &filt_config.filter_properties;

    let Some(ref_vals) = collection.scalar_prop(ref_prop) else {
        return vec![];
    };
    let n = ref_vals.len();
    if n == 0 {
        return vec![];
    }

    // Initialise: keep points where reference is not NaN
    let mut not_outlier: Vec<bool> = ref_vals.iter().map(|x| x.is_finite()).collect();
    for prop in filter_props {
        if let Some(v) = collection.scalar_prop(prop) {
            for (no, x) in not_outlier.iter_mut().zip(v.iter()) {
                if !x.is_finite() { *no = false; }
            }
        }
    }

    let mut not_outlier0 = vec![false; n]; // force first iteration

    for _ in 0..100 {
        if not_outlier == not_outlier0 {
            break;
        }
        not_outlier0 = not_outlier.clone();

        let mut per_prop: Vec<Vec<bool>> = Vec::with_capacity(filter_props.len());

        for prop in filter_props {
            let Some(y) = collection.scalar_prop(prop) else {
                per_prop.push(vec![true; n]);
                continue;
            };
            let default_cfg = ThresholdConfig {
                sigma: DEFAULT_SIGMA,
                direction: "upper".into(),
                tv: "3std".into(),
                ..Default::default()
            };
            let cfg = thresholds.get(prop.as_str()).unwrap_or(&default_cfg);
            let direction = cfg.direction.as_str();
            let sigma     = cfg.sigma;

            // Compute (lo, hi) per-element bounds
            let (lo, hi): (Vec<f64>, Vec<f64>) = match cfg.tv.as_str() {
                "3std" => {
                    let selected: Vec<f64> = y.iter().zip(&not_outlier0)
                        .filter(|(_, &k)| k)
                        .map(|(&v, _)| v)
                        .collect();
                    let mean_v = nanmean(&selected);
                    let std_v  = if selected.len() > 1 { nanstd_ddof1(&selected, mean_v) } else { 1.0 };
                    let lo_s = mean_v - sigma * std_v;
                    let hi_s = mean_v + sigma * std_v;
                    (vec![lo_s; n], vec![hi_s; n])
                }
                "3std_conditional" => {
                    let ref_in: Vec<f64> = ref_vals.iter().zip(&not_outlier0).filter(|(_, &k)| k).map(|(&v, _)| v).collect();
                    let y_in:   Vec<f64> = y.iter().zip(&not_outlier0).filter(|(_, &k)| k).map(|(&v, _)| v).collect();
                    let (slope, intercept) = ols(&ref_in, &y_in);
                    let ratio: Vec<f64> = y_in.iter().zip(&ref_in)
                        .map(|(&yi, &xi)| {
                            let denom = slope * xi + intercept;
                            if denom.abs() > 1e-12 { yi / denom } else { f64::NAN }
                        })
                        .filter(|r| r.is_finite())
                        .collect();
                    let mean_r = nanmean(&ratio);
                    let std_r  = if ratio.len() > 1 { nanstd_ddof1(&ratio, mean_r) } else { 1.0 };
                    let lo_v: Vec<f64> = ref_vals.iter().map(|&xi| (mean_r - sigma * std_r) * (slope * xi + intercept)).collect();
                    let hi_v: Vec<f64> = ref_vals.iter().map(|&xi| (mean_r + sigma * std_r) * (slope * xi + intercept)).collect();
                    (lo_v, hi_v)
                }
                _ /* "number" */ => {
                    match direction {
                        "both"  => (vec![cfg.value_lo; n], vec![cfg.value_hi; n]),
                        "lower" => (vec![cfg.value; n],    vec![f64::INFINITY; n]),
                        _       => (vec![f64::NEG_INFINITY; n], vec![cfg.value; n]),
                    }
                }
            };

            // Apply direction override for 3std variants
            let (lo, hi) = match direction {
                "upper" => (vec![f64::NEG_INFINITY; n], hi),
                "lower" => (lo, vec![f64::INFINITY; n]),
                _       => (lo, hi),
            };

            let mask: Vec<bool> = y.iter().zip(lo.iter()).zip(hi.iter())
                .map(|((&yi, &lo_i), &hi_i)| yi > lo_i && yi < hi_i)
                .collect();
            per_prop.push(mask);
        }

        // AND logic across all properties
        not_outlier = (0..n)
            .map(|i| per_prop.iter().all(|m| m[i]))
            .collect();
    }

    not_outlier
}

// ── Numerical helpers ──────────────────────────────────────────────────────────

fn nanmean(v: &[f64]) -> f64 {
    let vals: Vec<f64> = v.iter().filter(|x| x.is_finite()).cloned().collect();
    if vals.is_empty() { return f64::NAN; }
    vals.iter().sum::<f64>() / vals.len() as f64
}

fn nanstd_ddof1(v: &[f64], mean: f64) -> f64 {
    let vals: Vec<f64> = v.iter().filter(|x| x.is_finite()).cloned().collect();
    let n = vals.len();
    if n < 2 { return 1.0; }
    let var = vals.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (n - 1) as f64;
    var.sqrt()
}

/// Ordinary least squares for 2-coefficient fit y = slope*x + intercept.
/// Uses 2×2 normal equations (no LAPACK needed).
fn ols(x: &[f64], y: &[f64]) -> (f64, f64) {
    let n = x.len().min(y.len()) as f64;
    if n < 2.0 { return (0.0, 0.0); }
    let sx  = x.iter().sum::<f64>();
    let sy  = y.iter().sum::<f64>();
    let sxx = x.iter().map(|v| v * v).sum::<f64>();
    let sxy = x.iter().zip(y.iter()).map(|(xi, yi)| xi * yi).sum::<f64>();
    let det = n * sxx - sx * sx;
    if det.abs() < 1e-12 { return (0.0, sy / n); }
    let slope     = (n * sxy - sx * sy) / det;
    let intercept = (sy - slope * sx) / n;
    (slope, intercept)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nanmean() {
        assert!((nanmean(&[1.0, 2.0, 3.0]) - 2.0).abs() < 1e-10);
        assert!(nanmean(&[f64::NAN, 2.0, 3.0]).is_finite());
    }

    #[test]
    fn test_ols_identity() {
        let x = vec![1.0, 2.0, 3.0, 4.0];
        let y = vec![2.0, 4.0, 6.0, 8.0];
        let (s, b) = ols(&x, &y);
        assert!((s - 2.0).abs() < 1e-10);
        assert!(b.abs() < 1e-10);
    }
}
