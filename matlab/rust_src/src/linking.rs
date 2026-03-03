use ndarray::Array2;
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone)]
pub struct Spot {
    pub spot_id: usize,
    pub frame: usize,
    pub position: usize,
    pub position_refined: f64,
    pub intensity: f64,
    pub contrast: f64,
}

#[derive(Debug, Clone)]
pub struct Tracklet {
    pub spot_ids: Vec<usize>,
    pub frames: Vec<usize>,
    pub positions: Vec<usize>,
    pub positions_refined: Vec<f64>,
    pub intensities: Vec<f64>,
    pub contrasts: Vec<f64>,
}

#[derive(Debug, Clone)]
pub struct Track {
    pub frames: Vec<usize>,
    pub positions: Vec<usize>,
    pub positions_refined: Vec<f64>,
    pub intensities: Vec<f64>,
    pub contrasts: Vec<f64>,
}

pub fn spot_linking(
    spots: &[Spot],
    n_frames: usize,
    cut_off_distance: f64,
    unmatched_penalty_distance: f64,
    flow_estimate: f64,
) -> Vec<(usize, usize, f64)> {
    // Pre-group spots by frame — O(1) lookup instead of O(nSpots) scan per frame pair
    let mut spots_by_frame: Vec<Vec<usize>> = vec![Vec::new(); n_frames];
    for (idx, s) in spots.iter().enumerate() {
        if s.frame < n_frames {
            spots_by_frame[s.frame].push(idx);
        }
    }

    let cut2 = cut_off_distance.powi(2);
    let penalty2 = unmatched_penalty_distance.powi(2);
    let mut edges: Vec<(usize, usize, f64)> = Vec::new();

    for src_frame in 0..n_frames.saturating_sub(1) {
        let tgt_frame = src_frame + 1;
        let src_idxs = &spots_by_frame[src_frame];
        let tgt_idxs = &spots_by_frame[tgt_frame];

        if src_idxs.is_empty() || tgt_idxs.is_empty() {
            continue;
        }

        let ns = src_idxs.len();
        let nt = tgt_idxs.len();

        let mut cost = vec![vec![f64::INFINITY; nt]; ns];
        for (i, &si) in src_idxs.iter().enumerate() {
            for (j, &ti) in tgt_idxs.iter().enumerate() {
                let d = (spots[si].position_refined
                    - (spots[ti].position_refined - flow_estimate))
                    .powi(2);
                if d <= cut2 {
                    cost[i][j] = d;
                }
            }
        }

        for (si, ti) in match_pairs_lap(&cost, penalty2) {
            let jump = spots[tgt_idxs[ti]].position_refined
                - spots[src_idxs[si]].position_refined;
            edges.push((spots[src_idxs[si]].spot_id, spots[tgt_idxs[ti]].spot_id, jump));
        }
    }

    edges
}

pub fn join_linked_spots(edges: &[(usize, usize, f64)], spots: &[Spot]) -> Vec<Tracklet> {
    let spot_map: HashMap<usize, usize> =
        spots.iter().enumerate().map(|(i, s)| (s.spot_id, i)).collect();

    let mut tracklets: Vec<Vec<usize>> = Vec::new();
    // tail_spot_id → tracklet index for O(1) append lookup
    let mut tail_to_tl: HashMap<usize, usize> = HashMap::new();

    for &(src, tgt, _) in edges {
        if let Some(&tl_idx) = tail_to_tl.get(&src) {
            tracklets[tl_idx].push(tgt);
            tail_to_tl.remove(&src);
            tail_to_tl.insert(tgt, tl_idx);
        } else {
            let idx = tracklets.len();
            tracklets.push(vec![src, tgt]);
            tail_to_tl.insert(tgt, idx);
        }
    }

    tracklets
        .into_iter()
        .map(|ids| {
            let frames: Vec<usize> = ids.iter().map(|id| spots[spot_map[id]].frame).collect();
            let positions: Vec<usize> = ids.iter().map(|id| spots[spot_map[id]].position).collect();
            let positions_refined: Vec<f64> =
                ids.iter().map(|id| spots[spot_map[id]].position_refined).collect();
            let intensities: Vec<f64> = ids.iter().map(|id| spots[spot_map[id]].intensity).collect();
            let contrasts: Vec<f64> = ids.iter().map(|id| spots[spot_map[id]].contrast).collect();
            Tracklet { spot_ids: ids, frames, positions, positions_refined, intensities, contrasts }
        })
        .collect()
}

