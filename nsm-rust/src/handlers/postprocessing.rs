use std::collections::HashMap;

use axum::{
    extract::{Query, State},
    http::HeaderMap,
    response::Html,
    Form, Json,
};
use serde::{Deserialize, Serialize};
use tera::Context;

use crate::{
    algorithms::{
        calibration::run_ioc_calibration,
        outlier_filtering::find_outliers,
    },
    error::AppError,
    job_manager::job_dirs,
    models::{
        compute_states, Collection, ThresholdConfig, TrajectoryOverride,
        TrajectoryState,
    },
    state::SharedState,
};

#[derive(Deserialize)]
pub struct PpQuery {
    pub job_id: Option<String>,
}

pub async fn page(
    State(state): State<SharedState>,
    Query(q): Query<PpQuery>,
    headers: HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "Post-processing");

    if let Some(ref job_id) = q.job_id {
        let nsm_cfg = state.load_nsm_config_for_job(job_id).unwrap_or_default();
        let filt    = &nsm_cfg.outlier_filtering;
        let pp = state.get_or_init_pp_state(
            job_id,
            &filt.filter_properties,
            &filt.threshold_direction,
            &filt.threshold_value,
        ).await;

        match state.get_or_load_collection(job_id).await {
            Ok(col) => {
                let not_outlier = find_outliers(&col, filt, &pp.thresholds);
                let states      = compute_states(col.len(), &not_outlier, &pp.overrides);
                let scatter_json = build_scatter_json(&col, &states, &pp.axis_x, &pp.axis_y);
                let traj_json    = build_trajectory_json(&col, &states);
                let kept  = states.iter().filter(|s| s.is_kept()).count();
                let total = col.len();

                ctx.insert("job_id",       job_id);
                ctx.insert("scatter_json", &scatter_json);
                ctx.insert("traj_json",    &traj_json);
                ctx.insert("filter_props", &filt.filter_properties);
                ctx.insert("thresholds",   &pp.thresholds);
                ctx.insert("axis_x",       &pp.axis_x);
                ctx.insert("axis_y",       &pp.axis_y);
                ctx.insert("ioc_cal_on",   &pp.ioc_cal_on);
                ctx.insert("kept",         &kept);
                ctx.insert("total",        &total);
                ctx.insert("scalar_props", &crate::SCALAR_PROPS);
                ctx.insert("error",        &Option::<String>::None);
            }
            Err(e) => {
                ctx.insert("job_id", job_id);
                ctx.insert("error",  &Some(format!("Could not load collection.mat: {e}")));
            }
        }
    } else {
        ctx.insert("job_id", &Option::<String>::None);
        ctx.insert("error",  &Option::<String>::None);
    }

    super::pages::render_page(&state, "postprocessing.html", &mut ctx, crate::state::is_htmx(&headers))
}

// ── Threshold update ──────────────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct ThresholdForm {
    pub job_id:     String,
    pub thresholds: HashMap<String, ThresholdConfig>,
    pub axis_x:     Option<String>,
    pub axis_y:     Option<String>,
}

pub async fn update_thresholds(
    State(state): State<SharedState>,
    Form(form): Form<ThresholdForm>,
) -> Result<Html<String>, AppError> {
    {
        let mut map = state.pp_states.write().await;
        if let Some(pp) = map.get_mut(&form.job_id) {
            pp.thresholds = form.thresholds;
            if let Some(ax) = form.axis_x { pp.axis_x = ax; }
            if let Some(ay) = form.axis_y { pp.axis_y = ay; }
        }
    }
    render_pp_fragment(&state, &form.job_id).await
}

// ── Manual override ───────────────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct OverridePayload {
    pub job_id:  String,
    pub indices: Vec<usize>,
    pub action:  String, // "keep" | "exclude" | "clear"
}

