use axum::{
    extract::{Multipart, State},
    http::header,
    response::{IntoResponse, Response},
    Json,
};

use crate::{error::AppError, models::NsmConfig, state::SharedState};

/// GET /api/config/default → returns default NsmConfig as JSON download
pub async fn get_default(State(_state): State<SharedState>) -> Result<Response, AppError> {
    let json = serde_json::to_string_pretty(&NsmConfig::default())?;
    Ok((
        [
            (header::CONTENT_TYPE,        "application/json".to_owned()),
            (header::CONTENT_DISPOSITION, "attachment; filename=\"default_config.json\"".to_owned()),
        ],
        json,
    ).into_response())
}

/// POST /api/config/upload → parse uploaded JSON, return it as JSON
pub async fn upload(
    State(_state): State<SharedState>,
    mut multipart: Multipart,
) -> Result<Json<NsmConfig>, AppError> {
    while let Some(field) = multipart.next_field().await
        .map_err(|e| AppError::BadRequest(e.to_string()))?
    {
        let bytes = field.bytes().await.map_err(|e| AppError::BadRequest(e.to_string()))?;
        let cfg: NsmConfig = serde_json::from_slice(&bytes)?;
        return Ok(Json(cfg));
    }
    Err(AppError::BadRequest("No file uploaded".into()))
}

/// GET /api/config/download?job_id=... → download the config for a specific job
pub async fn download(
    State(state): State<SharedState>,
    axum::extract::Query(params): axum::extract::Query<std::collections::HashMap<String, String>>,
) -> Result<Response, AppError> {
    let cfg_val = if let Some(job_id) = params.get("job_id") {
        let path = state.job_config_path(job_id);
        if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            serde_json::from_str::<serde_json::Value>(&text)?
        } else {
            serde_json::to_value(NsmConfig::default())?
        }
    } else {
        serde_json::to_value(NsmConfig::default())?
    };

    let json = serde_json::to_string_pretty(&cfg_val)?;
    Ok((
        [
            (header::CONTENT_TYPE,        "application/json".to_owned()),
            (header::CONTENT_DISPOSITION, "attachment; filename=\"config.json\"".to_owned()),
        ],
        json,
    ).into_response())
}
