use std::collections::HashMap;

use crate::postprocess::CollectionPostprocessed;

#[derive(Debug, Clone)]
pub struct Population {
    pub mean: HashMap<String, f64>,
    pub std: HashMap<String, f64>,
    pub fwhm: HashMap<String, f64>,
    pub resolution: HashMap<String, f64>,
    pub n_trajectories: usize,
}

/// Multi-dimensional robust mean / std (robustStyle='multiD').
pub fn analyze_population_robust_mean(
    collection: &CollectionPostprocessed,
    properties: &[String],
) -> Population {
    let n = collection.len();
    if n == 0 {
        return Population {
            mean: HashMap::new(),
            std: HashMap::new(),
            fwhm: HashMap::new(),
            resolution: HashMap::new(),
            n_trajectories: 0,
        };
    }

    // Build matrix Y[prop][traj]
    let np = properties.len();
    let mut y: Vec<Vec<f64>> = Vec::with_capacity(np);
    for prop in properties {
        let col = collection.get_field(prop).unwrap_or_else(|| vec![f64::NAN; n]);
        y.push(col);
    }

    // Weights = N (number of frames per trajectory)
    let weights: Vec<f64> = collection.n.clone();

    let (std_vals, mean_vals, selected) = std_modified_nd_multid(&y, &weights, n, np);

    let n_traj = selected.iter().filter(|&&v| v).count();

    let mut pop = Population {
        mean: HashMap::new(),
        std: HashMap::new(),
        fwhm: HashMap::new(),
        resolution: HashMap::new(),
        n_trajectories: n_traj,
    };

    for (i, prop) in properties.iter().enumerate() {
        let m = mean_vals[i];
        let s = std_vals[i];
        let fwhm = 2.0 * (2.0 * std::f64::consts::LN_2).sqrt() * s;
        let resolution = if fwhm.abs() > 1e-15 { m.abs() / fwhm } else { f64::NAN };
        pop.mean.insert(prop.clone(), m);
        pop.std.insert(prop.clone(), s);
        pop.fwhm.insert(prop.clone(), fwhm);
        pop.resolution.insert(prop.clone(), resolution);
    }

    pop
}

/// std_modified_ND with robustStyle='multiD' and optional weights.
/// x: [np × n] matrix (outer = properties, inner = trajectories)
/// Returns (STD[np], MEAN[np], selected[n]).
fn std_modified_nd_multid(
    x: &[Vec<f64>],
    weights: &[f64],
    n: usize,
    np: usize,
) -> (Vec<f64>, Vec<f64>, Vec<bool>) {
    if n == 0 || np == 0 {
        return (vec![0.0; np], vec![0.0; np], vec![]);
    }

    // Initial mask: all finite
    let mut selected: Vec<bool> = (0..n)
        .map(|j| x.iter().all(|row| row[j].is_finite()))
        .collect();
    let mut selected0: Vec<bool> = selected.iter().map(|&v| !v).collect();

    let mut mean = vec![0.0f64; np];
    let mut std_v = vec![0.0f64; np];

    while selected != selected0 {
        selected0 = selected.clone();

        let sel_idx: Vec<usize> = selected
            .iter()
            .enumerate()
            .filter(|(_, &s)| s)
            .map(|(i, _)| i)
            .collect();

        if sel_idx.is_empty() {
            break;
        }

        let w_sum: f64 = sel_idx.iter().map(|&j| weights[j]).sum();

        for p in 0..np {
            let wm = if w_sum > 1e-15 {
                sel_idx.iter().map(|&j| weights[j] * x[p][j]).sum::<f64>() / w_sum
            } else {
                sel_idx.iter().map(|&j| x[p][j]).sum::<f64>() / sel_idx.len() as f64
            };
            mean[p] = wm;

            let wv = if w_sum > 1e-15 {
                sel_idx
                    .iter()
                    .map(|&j| weights[j] * (x[p][j] - wm).powi(2))
                    .sum::<f64>()
                    / w_sum
            } else {
                sel_idx
                    .iter()
                    .map(|&j| (x[p][j] - wm).powi(2))
                    .sum::<f64>()
                    / sel_idx.len() as f64
            };
            std_v[p] = wv.sqrt();
        }

        // Mahalanobis radius for selected points only
        let r: Vec<f64> = sel_idx
            .iter()
            .map(|&j| {
                (0..np)
                    .map(|p| {
                        let s = std_v[p];
                        if s > 1e-15 {
                            ((x[p][j] - mean[p]) / (3.0 * s)).powi(2)
                        } else {
                            0.0
                        }
                    })
                    .sum::<f64>()
            })
            .collect();

        // Update selected: only those among sel_idx with R < 1
        for (k, &j) in sel_idx.iter().enumerate() {
            selected[j] = r[k] < 1.0;
        }
    }

    (std_v, mean, selected)
}
