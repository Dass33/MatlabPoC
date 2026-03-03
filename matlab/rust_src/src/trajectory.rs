use crate::linking::Track;

/// Per-track trajectory analysis results
#[derive(Debug, Clone)]
pub struct TrajectoryResult {
    pub ioc_profile: Vec<f64>,
    pub ioc: f64,
    pub std_ioc: f64,
    pub n: f64,
    pub position_start: f64,
    pub position_end: f64,
    pub d: f64,
    pub velocity: f64,
    pub position_refined: Vec<f64>,
}

/// Analyze all tracks for one sweep.
pub fn analyze_tracks(
    tracks: &[Track],
    c: &[Vec<f64>],
    wx: f64,
    dx: f64,
    dt: f64,
) -> Vec<TrajectoryResult> {
    tracks
        .iter()
        .map(|track| analyze_single_track(track, c, wx, dx, dt))
        .collect()
}

fn analyze_single_track(track: &Track, c: &[Vec<f64>], wx: f64, dx: f64, dt: f64) -> TrajectoryResult {
    let nx = if !c.is_empty() { c[0].len() } else { 0 };
    let n_spots = track.frames.len();

    // iOC profile: one value per frame
    let mut ioc_profile = Vec::with_capacity(n_spots);
    for i in 0..n_spots {
        let t = track.frames[i];
        let x = track.positions[i];
        let (ioc_raw, _pos, base_length) = analyze_minima(c, t, x, 0.0);
        let a = (2.0 * wx + 1.0) / (2.0 * wx + 1.0 - base_length);
        let ioc_cal = ioc_raw * a * dx;
        ioc_profile.push(ioc_cal);
    }

    // Mean iOC and STD via iterative 3-sigma
    let (std_ioc, ioc_mean, selected) = std_modified(&ioc_profile, true, true);
    let n_selected = selected.iter().filter(|&&v| v).count() as f64;

    // positionStart / positionEnd
    let pos_start = track
        .positions_refined
        .iter()
        .cloned()
        .fold(f64::INFINITY, f64::min);
    let pos_end = track
        .positions_refined
        .iter()
        .cloned()
        .fold(f64::NEG_INFINITY, f64::max);

    // Vestergaard diffusivity + velocity
    let (d_px, vel_px) = trajectories_to_diffusivity(&track.positions_refined, &track.frames);
    let d = d_px * dx * dx / dt;
    let velocity = vel_px * dx / dt;

    TrajectoryResult {
        ioc_profile,
        ioc: ioc_mean,
        std_ioc,
        n: n_selected,
        position_start: pos_start,
        position_end: pos_end,
        d,
        velocity,
        position_refined: track.positions_refined.clone(),
    }
}

/// Compute iOC integral and base length for one spot.
/// Returns (iOC_px, centroid_position_px, base_length_px).
///
/// Mirrors analyzeMinimas.m with threshold=0.
pub fn analyze_minima(
    c: &[Vec<f64>],
    t: usize,
    x: usize,
    threshold: f64,
) -> (f64, f64, f64) {
    let nx = if !c.is_empty() { c[0].len() } else { 0 };
    let row = &c[t];

    let mut val = row[x];
    let flip = val >= 0.0;
    // Borrow directly when no negation needed — avoid cloning the full row
    let row_flipped: std::borrow::Cow<[f64]> = if flip {
        std::borrow::Cow::Owned(row.iter().map(|&v| -v).collect())
    } else {
        std::borrow::Cow::Borrowed(row)
    };
    val = row_flipped[x];

    if val > 0.0 {
        return (0.0, x as f64, 0.0);
    }

    let max_i = val * threshold; // threshold=0 → max_i = 0

    // Walk left
    let mut b_left = x;
    while b_left > 0 && row_flipped[b_left - 1] <= max_i {
        b_left -= 1;
    }

    // Walk right
    let mut b_right = x;
    while b_right + 1 < nx && row_flipped[b_right + 1] <= max_i {
        b_right += 1;
    }

    // Sub-pixel left boundary
    let x_left = if b_left == 0 {
        0.0
    } else {
        let d_i1 = row_flipped[b_left - 1] - row_flipped[b_left];
        if d_i1.abs() > 1e-15 {
            let d_i2 = max_i - row_flipped[b_left];
            b_left as f64 - d_i2 / d_i1
        } else {
            b_left as f64
        }
    };

    // Sub-pixel right boundary
    let x_right = if b_right == nx - 1 {
        (nx - 1) as f64
    } else {
        let d_i1 = row_flipped[b_right + 1] - row_flipped[b_right];
        if d_i1.abs() > 1e-15 {
            let d_i2 = max_i - row_flipped[b_right];
            b_right as f64 + d_i2 / d_i1
        } else {
            b_right as f64
        }
    };

    // Build integration x and y vectors
    let mut xs: Vec<f64> = vec![x_left];
    xs.extend((b_left..=b_right).map(|i| i as f64));
    xs.push(x_right);

    let mut ys: Vec<f64> = vec![max_i];
    ys.extend((b_left..=b_right).map(|i| row_flipped[i]));
    ys.push(max_i);

    let ioc_raw = trapz(&xs, &ys);
    let position = if ioc_raw.abs() > 1e-15 {
        let weighted: f64 = xs.iter().zip(ys.iter()).map(|(&xi, &yi)| xi * yi).sum();
        let sum_y: f64 = ys.iter().sum::<f64>();
        if sum_y.abs() > 1e-15 { weighted / sum_y } else { x as f64 }
    } else {
        x as f64
    };

    let base_length = x_right - x_left;
    let ioc_signed = if flip { -ioc_raw } else { ioc_raw };
    (ioc_signed, position, base_length)
}