pub fn tracklet_linking(
    tracklets: &[Tracklet],
    max_negative_gap: i32,
    max_positive_gap: i32,
    gap_cut_off: f64,
    gap_penalty: f64,
    flow_estimate: f64,
) -> (Vec<(usize, usize)>, Vec<usize>) {
    let n = tracklets.len();
    if n == 0 {
        return (vec![], vec![]);
    }

    let cut2 = gap_cut_off.powi(2);
    let mut cost = vec![vec![f64::INFINITY; n]; n];

    for i in 0..n {
        let src_end_frame = *tracklets[i].frames.last().unwrap() as i32;
        let src_end_pos = tracklets[i].positions_refined.last().unwrap()
            - flow_estimate * src_end_frame as f64;

        for j in 0..n {
            if i == j {
                continue;
            }
            let dst_start_frame = tracklets[j].frames[0] as i32;
            let frame_diff = dst_start_frame - src_end_frame;
            if frame_diff < 1 - max_negative_gap || frame_diff > max_positive_gap + 1 {
                continue;
            }

            let dst_start_pos = tracklets[j].positions_refined[0]
                - flow_estimate * dst_start_frame as f64;

            let d = (src_end_pos - dst_start_pos).powi(2);
            if d <= cut2 {
                cost[i][j] = d;
            }
        }
    }

    let matches = match_pairs_lap(&cost, gap_penalty.powi(2));

    let matched_sources: HashSet<usize> = matches.iter().map(|&(i, _)| i).collect();
    let unmatched_rows: Vec<usize> = (0..n).filter(|i| !matched_sources.contains(i)).collect();

    (matches, unmatched_rows)
}

pub fn join_linked_tracklets(
    matches: &[(usize, usize)],
    unmatched_rows: &[usize],
    tracklets: &[Tracklet],
) -> Vec<Track> {
    let mut chains: Vec<Vec<usize>> = Vec::new();
    // tail_tl_id → chain index for O(1) append lookup
    let mut tail_to_chain: HashMap<usize, usize> = HashMap::new();

    for &(src, dst) in matches {
        if let Some(&chain_idx) = tail_to_chain.get(&src) {
            chains[chain_idx].push(dst);
            tail_to_chain.remove(&src);
            tail_to_chain.insert(dst, chain_idx);
        } else {
            let idx = chains.len();
            chains.push(vec![src, dst]);
            tail_to_chain.insert(dst, idx);
        }
    }

    // Collect all tracklet IDs already in chains
    let in_chains: HashSet<usize> = chains.iter().flat_map(|c| c.iter().copied()).collect();

    // Unmatched rows not yet in any chain become single-tracklet tracks
    for &row in unmatched_rows {
        if !in_chains.contains(&row) {
            chains.push(vec![row]);
        }
    }

    // Any tracklet not in any chain at all
    for i in 0..tracklets.len() {
        if !in_chains.contains(&i) {
            // check it wasn't just added above
            if !chains.iter().any(|c| c.contains(&i)) {
                chains.push(vec![i]);
            }
        }
    }

    chains
        .into_iter()
        .map(|tl_ids| {
            let frames: Vec<usize> = tl_ids.iter().flat_map(|&ti| tracklets[ti].frames.iter().copied()).collect();
            let positions: Vec<usize> = tl_ids.iter().flat_map(|&ti| tracklets[ti].positions.iter().copied()).collect();
            let positions_refined: Vec<f64> = tl_ids.iter().flat_map(|&ti| tracklets[ti].positions_refined.iter().copied()).collect();
            let intensities: Vec<f64> = tl_ids.iter().flat_map(|&ti| tracklets[ti].intensities.iter().copied()).collect();
            let contrasts: Vec<f64> = tl_ids.iter().flat_map(|&ti| tracklets[ti].contrasts.iter().copied()).collect();
            Track { frames, positions, positions_refined, intensities, contrasts }
        })
        .collect()
}

fn match_pairs_lap(cost: &[Vec<f64>], penalty: f64) -> Vec<(usize, usize)> {
    let ns = cost.len();
    if ns == 0 {
        return vec![];
    }
    let nt = cost[0].len();
    if nt == 0 {
        return vec![];
    }

    let n = ns + nt;
    let mut aug = vec![f64::INFINITY; n * n];

    for i in 0..ns {
        for j in 0..nt {
            aug[i * n + j] = cost[i][j];
        }
    }
    for j in 0..nt {
        aug[(ns + j) * n + j] = penalty;
    }
    for i in 0..ns {
        aug[i * n + (nt + i)] = penalty;
    }
    for i in 0..nt {
        for j in 0..ns {
            aug[(ns + i) * n + (nt + j)] = 0.0;
        }
    }

    let big = penalty * 1e9;
    for v in &mut aug {
        if !v.is_finite() {
            *v = big;
        }
    }

    let aug_matrix = Array2::from_shape_vec((n, n), aug).unwrap();
    let (row_sol, _col_sol) = match lapjv::lapjv(&aug_matrix) {
        Ok(sol) => sol,
        Err(_) => return vec![],
    };

    let mut matches = Vec::new();
    for i in 0..ns {
        let j = row_sol[i];
        if j < nt && cost[i][j].is_finite() {
            matches.push((i, j));
        }
    }
    matches
}
