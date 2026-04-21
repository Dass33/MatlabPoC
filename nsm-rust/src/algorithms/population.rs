/// Port of analyzePopulation_robustMean.m, std_modified_ND.m,
///         analyzePopulation_gaussFit.m / algorithms/population.py

use std::collections::HashMap;
use crate::models::{Collection, PropStats};

const FWHM_FACTOR: f64 = 2.354_820_045; // 2 * sqrt(2 * ln(2))

pub fn robust_mean(collection: &Collection, props: &[&str]) -> HashMap<String, PropStats> {
    if props.is_empty() { return HashMap::new(); }
    let n = collection.len();
    if n == 0 { return HashMap::new(); }

    let arrays: Vec<&Vec<f64>> = props.iter()
        .filter_map(|p| collection.scalar_prop(p))
        .collect();
    if arrays.is_empty() { return HashMap::new(); }
    let p = arrays.len();

    let weights = if collection.n.len() == n { Some(&collection.n) } else { None };

    let mut selected: Vec<bool> = (0..n)
        .map(|i| arrays.iter().all(|a| i < a.len() && a[i].is_finite()))
        .collect();
    let mut selected0: Vec<bool> = selected.iter().map(|&b| !b).collect();

    let mut mean_v = vec![f64::NAN; p];
    let mut std_v  = vec![f64::NAN; p];

    for _ in 0..100 {
        if selected == selected0 { break; }
        selected0 = selected.clone();

        let sel_idx: Vec<usize> = (0..n).filter(|&i| selected[i]).collect();
        if sel_idx.is_empty() { break; }

        if let Some(w) = weights {
            let w_sel: Vec<f64> = sel_idx.iter().map(|&i| w[i].max(0.0)).collect();
            let w_sum: f64 = w_sel.iter().sum();
            if w_sum < 1e-12 { break; }
            for k in 0..p {
                mean_v[k] = sel_idx.iter().zip(&w_sel)
                    .map(|(&i, &wi)| arrays[k][i] * wi)
                    .sum::<f64>() / w_sum;
                std_v[k] = (sel_idx.iter().zip(&w_sel)
                    .map(|(&i, &wi)| wi * (arrays[k][i] - mean_v[k]).powi(2))
                    .sum::<f64>() / w_sum)
                    .sqrt();
            }
        } else {
            let m = sel_idx.len() as f64;
            for k in 0..p {
                let vals: Vec<f64> = sel_idx.iter().map(|&i| arrays[k][i]).collect();
                mean_v[k] = vals.iter().sum::<f64>() / m;
                std_v[k]  = (vals.iter().map(|v| (v - mean_v[k]).powi(2)).sum::<f64>() / m).sqrt();
            }
        }

        let std_safe: Vec<f64> = std_v.iter().map(|&s| if s == 0.0 { 1.0 } else { s }).collect();
        for &i in &sel_idx {
            let r: f64 = (0..p)
                .map(|k| ((arrays[k][i] - mean_v[k]) / (std_safe[k] * 3.0)).powi(2))
                .sum();
            selected[i] = r < 1.0;
        }
    }

    let mut result = HashMap::new();
    for (k, prop) in props.iter().enumerate() {
        let fwhm = FWHM_FACTOR * std_v[k];
        result.insert(prop.to_string(), PropStats {
            mean: mean_v[k],
            std:  std_v[k],
            fwhm,
            resolution: if fwhm != 0.0 { mean_v[k].abs() / fwhm } else { f64::NAN },
            hist_centers: None,
            hist_counts: None,
        });
    }
    result
}

