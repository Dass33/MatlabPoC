use axum::{
    extract::{Query, State},
    http::HeaderMap,
    response::Html,
};
use serde::Deserialize;
use tera::Context;

use crate::{error::AppError, state::SharedState};

#[derive(Deserialize)]
pub struct KymographQuery {
    pub job_id: Option<String>,
}

pub async fn page(
    State(state): State<SharedState>,
    Query(q): Query<KymographQuery>,
    headers: HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "Kymograph Analysis");

    if let Some(ref job_id) = q.job_id {
        let kymo_dir = state.config.data_dir.join(job_id).join("output").join("kymographs");
        let mut images: Vec<String> = vec![];
        if kymo_dir.is_dir() {
            let mut entries: Vec<String> = std::fs::read_dir(&kymo_dir)
                .into_iter()
                .flatten()
                .flatten()
                .filter_map(|e| {
                    let p = e.path();
                    if p.extension().and_then(|x| x.to_str()) == Some("png") {
                        Some(p.file_name()?.to_string_lossy().to_string())
                    } else {
                        None
                    }
                })
                .collect();
            entries.sort();
            images = entries;
        }
        ctx.insert("job_id", job_id);
        ctx.insert("images", &images);
    } else {
        ctx.insert("job_id", &Option::<String>::None);
        ctx.insert("images", &Vec::<String>::new());
    }

    super::pages::render_page(&state, "kymograph.html", &mut ctx, crate::state::is_htmx(&headers))
}

/// Serve a kymograph PNG directly.
pub async fn serve_image(
    State(state): State<SharedState>,
    axum::extract::Path((job_id, filename)): axum::extract::Path<(String, String)>,
) -> Result<impl axum::response::IntoResponse, AppError> {
    let path = state.config.data_dir
        .join(&job_id)
        .join("output")
        .join("kymographs")
        .join(&filename);

    if !path.exists() {
        return Err(AppError::NotFound(format!("Image not found: {filename}")));
    }
    let bytes = std::fs::read(&path)?;
    Ok((
        [(axum::http::header::CONTENT_TYPE, "image/png")],
        bytes,
    ))
}
