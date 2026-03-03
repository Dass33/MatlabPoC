use crate::detection::Detection;

/// Refine detection positions using centroid within fittingRadius.
/// Returns refined positions (sub-pixel, 0-indexed).
pub fn refine_centroid(
    detections: &[Detection],
    c: &[Vec<f64>],
    fitting_radius: usize,
) -> Vec<f64> {
    let nx = if !c.is_empty() { c[0].len() } else { 0 };
    detections
        .iter()
        .map(|d| {
            let t = d.frame;
            let x = d.position;
            // MATLAB condition: x > fittingRadius && x < (Nx - fittingRadius + 1)  (1-indexed)
            // 0-indexed equivalent: x >= fitting_radius && x < nx - fitting_radius
            if x >= fitting_radius && x + fitting_radius < nx {
                let lo = x - fitting_radius;
                let hi = x + fitting_radius;
                let weights: Vec<f64> = (lo..=hi).map(|xi| c[t][xi].abs()).collect();
                let sum_w: f64 = weights.iter().sum();
                if sum_w > 1e-15 {
                    let weighted_x: f64 = (lo..=hi)
                        .zip(weights.iter())
                        .map(|(xi, &w)| xi as f64 * w)
                        .sum();
                    weighted_x / sum_w
                } else {
                    x as f64
                }
            } else {
                x as f64
            }
        })
        .collect()
}