pub fn gauss_fit(collection: &Collection, props: &[&str]) -> HashMap<String, PropStats> {
    let mut result = HashMap::new();
    let n = collection.len();
    let weights = if collection.n.len() == n { Some(&collection.n) } else { None };

    for &prop in props {
        let Some(y_raw) = collection.scalar_prop(prop) else { continue };

        let y_clean: Vec<f64> = y_raw.iter().cloned().filter(|x| x.is_finite()).collect();
        if y_clean.is_empty() { continue; }

        // Robust initial estimates (median + MAD)
        let mut sorted = y_clean.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let mean_est = sorted[sorted.len() / 2];
        let mut devs: Vec<f64> = y_clean.iter().map(|y| (y - mean_est).abs()).collect();
        devs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let std_est  = (devs[devs.len() / 2] / 0.6745).max(1e-10);
        let n_est    = y_clean.iter().filter(|&&v| (v - mean_est).abs() < 3.0 * std_est).count();

        // Expand by N counts if available
        let y_expanded: Vec<f64> = if let Some(w) = weights {
            y_raw.iter().zip(w.iter())
                .filter(|(&yi, &ni)| yi.is_finite() && ni.is_finite())
                .flat_map(|(&yi, &ni)| std::iter::repeat(yi).take(ni.round().max(0.0) as usize))
                .collect()
        } else {
            y_clean.clone()
        };

        // Freedman-Diaconis binning
        let dx = (3.5 * std_est / (n_est as f64).max(1.0).cbrt()).max(1e-10);
        let y_min = y_expanded.iter().cloned().fold(f64::INFINITY,     f64::min);
        let y_max = y_expanded.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let mut edges = vec![];
        let mut e = y_min - dx / 2.0;
        while e <= y_max + dx {
            edges.push(e);
            e += dx;
        }
        if edges.len() < 2 { continue; }

        let (centers, counts) = histogram(&y_expanded, &edges);

        // Gaussian LM fit
        let amp0 = counts.iter().cloned().max().unwrap_or(1) as f64;
        let p0   = [amp0, mean_est, std_est];
        let (_, fit_mean, fit_std) = lm_gaussian_fit(&centers, &counts, p0)
            .unwrap_or((amp0, mean_est, std_est));

        let fit_std_abs = fit_std.abs().max(1e-10);
        let fwhm = FWHM_FACTOR * fit_std_abs;
        result.insert(prop.to_string(), PropStats {
            mean: fit_mean,
            std:  fit_std_abs,
            fwhm,
            resolution: if fwhm != 0.0 { fit_mean.abs() / fwhm } else { f64::NAN },
            hist_centers: Some(centers),
            hist_counts:  Some(counts),
        });
    }
    result
}

// ── Histogram ─────────────────────────────────────────────────────────────────

fn histogram(y: &[f64], edges: &[f64]) -> (Vec<f64>, Vec<u64>) {
    let n_bins = edges.len() - 1;
    let mut counts = vec![0_u64; n_bins];
    for &v in y {
        if v.is_nan() { continue; }
        let idx = edges.partition_point(|&e| e <= v).saturating_sub(1).min(n_bins - 1);
        counts[idx] += 1;
    }
    let centers = (0..n_bins).map(|i| (edges[i] + edges[i + 1]) / 2.0).collect();
    (centers, counts)
}

// ── Levenberg-Marquardt for Gaussian f(x; A, mu, sig) = A*exp(-(x-mu)^2/(2*sig^2)) ─

fn gaussian(x: f64, amp: f64, mu: f64, sig: f64) -> f64 {
    amp * (-(x - mu).powi(2) / (2.0 * sig.powi(2))).exp()
}

fn gaussian_jac(x: f64, amp: f64, mu: f64, sig: f64) -> [f64; 3] {
    let e = (-(x - mu).powi(2) / (2.0 * sig.powi(2))).exp();
    [
        e,
        amp * e * (x - mu) / sig.powi(2),
        amp * e * (x - mu).powi(2) / sig.powi(3),
    ]
}

