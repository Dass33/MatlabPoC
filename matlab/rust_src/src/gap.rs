use crate::linking::Track;
use crate::refinement::refine_centroid;
use crate::detection::Detection;

/// Delete spots that cause frame deltas < 1 (overlapping/reversed).
/// Keeps the spot with lower intensity value (more negative = stronger for negative peaks).
pub fn delete_negative_gap_spots(mut tracks: Vec<Track>) -> Vec<Track> {
    for track in &mut tracks {
        let mut i = 0;
        while i + 1 < track.frames.len() {
            let delta = track.frames[i + 1] as i64 - track.frames[i] as i64;
            if delta < 1 {
                // Keep spot with lower intensity (more extreme for negative peaks)
                if track.intensities[i] <= track.intensities[i + 1] {
                    // delete i+1
                    track.frames.remove(i + 1);
                    track.positions.remove(i + 1);
                    track.positions_refined.remove(i + 1);
                    track.intensities.remove(i + 1);
                    track.contrasts.remove(i + 1);
                } else {
                    // delete i
                    track.frames.remove(i);
                    track.positions.remove(i);
                    track.positions_refined.remove(i);
                    track.intensities.remove(i);
                    track.contrasts.remove(i);
                    if i > 0 {
                        i -= 1;
                    }
                }
            } else {
                i += 1;
            }
        }
    }
    tracks
}

/// Filter tracks shorter than min_track_length frames.
/// Track "length" = last_frame - first_frame (matching MATLAB's track_length > minTrackLength).
pub fn filter_tracks(tracks: Vec<Track>, min_track_length: usize) -> Vec<Track> {
    tracks
        .into_iter()
        .filter(|t| {
            if t.frames.is_empty() {
                return false;
            }
            let length = t.frames.last().unwrap() - t.frames[0];
            length > min_track_length
        })
        .collect()
}

/// Fill gaps in tracks: linearly interpolate positions, then snap to local optimum.
pub fn gap_filling(
    mut tracks: Vec<Track>,
    c: &[Vec<f64>],
    peak_sign: &str,
    gap_local_optimum_range: usize,
    fitting_radius: usize,
) -> Vec<Track> {
    let nx = if !c.is_empty() { c[0].len() } else { 0 };

    for track in &mut tracks {
        let mut i = 0;
        // Collect gap info before modifying, then insert
        while i + 1 < track.frames.len() {
            let f0 = track.frames[i];
            let f1 = track.frames[i + 1];
            if f1 > f0 + 1 {
                // Gap: fill frames f0+1 .. f1-1
                let gap_len = (f1 - f0 - 1) as usize;
                let p0 = track.positions[i] as f64;
                let p1 = track.positions[i + 1] as f64;

                let mut new_frames = Vec::with_capacity(gap_len);
                let mut new_positions = Vec::with_capacity(gap_len);
                let mut new_positions_refined = Vec::with_capacity(gap_len);
                let mut new_intensities = Vec::with_capacity(gap_len);
                let mut new_contrasts = Vec::with_capacity(gap_len);

                for k in 0..gap_len {
                    let t = f0 + 1 + k;
                    // Linearly interpolate position
                    let frac = (k + 1) as f64 / (gap_len + 1) as f64;
                    let p_line = (p0 + frac * (p1 - p0)).round() as usize;

                    // Snap to local optimum
                    let lo = p_line.saturating_sub(gap_local_optimum_range);
                    let hi = (p_line + gap_local_optimum_range).min(nx - 1);
                    let range = &c[t][lo..=hi];

                    let best_local = match peak_sign {
                        "negative" => range
                            .iter()
                            .enumerate()
                            .min_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
                            .map(|(idx, _)| lo + idx)
                            .unwrap_or(p_line),
                        "positive" => range
                            .iter()
                            .enumerate()
                            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
                            .map(|(idx, _)| lo + idx)
                            .unwrap_or(p_line),
                        _ => p_line,
                    };

                    let intensity = c[t][best_local];
                    let contrast = c[t][best_local];

                    // Refine position
                    let dummy_det = Detection {
                        frame: t,
                        position: best_local,
                        intensity,
                    };
                    let refined_vec = refine_centroid(&[dummy_det], c, fitting_radius);
                    let refined = refined_vec[0];

                    new_frames.push(t);
                    new_positions.push(best_local);
                    new_positions_refined.push(refined);
                    new_intensities.push(intensity);
                    new_contrasts.push(contrast);
                }

                // Splice all gap frames in one operation — O(n) instead of O(n*gap_len)
                let insert_at = i + 1;
                track.frames.splice(insert_at..insert_at, new_frames);
                track.positions.splice(insert_at..insert_at, new_positions);
                track.positions_refined.splice(insert_at..insert_at, new_positions_refined);
                track.intensities.splice(insert_at..insert_at, new_intensities);
                track.contrasts.splice(insert_at..insert_at, new_contrasts);

                // Skip past inserted elements
                i += gap_len + 1;
            } else {
                i += 1;
            }
        }
    }
    tracks
}

/// Compute std_jump_distance from jump distances of all edges.
pub fn compute_gap_local_optimum_range(jump_distances: &[f64]) -> usize {
    if jump_distances.is_empty() {
        return 1;
    }
    let n = jump_distances.len() as f64;
    let mean = jump_distances.iter().sum::<f64>() / n;
    let var = jump_distances.iter().map(|&d| (d - mean).powi(2)).sum::<f64>() / n;
    let std = var.sqrt();
    // MATLAB: gap_local_optimum_range = 2*round(std_jump_distance)
    (2.0 * std.round()) as usize
}
