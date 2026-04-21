use axum::{
    extract::{Path, Query, State},
    http::{HeaderMap, header},
    response::{Html, IntoResponse, Redirect, Response},
};
use serde::Deserialize;
use tera::Context;

use crate::{
    error::AppError,
    job_manager::{create_zip, list_all_jobs, write_status},
    models::{JobStatus, JobStatusFile},
    state::SharedState,
};

#[derive(Deserialize, Default)]
pub struct HistoryQuery {
    pub submitted: Option<String>,
}

pub async fn page(
    State(state): State<SharedState>,
    Query(q): Query<HistoryQuery>,
    headers: HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "History");
    ctx.insert("submitted_job", &q.submitted);
    let jobs = list_all_jobs(&state.config.data_dir);
    ctx.insert("jobs", &jobs);
    ctx.insert("max_workers", &state.config.max_workers);
    super::pages::render_page(&state, "history.html", &mut ctx, crate::state::is_htmx(&headers))
}

/// HTMX polling target — returns only the table fragment.
pub async fn table_fragment(
    State(state): State<SharedState>,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    let jobs = list_all_jobs(&state.config.data_dir);
    ctx.insert("jobs", &jobs);
    ctx.insert("max_workers", &state.config.max_workers);
    Ok(Html(state.tera.render("history_table.html", &ctx)?))
}

/// Force-free a stuck job by marking it as failed.
pub async fn force_free(
    State(state): State<SharedState>,
    Path(job_id): Path<String>,
) -> Result<impl IntoResponse, AppError> {
    let (_, _, out) = crate::job_manager::job_dirs(&state.config.data_dir, &job_id);
    std::fs::create_dir_all(&out)?;
    write_status(&out, &JobStatusFile {
        status: JobStatus::Failed,
        error: Some("Manually freed by admin".into()),
    })?;
    tracing::info!("Force-freed job: {}", job_id);
    Ok(Redirect::to("/history"))
}

/// Download all results as a ZIP archive.
pub async fn download_zip(
    State(state): State<SharedState>,
    Path(job_id): Path<String>,
) -> Result<Response, AppError> {
    let zip_bytes = create_zip(&state.config.data_dir, &job_id)?;
    let filename  = format!("{job_id}_results.zip");
    Ok((
        [
            (header::CONTENT_TYPE,        "application/zip".to_owned()),
            (header::CONTENT_DISPOSITION, format!("attachment; filename=\"{filename}\"")),
        ],
        zip_bytes,
    ).into_response())
}
