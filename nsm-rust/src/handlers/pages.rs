use axum::{
    extract::State,
    http::StatusCode,
    response::{Html, IntoResponse, Redirect, Response},
};
use tera::Context;

use crate::{error::AppError, job_manager::list_completed_jobs, state::SharedState};

pub async fn index() -> Redirect {
    Redirect::to("/submit")
}

pub async fn health() -> Response {
    (StatusCode::OK, r#"{"status":"ok"}"#).into_response()
}

/// Render a simple info page when no fragment template is needed.
pub(crate) fn render_fragment(
    state: &SharedState,
    template: &str,
    ctx: &Context,
) -> Result<Html<String>, AppError> {
    Ok(Html(state.tera.render(template, ctx)?))
}

/// Check HX-Request header and render full page or fragment accordingly.
pub(crate) fn render_page(
    state: &SharedState,
    fragment: &str,
    ctx: &mut Context,
    is_htmx: bool,
) -> Result<Html<String>, AppError> {
    let jobs = list_completed_jobs(&state.config.data_dir);
    ctx.insert("completed_jobs", &jobs);
    if is_htmx {
        Ok(Html(state.tera.render(fragment, ctx)?))
    } else {
        ctx.insert("_content_template", fragment);
        Ok(Html(state.tera.render("base.html", ctx)?))
    }
}

pub async fn help(
    State(state): State<SharedState>,
    headers: axum::http::HeaderMap,
) -> Result<Html<String>, AppError> {
    let mut ctx = Context::new();
    ctx.insert("active_tab", "Help");
    render_page(&state, "help.html", &mut ctx, crate::state::is_htmx(&headers))
}
