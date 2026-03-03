use std::collections::BTreeMap;

pub fn preprocess(
    im: &[Vec<f64>],
    dark: f64,
    wx_vec: &[f64],
    wt_vec: &[f64],
) -> Vec<Vec<Vec<f64>>> {
    let nt = im.len();
    let nx = if nt > 0 { im[0].len() } else { 0 };

    let i0: Vec<Vec<f64>> = im
        .iter()
        .map(|row| row.iter().map(|&v| v - dark).collect())
        .collect();

    let i_smooth = movmean_2d_axis1(&i0, 16);

    let n_sweeps = wx_vec.len();
    let mut result = Vec::with_capacity(n_sweeps);

    for s in 0..n_sweeps {
        let wx = wx_vec[s] as usize;
        let wt = wt_vec[s] as usize;
        let c = remove_background(&i_smooth, wt, wx, nt, nx);
        result.push(c);
    }

    result
}

fn movmean_2d_axis1(im: &[Vec<f64>], w: usize) -> Vec<Vec<f64>> {
    im.iter().map(|row| movmean_shrink(row, w)).collect()
}

pub fn movmean_shrink(x: &[f64], w: usize) -> Vec<f64> {
    let n = x.len();
    if n == 0 {
        return vec![];
    }
    let half = w / 2;
    let mut prefix = vec![0.0f64; n + 1];
    for i in 0..n {
        prefix[i + 1] = prefix[i] + x[i];
    }
    let mut out = vec![0.0f64; n];
    for i in 0..n {
        let lo = if i >= half { i - half } else { 0 };
        let hi = (i + half).min(n - 1);
        let count = (hi - lo + 1) as f64;
        out[i] = (prefix[hi + 1] - prefix[lo]) / count;
    }
    out
}

fn remove_background(
    i: &[Vec<f64>],
    wt: usize,
    wx: usize,
    nt: usize,
    nx: usize,
) -> Vec<Vec<f64>> {
    // Step 1: C1[t][x] = I[t][x] / movmean(I[t,:], 2Wx+1, spatial)
    let win_x = 2 * wx + 1;
    let mut c1 = vec![vec![0.0f64; nx]; nt];
    for t in 0..nt {
        let row_mean = movmean_shrink(&i[t], win_x);
        for x in 0..nx {
            let denom = row_mean[x];
            c1[t][x] = if denom.abs() > 1e-15 { i[t][x] / denom } else { 1.0 };
        }
    }

    // Step 2: C[t][x] = C1[t][x] / movmedian(C1[:,x], 2Wt+1, temporal) - 1
    // Transpose c1 to column-major for sequential memory access during temporal pass
    let mut c1_col: Vec<Vec<f64>> = vec![vec![0.0f64; nt]; nx];
    for t in 0..nt {
        for x in 0..nx {
            c1_col[x][t] = c1[t][x];
        }
    }

    let win_t = 2 * wt + 1;
    let mut c = vec![vec![0.0f64; nx]; nt];
    for x in 0..nx {
        let col_med = movmedian_shrink(&c1_col[x], win_t);
        for t in 0..nt {
            let denom = col_med[t];
            c[t][x] = if denom.abs() > 1e-15 {
                c1[t][x] / denom - 1.0
            } else {
                c1[t][x] - 1.0
            };
        }
    }
    c
}

// ── O(n log w) sliding window median ─────────────────────────────────────────
//
// Two BTreeMaps maintain a split of the current window:
//   lower — the bottom half  (we query its max)
//   upper — the top half     (we query its min)
// Invariant: lower_size == upper_size  OR  lower_size == upper_size + 1
// This means the median is:
//   odd window  → max(lower)
//   even window → (max(lower) + min(upper)) / 2

#[derive(Clone, Copy, PartialEq, Eq)]
struct OrdF64(u64); // bit-cast of f64 preserving total order for finite values