pub async fn handle_override(
    State(state): State<SharedState>,
    Json(payload): Json<OverridePayload>,
) -> Result<Html<String>, AppError> {
    {
        let mut map = state.pp_states.write().await;
        if let Some(pp) = map.get_mut(&payload.job_id) {
            for &i in &payload.indices {
                match payload.action.as_str() {
                    "keep"    => { pp.overrides.insert(i, TrajectoryOverride::Kept); }
                    "exclude" => { pp.overrides.insert(i, TrajectoryOverride::Excluded); }
                    "clear"   => { pp.overrides.remove(&i); }
                    "reset"   => { pp.overrides.clear(); break; }
                    _         => {}
                }
            }
        }
    }
    render_pp_fragment(&state, &payload.job_id).await
}

// ── Accept & Save ─────────────────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct AcceptForm {
    pub job_id:    String,
    pub ioc_cal:   Option<String>, // "on" when checkbox checked
}

pub async fn accept(
    State(state): State<SharedState>,
    Form(form): Form<AcceptForm>,
) -> Result<Html<String>, AppError> {
    let col = state.get_or_load_collection(&form.job_id).await?;
    let nsm_cfg = state.load_nsm_config_for_job(&form.job_id).unwrap_or_default();
    let filt = &nsm_cfg.outlier_filtering;
    let pp = {
        let map = state.pp_states.read().await;
        map.get(&form.job_id).cloned()
    };
    let pp = match pp {
        Some(p) => p,
        None => state.get_or_init_pp_state(&form.job_id, &filt.filter_properties, &filt.threshold_direction, &filt.threshold_value).await,
    };

    let not_outlier = find_outliers(&col, filt, &pp.thresholds);
    let states      = compute_states(col.len(), &not_outlier, &pp.overrides);
    let keep_mask: Vec<bool> = states.iter().map(|s| s.is_kept()).collect();
    let n_kept  = keep_mask.iter().filter(|&&k| k).count();
    let n_total = keep_mask.len();

    let ioc_cal_on = form.ioc_cal.as_deref() == Some("on");
    let (calibration, col_out) = if ioc_cal_on
        && !col.ioc_profile.is_empty()
        && !col.position_refined.is_empty()
    {
        match run_ioc_calibration(&col, &keep_mask) {
            Ok(r) => (Some(r.0), r.1),
            Err(e) => {
                tracing::warn!("iOC calibration failed: {e}");
                (None, (*col).clone())
            }
        }
    } else {
        (None, (*col).clone())
    };

    let filtered = col_out.filter(&keep_mask);
    let (_, _, out) = job_dirs(&state.config.data_dir, &form.job_id);
    let json = serde_json::json!({
        "collection": filtered,
        "calibration": calibration,
        "n_kept": n_kept,
        "n_total": n_total,
    });
    std::fs::write(out.join("collection_postprocessed.json"), serde_json::to_string_pretty(&json)?)?;

    let mut ctx = Context::new();
    ctx.insert("job_id",    &form.job_id);
    ctx.insert("n_kept",    &n_kept);
    ctx.insert("n_total",   &n_total);
    ctx.insert("cal_done",  &calibration.is_some());
    Ok(Html(state.tera.render("accept_result.html", &ctx)?))
}

// ── Shared fragment renderer ──────────────────────────────────────────────────

async fn render_pp_fragment(
    state:  &SharedState,
    job_id: &str,
) -> Result<Html<String>, AppError> {
    let col = state.get_or_load_collection(job_id).await?;
    let nsm_cfg = state.load_nsm_config_for_job(job_id).unwrap_or_default();
    let filt = &nsm_cfg.outlier_filtering;
    let pp = {
        let map = state.pp_states.read().await;
        map.get(job_id).cloned().unwrap_or_else(|| crate::models::PostprocessingState {
            thresholds: HashMap::new(),
            overrides: HashMap::new(),
            axis_x: "iOC".into(),
            axis_y: "velocity".into(),
            ioc_cal_on: true,
        })
    };

    let not_outlier = find_outliers(&col, filt, &pp.thresholds);
    let states      = compute_states(col.len(), &not_outlier, &pp.overrides);
    let scatter_json = build_scatter_json(&col, &states, &pp.axis_x, &pp.axis_y);
    let kept  = states.iter().filter(|s| s.is_kept()).count();
    let total = col.len();

    let mut ctx = Context::new();
    ctx.insert("job_id",       job_id);
    ctx.insert("scatter_json", &scatter_json);
    ctx.insert("filter_props", &filt.filter_properties);
    ctx.insert("thresholds",   &pp.thresholds);
    ctx.insert("axis_x",       &pp.axis_x);
    ctx.insert("axis_y",       &pp.axis_y);
    ctx.insert("ioc_cal_on",   &pp.ioc_cal_on);
    ctx.insert("kept",         &kept);
    ctx.insert("total",        &total);
    ctx.insert("scalar_props", &crate::SCALAR_PROPS);
    Ok(Html(state.tera.render("pp_fragment.html", &ctx)?))
}

