use crate::kymo::KymoMatrix;

pub fn preprocess(
    im: &KymoMatrix,
    dark: f64,
    wx_vec: &[f64],
    wt_vec: &[f64],
) -> Vec<KymoMatrix> {
    // Subtract dark level in a single flat pass — no intermediate 2D allocation
    let i0 = KymoMatrix {
        data: im.data.iter().map(|&v| v - dark).collect(),
        nt: im.nt,
        nx: im.nx,
    };

    let i_smooth = movmean_2d_axis1(&i0, 16);

    let n_sweeps = wx_vec.len();
    let mut result = Vec::with_capacity(n_sweeps);

    for s in 0..n_sweeps {
        let wx = wx_vec[s] as usize;
        let wt = wt_vec[s] as usize;
        let c = remove_background(&i_smooth, wt, wx);
        result.push(c);
    }

    result
}

fn movmean_2d_axis1(im: &KymoMatrix, w: usize) -> KymoMatrix {
    let nt = im.nt;
    let nx = im.nx;
    let mut data = vec![0.0f64; nt * nx];
    for t in 0..nt {
        let smoothed = movmean_shrink(im.row(t), w);
        data[t * nx..(t + 1) * nx].copy_from_slice(&smoothed);
    }
    KymoMatrix { data, nt, nx }
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

fn remove_background(i: &KymoMatrix, wt: usize, wx: usize) -> KymoMatrix {
    let nt = i.nt;
    let nx = i.nx;

    // Step 1: c1[t * nx + x] = I[t][x] / movmean(I[t,:], 2wx+1)
    let win_x = 2 * wx + 1;
    let mut c1 = vec![0.0f64; nt * nx];
    for t in 0..nt {
        let row_mean = movmean_shrink(i.row(t), win_x);
        let c1_row = &mut c1[t * nx..(t + 1) * nx];
        for x in 0..nx {
            let denom = row_mean[x];
            c1_row[x] = if denom.abs() > 1e-15 { i.get(t, x) / denom } else { 1.0 };
        }
    }

    // Step 2: transpose c1 to column-major layout (c1_col[x * nt + t] = c1[t * nx + x])
    // so that each column is a contiguous slice for the temporal median pass.
    let mut c1_col = vec![0.0f64; nx * nt];
    for t in 0..nt {
        for x in 0..nx {
            c1_col[x * nt + t] = c1[t * nx + x];
        }
    }

    // Step 3: c[t][x] = c1[t][x] / movmedian(c1[:,x], 2wt+1) - 1
    let win_t = 2 * wt + 1;
    let mut data = vec![0.0f64; nt * nx];
    for x in 0..nx {
        let col_med = movmedian_shrink(&c1_col[x * nt..(x + 1) * nt], win_t);
        for t in 0..nt {
            let denom = col_med[t];
            data[t * nx + x] = if denom.abs() > 1e-15 {
                c1[t * nx + x] / denom - 1.0
            } else {
                c1[t * nx + x] - 1.0
            };
        }
    }

    KymoMatrix { data, nt, nx }
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

// Two sorted Vecs maintain a split of the current window, replacing the
// previous BTreeMap implementation.  Vec operations (binary search +
// memmove) have much smaller constant factors than B-tree node traversal
// for the window sizes used here (typically w ≤ 200).
//
// Invariants:
//   • lower is sorted ascending; its maximum is lower.last()
//   • upper is sorted ascending; its minimum is upper.first()
//   • every element in lower ≤ every element in upper
//   • lower.len() == upper.len()  OR  lower.len() == upper.len() + 1
struct SlidingMedian {
    lower: Vec<OrdF64>, // lower half — max is last element
    upper: Vec<OrdF64>, // upper half — min is first element
}

impl SlidingMedian {
    fn new(w: usize) -> Self {
        let half = w / 2 + 1;
        Self {
            lower: Vec::with_capacity(half + 1),
            upper: Vec::with_capacity(half),
        }
    }

    fn add(&mut self, val: f64) {
        let key = OrdF64::from(val);
        if self.lower.is_empty() || key <= *self.lower.last().unwrap() {
            let pos = self.lower.partition_point(|&k| k < key);
            self.lower.insert(pos, key);
        } else {
            let pos = self.upper.partition_point(|&k| k < key);
            self.upper.insert(pos, key);
        }
        self.rebalance();
    }

    fn remove(&mut self, val: f64) {
        let key = OrdF64::from(val);
        // Prefer removing from lower when the value sits on the boundary
        // (lower.last() == key); this matches the add() routing above.
        if !self.lower.is_empty() && key <= *self.lower.last().unwrap() {
            let pos = self.lower.binary_search(&key).unwrap();
            self.lower.remove(pos);
        } else {
            let pos = self.upper.binary_search(&key).unwrap();
            self.upper.remove(pos);
        }
        self.rebalance();
    }

    fn rebalance(&mut self) {
        // lower is too big: move its max to the front of upper
        while self.lower.len() > self.upper.len() + 1 {
            let elem = self.lower.pop().unwrap();
            self.upper.insert(0, elem);
        }
        // upper is too big: move its min to the back of lower
        while self.upper.len() > self.lower.len() {
            let elem = self.upper.remove(0);
            self.lower.push(elem);
        }
    }

    fn median(&self) -> f64 {
        let lower_max = self.lower.last().unwrap().val();
        if self.lower.len() == self.upper.len() {
            let upper_min = self.upper.first().unwrap().val();
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
    let mut sm = SlidingMedian::new(w);
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