fn lm_gaussian_fit(x: &[f64], y: &[u64], p0: [f64; 3]) -> Option<(f64, f64, f64)> {
    let m = x.len();
    if m < 3 { return None; }
    let y_f: Vec<f64> = y.iter().map(|&v| v as f64).collect();
    let mut p = p0;
    let mut lam = 1e-3_f64;

    for _ in 0..10_000 {
        let r:    Vec<f64>    = x.iter().zip(&y_f).map(|(&xi, &yi)| yi - gaussian(xi, p[0], p[1], p[2])).collect();
        let jac:  Vec<[f64;3]> = x.iter().map(|&xi| gaussian_jac(xi, p[0], p[1], p[2])).collect();

        let mut jtj = [[0.0_f64; 3]; 3];
        let mut jtr = [0.0_f64; 3];
        for i in 0..m {
            for a in 0..3 {
                jtr[a] += jac[i][a] * r[i];
                for b in 0..3 { jtj[a][b] += jac[i][a] * jac[i][b]; }
            }
        }

        let mut h = jtj;
        for k in 0..3 { h[k][k] *= 1.0 + lam; }

        let Some(dp) = solve3x3(&h, &jtr) else { break };
        let chi2     = r.iter().map(|v| v * v).sum::<f64>();
        let p_new    = [p[0] + dp[0], p[1] + dp[1], p[2] + dp[2]];
        let chi2_new = x.iter().zip(&y_f)
            .map(|(&xi, &yi)| (yi - gaussian(xi, p_new[0], p_new[1], p_new[2])).powi(2))
            .sum::<f64>();

        if chi2_new < chi2 {
            p   = p_new;
            lam /= 10.0;
            if dp.iter().map(|v| v.abs()).sum::<f64>() < 1e-9 { break; }
        } else {
            lam *= 10.0;
            if lam > 1e12 { break; }
        }
    }
    Some((p[0], p[1], p[2]))
}

fn solve3x3(a: &[[f64; 3]; 3], b: &[f64; 3]) -> Option<[f64; 3]> {
    let det = a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
            - a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
            + a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
    if det.abs() < 1e-20 { return None; }
    let d = 1.0 / det;
    let x0 = (b[0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
             - a[0][1]*(b[1]*a[2][2]-a[1][2]*b[2])
             + a[0][2]*(b[1]*a[2][1]-a[1][1]*b[2])) * d;
    let x1 = (a[0][0]*(b[1]*a[2][2]-a[1][2]*b[2])
             - b[0]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
             + a[0][2]*(a[1][0]*b[2]-b[1]*a[2][0])) * d;
    let x2 = (a[0][0]*(a[1][1]*b[2]-b[1]*a[2][1])
             - a[0][1]*(a[1][0]*b[2]-b[1]*a[2][0])
             + b[0]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])) * d;
    Some([x0, x1, x2])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::Collection;

    fn make_col(ioc: Vec<f64>) -> Collection {
        let n = ioc.len();
        Collection {
            ioc: ioc.clone(),
            std_ioc: ioc.clone(),
            d: ioc.clone(),
            velocity: ioc.clone(),
            n: vec![10.0; n],
            position_start: ioc.clone(),
            position_end:   ioc,
            ..Default::default()
        }
    }

    #[test]
    fn test_robust_mean_rejects_outlier() {
        let col = make_col(vec![1.0, 1.1, 0.9, 1.05, 50.0]);
        let res = robust_mean(&col, &["iOC"]);
        let m = res["iOC"].mean;
        assert!(m < 5.0, "outlier should not dominate mean, got {m}");
        assert!(res["iOC"].fwhm > 0.0);
    }

    #[test]
    fn test_gauss_fit_symmetric() {
        // Generate samples near a Gaussian with mean=5, std=1
        let col = make_col(vec![4.0, 4.5, 5.0, 5.0, 5.5, 6.0]);
        let res = gauss_fit(&col, &["iOC"]);
        if let Some(s) = res.get("iOC") {
            assert!((s.mean - 5.0).abs() < 1.5, "fit mean should be ~5, got {}", s.mean);
        }
    }
}