// ── Scatter plot JSON builder ─────────────────────────────────────────────────

fn build_scatter_json(
    col:    &Collection,
    states: &[TrajectoryState],
    x_prop: &str,
    y_prop: &str,
) -> String {
    let x_vals = col.scalar_prop(x_prop).map(|v| v.as_slice()).unwrap_or(&[]);
    let y_vals = col.scalar_prop(y_prop).map(|v| v.as_slice()).unwrap_or(&[]);

    let all_state_types = [
        TrajectoryState::AutoKept,
        TrajectoryState::AutoExcluded,
        TrajectoryState::ManualKept,
        TrajectoryState::ManualExcluded,
    ];

    let mut traces = Vec::new();
    for &state_type in &all_state_types {
        let idx: Vec<usize> = states.iter().enumerate()
            .filter(|(_, &s)| s == state_type)
            .map(|(i, _)| i)
            .collect();
        if idx.is_empty() { continue; }

        let xs: Vec<f64> = idx.iter().filter_map(|&i| x_vals.get(i)).cloned().collect();
        let ys: Vec<f64> = idx.iter().filter_map(|&i| y_vals.get(i)).cloned().collect();
        let custom: Vec<[usize; 1]> = idx.iter().map(|&i| [i]).collect();

        traces.push(serde_json::json!({
            "x": xs,
            "y": ys,
            "mode": "markers",
            "name": state_type.label(),
            "marker": {
                "size": 9,
                "color": state_type.color(),
                "symbol": state_type.symbol(),
                "line": { "width": 1, "color": state_type.color() }
            },
            "customdata": custom,
            "hovertemplate": format!(
                "{x_prop}: %{{x:.4f}}<br>{y_prop}: %{{y:.4f}}<br>idx: %{{customdata[0]}}<extra>{}</extra>",
                state_type.label()
            ),
            "type": "scatter"
        }));
    }

    let layout = serde_json::json!({
        "xaxis_title": x_prop,
        "yaxis_title": y_prop,
        "dragmode": "lasso",
        "height": 450,
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        "paper_bgcolor": "#1e1e2e",
        "plot_bgcolor": "#1e1e2e",
        "font": {"color": "#cdd6f4"}
    });

    serde_json::json!({"data": traces, "layout": layout}).to_string()
}

// ── Trajectory data for track preview ─────────────────────────────────────────

#[derive(Serialize)]
struct TrajectoryData {
    index:    usize,
    frames:   Vec<f64>,
    positions: Vec<f64>,
    state:    String,
    kymo_key: String,
}

fn build_trajectory_json(col: &Collection, states: &[TrajectoryState]) -> String {
    let mut trajs = Vec::new();
    for (i, state) in states.iter().enumerate() {
        if i >= col.position_refined.len() { break; }
        let frames = if i < col.time_frame.len() && !col.time_frame[i].is_empty() {
            col.time_frame[i].clone()
        } else {
            (0..col.position_refined[i].len()).map(|j| j as f64).collect()
        };
        let kymo_key = col.experiment_time_stamp.get(i)
            .cloned()
            .unwrap_or_else(|| "all".into());
        trajs.push(TrajectoryData {
            index:     i,
            frames,
            positions: col.position_refined[i].clone(),
            state:     state.label().into(),
            kymo_key,
        });
    }
    serde_json::to_string(&trajs).unwrap_or_else(|_| "[]".into())
}
