use std::collections::VecDeque;
use statrs::distribution::{ContinuousCDF, Normal};
use crate::kymo::KymoMatrix;

#[derive(Debug, Clone)]
pub struct Detection {
    pub frame: usize,
    pub position: usize,
    pub intensity: f64,
}

pub fn detect(
    c: &KymoMatrix,
    peak_sign: &str,
    pfa: f64,
    local_optimum_range: usize,
    border_range: usize,
) -> Vec<Detection> {
    // c.data is already a contiguous flat slice — no copy needed
    let (sigma, med) = noise_stats(&c.data);
    let normal = Normal::new(0.0, 1.0).unwrap();

    let mut detections = Vec::new();

    match peak_sign {
        "negative" => {
            let tau = med + sigma * normal.inverse_cdf(pfa);
            let thresholded = compute_threshold_mask(c, |v| v < tau);
            let local_min = find_local_minima(c, local_optimum_range);
            collect_detections(c, &thresholded, &local_min, border_range, &mut detections);
        }
        "positive" => {
            let tau = med + sigma * normal.inverse_cdf(1.0 - pfa);
            let thresholded = compute_threshold_mask(c, |v| v > tau);
            let local_max = find_local_maxima(c, local_optimum_range);
            collect_detections(c, &thresholded, &local_max, border_range, &mut detections);
        }
        "negative-positive" => {
            let tau_neg = med + sigma * normal.inverse_cdf(pfa / 2.0);
            let tau_pos = med + sigma * normal.inverse_cdf(1.0 - pfa / 2.0);
            let thresholded =
                compute_threshold_mask(c, |v| v < tau_neg || v > tau_pos);
            let local_min = find_local_minima(c, local_optimum_range);
            let local_max = find_local_maxima(c, local_optimum_range);
            let local_opt: Vec<bool> = local_min
                .iter()
                .zip(local_max.iter())
                .map(|(&a, &b)| a || b)
                .collect();
            collect_detections(c, &thresholded, &local_opt, border_range, &mut detections);
        }
        _ => {}
    }

    detections
}

/// Single sort to get median and IQR-based sigma simultaneously.
fn noise_stats(x: &[f64]) -> (f64, f64) {
    let mut sorted: Vec<f64> = x.iter().cloned().filter(|v| v.is_finite()).collect();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = sorted.len();
    if n < 2 {
        return (0.0, 0.0);
    }
    let q1 = percentile(&sorted, 25.0);
    let med = percentile(&sorted, 50.0);
    let q3 = percentile(&sorted, 75.0);
    (0.7413 * (q3 - q1), med)
}

fn compute_threshold_mask(c: &KymoMatrix, predicate: impl Fn(f64) -> bool) -> Vec<bool> {
    c.data.iter().map(|&v| predicate(v)).collect()
}

/// O(n) sliding window minimum using a monotonic deque.
fn sliding_window_min(x: &[f64], w: usize) -> Vec<f64> {
    let n = x.len();
    if n == 0 {
        return vec![];
    }
    let half = w / 2;
    let mut deque: VecDeque<usize> = VecDeque::new();
    let mut out = vec![0.0f64; n];
    let mut next_right = 0usize;

    for i in 0..n {
        let lo = i.saturating_sub(half);
        let hi = (i + half).min(n - 1);

        while next_right <= hi {
            while !deque.is_empty() && x[*deque.back().unwrap()] >= x[next_right] {
                deque.pop_back();
            }
            deque.push_back(next_right);
            next_right += 1;
        }

        while !deque.is_empty() && *deque.front().unwrap() < lo {
            deque.pop_front();
        }

        out[i] = x[*deque.front().unwrap()];
    }
    out
}

/// O(n) sliding window maximum using a monotonic deque.
fn sliding_window_max(x: &[f64], w: usize) -> Vec<f64> {
    let n = x.len();
    if n == 0 {
        return vec![];
    }
    let half = w / 2;
    let mut deque: VecDeque<usize> = VecDeque::new();
    let mut out = vec![0.0f64; n];
    let mut next_right = 0usize;

    for i in 0..n {
        let lo = i.saturating_sub(half);
        let hi = (i + half).min(n - 1);

        while next_right <= hi {
            while !deque.is_empty() && x[*deque.back().unwrap()] <= x[next_right] {
                deque.pop_back();
            }
            deque.push_back(next_right);
            next_right += 1;
        }

        while !deque.is_empty() && *deque.front().unwrap() < lo {
            deque.pop_front();
        }

        out[i] = x[*deque.front().unwrap()];
    }
    out
}

fn find_local_minima(c: &KymoMatrix, half: usize) -> Vec<bool> {
    let win = 2 * half + 1;
    let nt = c.nt;
    let nx = c.nx;
    let mut out = vec![false; nt * nx];
    for t in 0..nt {
        let row = c.row(t);
        let eroded = sliding_window_min(row, win);
        for x in 0..nx {
            out[t * nx + x] = (row[x] - eroded[x]).abs() < 1e-8;
        }
    }
    out
}

fn find_local_maxima(c: &KymoMatrix, half: usize) -> Vec<bool> {
    let win = 2 * half + 1;
    let nt = c.nt;
    let nx = c.nx;
    let mut out = vec![false; nt * nx];
    for t in 0..nt {
        let row = c.row(t);
        let dilated = sliding_window_max(row, win);
        for x in 0..nx {
            out[t * nx + x] = (row[x] - dilated[x]).abs() < 1e-8;
        }
    }
    out
}

fn collect_detections(
    c: &KymoMatrix,
    thresholded: &[bool],
    local_opt: &[bool],
    border_range: usize,
    out: &mut Vec<Detection>,
) {
    let nt = c.nt;
    let nx = c.nx;
    for t in 0..nt {
        for x in 0..nx {
            if x < border_range || x >= nx.saturating_sub(border_range) {
                continue;
            }
            let idx = t * nx + x;
            if thresholded[idx] && local_opt[idx] {
                out.push(Detection {
                    frame: t,
                    position: x,
                    intensity: c.get(t, x),
                });
            }
        }
    }
}

pub fn std_iqr(x: &[f64]) -> f64 {
    let (sigma, _) = noise_stats(x);
    sigma
}

pub fn median_f64(x: &[f64]) -> f64 {
    let mut v: Vec<f64> = x.iter().cloned().filter(|v| v.is_finite()).collect();
    if v.is_empty() {
        return 0.0;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 0 {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    } else {
        v[n / 2]
    }
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    let n = sorted.len();
    if n == 0 {
        return 0.0;
    }
    let idx = p / 100.0 * (n - 1) as f64;
    let lo = idx.floor() as usize;
    let hi = idx.ceil() as usize;
    if lo == hi {
        sorted[lo]
    } else {
        sorted[lo] + (idx - lo as f64) * (sorted[hi] - sorted[lo])
    }
}