fn trapz(x: &[f64], y: &[f64]) -> f64 {
    x.windows(2)
        .zip(y.windows(2))
        .map(|(xw, yw)| (xw[1] - xw[0]) * (yw[0] + yw[1]) / 2.0)
        .sum()
}

/// Vestergaard estimator (version 2).
/// Returns (diffusivity_px2_per_frame, velocity_px_per_frame).
pub fn trajectories_to_diffusivity(positions: &[f64], frames: &[usize]) -> (f64, f64) {
    if positions.len() <= 3 {
        return (f64::NAN, f64::NAN);
    }

    let displacements: Vec<f64> = positions.windows(2).map(|w| w[1] - w[0]).collect();
    let dt_frames: Vec<i64> = frames.windows(2).map(|w| w[1] as i64 - w[0] as i64).collect();

    let relevant: Vec<bool> = dt_frames.iter().map(|&d| d == 1).collect();
    let rel_disps: Vec<f64> = displacements
        .iter()
        .zip(relevant.iter())
        .filter(|(_, &r)| r)
        .map(|(&d, _)| d)
        .collect();

    if rel_disps.is_empty() {
        return (f64::NAN, f64::NAN);
    }

    let velocity = rel_disps.iter().sum::<f64>() / rel_disps.len() as f64;
    let d0 = rel_disps.iter().map(|&d| (d - velocity).powi(2)).sum::<f64>()
        / rel_disps.len() as f64
        / 2.0;

    // Autocorrelation: consecutive relevant pairs
    let rel_consecutive: Vec<bool> = (0..relevant.len().saturating_sub(1))
        .map(|i| relevant[i] && relevant[i + 1])
        .collect();

    let correction: f64 = {
        let pairs: Vec<f64> = displacements
            .windows(2)
            .zip(rel_consecutive.iter())
            .filter(|(_, &r)| r)
            .map(|(w, _)| (w[0] - velocity) * (w[1] - velocity))
            .collect();
        if pairs.is_empty() {
            0.0
        } else {
            pairs.iter().sum::<f64>() / pairs.len() as f64
        }
    };

    (d0 + correction, velocity)
}

/// Iterative 3-sigma robust STD and MEAN.
/// fun_mean=true → compute mean; fun_stabil=true → iterate.
/// Returns (STD, MEAN, selected_mask).
pub fn std_modified(x: &[f64], fun_mean: bool, fun_stabil: bool) -> (f64, f64, Vec<bool>) {
    let n = x.len();
    if n == 0 {
        return (0.0, 0.0, vec![]);
    }

    let nan_mask: Vec<bool> = x.iter().map(|v| v.is_finite()).collect();
    let mut selected: Vec<bool> = nan_mask.clone();

    let (mut mean, mut std) = if fun_mean {
        let s: Vec<f64> = x.iter().zip(selected.iter()).filter(|(_, &m)| m).map(|(&v, _)| v).collect();
        let m = if s.is_empty() { 0.0 } else { s.iter().sum::<f64>() / s.len() as f64 };
        let v = if s.len() > 1 {
            s.iter().map(|&v| (v - m).powi(2)).sum::<f64>() / (s.len() - 1) as f64
        } else {
            0.0
        };
        (m, v.sqrt())
    } else {
        let s: Vec<f64> = x.iter().zip(selected.iter()).filter(|(_, &m)| m).map(|(&v, _)| v).collect();
        let v = if s.len() > 1 {
            s.iter().map(|&v| v.powi(2)).sum::<f64>() / (s.len() - 1) as f64
        } else {
            0.0
        };
        (0.0, v.sqrt())
    };

    if fun_stabil && selected.iter().filter(|&&v| v).count() > 1 {
        let mut selected0 = nan_mask;
        // Update selection: |x - mean| < 3*std
        selected = x.iter().map(|&v| v.is_finite() && (v - mean).abs() < 3.0 * std).collect();

        while selected.iter().filter(|&&v| v).count() < selected0.iter().filter(|&&v| v).count() {
            let s: Vec<f64> = x.iter().zip(selected.iter()).filter(|(_, &m)| m).map(|(&v, _)| v).collect();
            if fun_mean {
                mean = if s.is_empty() { 0.0 } else { s.iter().sum::<f64>() / s.len() as f64 };
            }
            std = if s.len() > 1 {
                let base: f64 = if fun_mean { mean } else { 0.0 };
                (s.iter().map(|&v| (v - base).powi(2)).sum::<f64>() / (s.len() - 1) as f64).sqrt()
            } else {
                0.0
            };
            selected0 = selected.clone();
            selected = x.iter().map(|&v| v.is_finite() && (v - mean).abs() < 3.0 * std).collect();
        }
    }

    (std, mean, selected)
}