impl OrdF64 {
    fn from(v: f64) -> Self {
        // For finite f64, reinterpreting bits as u64 preserves order when
        // the sign bit is 0 (positive). Negative values need bit-flip.
        // Using total_cmp semantics via the standard trick:
        let bits = v.to_bits();
        let bits = if v.is_sign_negative() { !bits } else { bits | (1 << 63) };
        OrdF64(bits)
    }
    fn val(self) -> f64 {
        let bits = self.0;
        let bits = if bits & (1 << 63) != 0 { bits & !(1 << 63) } else { !bits };
        f64::from_bits(bits)
    }
}

impl PartialOrd for OrdF64 {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}
impl Ord for OrdF64 {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.0.cmp(&other.0)
    }
}

struct SlidingMedian {
    lower: BTreeMap<OrdF64, usize>, // lower half — query max
    upper: BTreeMap<OrdF64, usize>, // upper half — query min
    lower_size: usize,
    upper_size: usize,
}

impl SlidingMedian {
    fn new() -> Self {
        Self {
            lower: BTreeMap::new(),
            upper: BTreeMap::new(),
            lower_size: 0,
            upper_size: 0,
        }
    }

    fn add(&mut self, val: f64) {
        let key = OrdF64::from(val);
        if self.lower_size == 0 || key <= *self.lower.keys().next_back().unwrap() {
            *self.lower.entry(key).or_insert(0) += 1;
            self.lower_size += 1;
        } else {
            *self.upper.entry(key).or_insert(0) += 1;
            self.upper_size += 1;
        }
        self.rebalance();
    }

    fn remove(&mut self, val: f64) {
        let key = OrdF64::from(val);
        // Remove from whichever half holds this key; prefer lower when
        // the key sits on the boundary of both (correct with duplicates).
        if self.lower.contains_key(&key) {
            let cnt = self.lower.get_mut(&key).unwrap();
            *cnt -= 1;
            if *cnt == 0 {
                self.lower.remove(&key);
            }
            self.lower_size -= 1;
        } else {
            let cnt = self.upper.get_mut(&key).unwrap();
            *cnt -= 1;
            if *cnt == 0 {
                self.upper.remove(&key);
            }
            self.upper_size -= 1;
        }
        self.rebalance();
    }

    fn rebalance(&mut self) {
        while self.lower_size > self.upper_size + 1 {
            let (&key, _) = self.lower.iter().next_back().unwrap();
            let cnt = self.lower.get_mut(&key).unwrap();
            *cnt -= 1;
            if *cnt == 0 {
                self.lower.remove(&key);
            }
            self.lower_size -= 1;
            *self.upper.entry(key).or_insert(0) += 1;
            self.upper_size += 1;
        }
        while self.upper_size > self.lower_size {
            let (&key, _) = self.upper.iter().next().unwrap();
            let cnt = self.upper.get_mut(&key).unwrap();
            *cnt -= 1;
            if *cnt == 0 {
                self.upper.remove(&key);
            }
            self.upper_size -= 1;
            *self.lower.entry(key).or_insert(0) += 1;
            self.lower_size += 1;
        }
    }

    fn median(&self) -> f64 {
        let lower_max = self.lower.keys().next_back().unwrap().val();
        if self.lower_size == self.upper_size {
            let upper_min = self.upper.keys().next().unwrap().val();
            (lower_max + upper_min) / 2.0
        } else {
            lower_max
        }
    }
}

/// O(n log w) sliding window median with shrink endpoints.
pub fn movmedian_shrink(x: &[f64], w: usize) -> Vec<f64> {
    let n = x.len();
    if n == 0 {
        return vec![];
    }
    let half = w / 2;
    let mut out = vec![0.0f64; n];
    let mut sm = SlidingMedian::new();
    let mut right = 0usize;

    for i in 0..n {
        let hi = (i + half).min(n - 1);

        // Expand right edge of window
        while right <= hi {
            sm.add(x[right]);
            right += 1;
        }

        // Drop element that just left the left edge
        if i >= half + 1 {
            sm.remove(x[i - half - 1]);
        }

        out[i] = sm.median();
    }
    out
}
