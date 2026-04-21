use std::collections::HashMap;

use axum::{
    extract::{Query, State},
    http::HeaderMap,
    response::Html,
    Form,
};
use serde::Deserialize;
use tera::Context;

use crate::{
    algorithms::population::{gauss_fit, robust_mean},
    error::AppError,
    job_manager::job_dirs,
    state::SharedState,
};

const AVAILABLE_PROPS: &[&str] = &[
    "iOC", "D", "STDiOC", "velocity", "N", "positionStart", "positionEnd",
];

#[derive(Deserialize)]
pub struct PopQuery {
    pub job_id: Option<String>,
}

pub async fn page(
    State(state): State<SharedState>,
    Query(q): Query<PopQuery>,
    headers: HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "Population Analysis");

    if let Some(ref job_id) = q.job_id {
        let (_, _, out) = job_dirs(&state.config.data_dir, job_id);
        let pp_path = out.join("collection_postprocessed.json");
        if pp_path.exists() {
            let data: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&pp_path)?)?;
            let n_kept  = data.get("n_kept").and_then(|v| v.as_u64()).unwrap_or(0);
            let n_total = data.get("n_total").and_then(|v| v.as_u64()).unwrap_or(0);
            ctx.insert("job_id",   job_id);
            ctx.insert("n_kept",   &n_kept);
            ctx.insert("n_total",  &n_total);
            ctx.insert("has_data", &true);

            // Available properties (those present in collection)
            let col = data.get("collection").cloned().unwrap_or(serde_json::Value::Null);
            let available: Vec<&str> = AVAILABLE_PROPS.iter()
                .filter(|&&p| col.get(p).is_some())
                .cloned()
                .collect();
            ctx.insert("available_props", &available);

            // Previously cached result
            let pop_cache = state.pop_results.read().await;
            if let Some(r) = pop_cache.get(job_id) {
                ctx.insert("pop_result", r);
            }
        } else {
            ctx.insert("job_id",   job_id);
            ctx.insert("has_data", &false);
        }
    } else {
        ctx.insert("job_id",   &Option::<String>::None);
        ctx.insert("has_data", &false);
    }

    super::pages::render_page(&state, "population.html", &mut ctx, crate::state::is_htmx(&headers))
}

#[derive(Deserialize)]
pub struct RunForm {
    pub job_id:  String,
    pub method:  String,
    pub props:   Vec<String>, // multi-value form field
}

pub async fn run(
    State(state): State<SharedState>,
    Form(form): Form<RunForm>,
) -> Result<Html<String>, AppError> {
    let (_, _, out) = job_dirs(&state.config.data_dir, &form.job_id);
    let pp_path = out.join("collection_postprocessed.json");
    if !pp_path.exists() {
        return Err(AppError::NotFound("collection_postprocessed.json not found".into()));
    }

    let data: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&pp_path)?)?;
    let col_val = data.get("collection").ok_or_else(|| AppError::BadRequest("No collection in postprocessed file".into()))?;
    let collection: crate::models::Collection = serde_json::from_value(col_val.clone())?;

    let props_str: Vec<&str> = form.props.iter().map(|s| s.as_str()).collect();
    let result = match form.method.as_str() {
        "gaussFit"   => gauss_fit(&collection, &props_str),
        _            => robust_mean(&collection, &props_str),
    };

    // Save population.json
    let n_kept = data.get("n_kept").and_then(|v| v.as_u64());
    let pop_json = serde_json::json!({
        "method": form.method,
        "properties": form.props,
        "n_trajectories": n_kept,
        "results": result.iter().map(|(k, v)| {
            let mut obj = serde_json::to_value(v).unwrap();
            // remove internal histogram fields for the saved file
            if let Some(o) = obj.as_object_mut() {
                o.remove("_hist_centers");
                o.remove("_hist_counts");
            }
            (k.clone(), obj)
        }).collect::<HashMap<_, _>>()
    });
    std::fs::write(out.join("population.json"), serde_json::to_string_pretty(&pop_json)?)?;

    // Cache result
    state.pop_results.write().await.insert(form.job_id.clone(), result.clone());

    // Render histograms JSON for Plotly
    let hist_data = build_histogram_json(&collection, &result, &props_str, &form.method);

    let mut ctx = Context::new();
    ctx.insert("job_id",      &form.job_id);
    ctx.insert("method",      &form.method);
    ctx.insert("props",       &form.props);
    ctx.insert("result",      &result);
    ctx.insert("hist_json",   &hist_data);
    ctx.insert("props_order", &form.props);
    Ok(Html(state.tera.render("pop_results.html", &ctx)?))
}

fn build_histogram_json(
    collection: &crate::models::Collection,
    result:     &HashMap<String, crate::models::PropStats>,
    props:      &[&str],
    method:     &str,
) -> String {
    use serde_json::json;
    let mut subplots = Vec::new();
    for (i, &prop) in props.iter().enumerate() {
        let y_vals: Vec<f64> = collection.scalar_prop(prop)
            .map(|v| v.iter().cloned().filter(|x| x.is_finite()).collect())
            .unwrap_or_default();
        if y_vals.is_empty() { continue; }

        let stats = result.get(prop);
        let trace = json!({
            "type": "histogram",
            "x": y_vals,
            "nbinsx": 20,
            "marker": { "color": "#4C72B0", "opacity": 0.7 },
            "name": prop,
            "showlegend": false,
            "xaxis": format!("x{}", if i == 0 { "".into() } else { (i + 1).to_string() }),
            "yaxis": format!("y{}", if i == 0 { "".into() } else { (i + 1).to_string() }),
        });
        subplots.push(json!({"trace": trace, "mean": stats.map(|s| s.mean)}));
    }
    serde_json::to_string(&subplots).unwrap_or_else(|_| "[]".into())
}
