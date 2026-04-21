use axum::{
    extract::{Multipart, State},
    http::HeaderMap,
    response::{Html, IntoResponse, Redirect},
};
use tera::Context;

use crate::{
    docker_runner::launch_matlab_container,
    error::AppError,
    job_manager::{count_running_jobs, create_job, SubmitFiles},
    models::NsmConfig,
    state::SharedState,
};

pub async fn page(
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "Submit");
    ctx.insert("max_workers", &state.config.max_workers);
    ctx.insert("running_jobs", &count_running_jobs(&state.config.data_dir));
    ctx.insert("default_config", &serde_json::to_value(NsmConfig::default())?);
    super::pages::render_page(&state, "submit.html", &mut ctx, crate::state::is_htmx(&headers))
}

pub async fn handle_submit(
    State(state): State<SharedState>,
    mut multipart: Multipart,
) -> Result<impl IntoResponse, AppError> {
    let running = count_running_jobs(&state.config.data_dir);
    if running >= state.config.max_workers {
        return Err(AppError::BadRequest(format!(
            "All {max} worker slots busy ({running} running). Wait for a job to finish.",
            max = state.config.max_workers
        )));
    }

    let mut name          = String::new();
    let mut config_json   = String::new();
    let mut file_bytes:   Vec<(String, Vec<u8>)> = Vec::new();
    let mut filenames     = Vec::new();
    let mut dark_cal_bytes: Option<Vec<u8>> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| AppError::BadRequest(e.to_string()))? {
        let field_name = field.name().unwrap_or("").to_owned();
        match field_name.as_str() {
            "name"        => name        = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?,
            "config_json" => config_json = field.text().await.map_err(|e| AppError::BadRequest(e.to_string()))?,
            "dark_cal"    => {
                let bytes = field.bytes().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                if !bytes.is_empty() { dark_cal_bytes = Some(bytes.to_vec()); }
            }
            "files" => {
                let fname = field.file_name().unwrap_or("unknown").to_owned();
                let bytes = field.bytes().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
                filenames.push(fname.clone());
                file_bytes.push((fname, bytes.to_vec()));
            }
            _ => { let _ = field.bytes().await; }
        }
    }

    if file_bytes.is_empty() {
        return Err(AppError::BadRequest("No files uploaded.".into()));
    }

    // Validate TIFF/TXT pairing
    let tiff_stems: std::collections::HashSet<String> = file_bytes.iter()
        .filter(|(n, _)| n.ends_with(".tiff") || n.ends_with(".tif"))
        .map(|(n, _)| n.trim_end_matches(".tiff").trim_end_matches(".tif").to_owned())
        .collect();
    let txt_stems: std::collections::HashSet<String> = file_bytes.iter()
        .filter(|(n, _)| n.ends_with(".txt"))
        .map(|(n, _)| n.trim_end_matches(".txt").to_owned())
        .collect();
    let missing: Vec<&str> = tiff_stems.iter()
        .filter(|s| !txt_stems.contains(*s))
        .map(|s| s.as_str())
        .collect();
    if !missing.is_empty() {
        return Err(AppError::BadRequest(format!("Missing .txt metadata for: {:?}", missing)));
    }

    let config_val: serde_json::Value = if config_json.is_empty() {
        serde_json::to_value(NsmConfig::default())?
    } else {
        serde_json::from_str(&config_json)?
    };

    let submit = SubmitFiles { name, filenames, file_bytes, config: config_val, dark_cal_bytes };
    let job_id = create_job(&state.config.data_dir, &submit)?;

    launch_matlab_container(&state.docker, &state.config, &job_id).await?;

    Ok(Redirect::to(&format!("/history?submitted={job_id}")))
}
