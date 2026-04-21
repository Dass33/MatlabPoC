mod algorithms;
mod config;
mod docker_runner;
mod error;
mod handlers;
mod job_manager;
mod mat_reader;
mod models;
mod state;

use axum::{
    routing::{get, post},
    Router,
};
use bollard::Docker;
use tera::Tera;
use tower_http::trace::TraceLayer;

use config::AppConfig;
use state::AppState;

/// Scalar collection property names used in postprocessing UI.
pub const SCALAR_PROPS: &[&str] = &[
    "iOC", "STDiOC", "D", "velocity", "N", "positionStart", "positionEnd",
];

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "nsm_processor=info,tower_http=debug".parse().unwrap()),
        )
        .init();

    let config = AppConfig::from_env()?;
    let addr   = config.listen_addr;

    let tera   = Tera::new("templates/**/*").map_err(|e| anyhow::anyhow!("Tera init: {e}"))?;
    let docker = Docker::connect_with_unix_defaults()?;
    let state  = AppState::new(config, tera, docker);

    let app = build_router(state);

    tracing::info!("NSM Processor listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn build_router(state: state::SharedState) -> Router {
    Router::new()
        // Pages
        .route("/",                             get(handlers::pages::index))
        .route("/health",                       get(handlers::pages::health))
        .route("/help",                         get(handlers::pages::help))
        // Submit
        .route("/submit",                       get(handlers::submit::page)
                                                    .post(handlers::submit::handle_submit))
        // Kymograph
        .route("/kymograph",                    get(handlers::kymograph::page))
        .route("/kymograph/image/:job_id/:file",get(handlers::kymograph::serve_image))
        // Post-processing
        .route("/postprocessing",               get(handlers::postprocessing::page))
        .route("/postprocessing/thresholds",    post(handlers::postprocessing::update_thresholds))
        .route("/postprocessing/override",      post(handlers::postprocessing::handle_override))
        .route("/postprocessing/accept",        post(handlers::postprocessing::accept))
        // Population
        .route("/population",                   get(handlers::population::page))
        .route("/population/run",               post(handlers::population::run))
        // History
        .route("/history",                      get(handlers::history::page))
        .route("/history/table",                get(handlers::history::table_fragment))
        .route("/history/force-free/:id",       post(handlers::history::force_free))
        .route("/history/download/:id",         get(handlers::history::download_zip))
        // Config API
        .route("/api/config/default",           get(handlers::config_api::get_default))
        .route("/api/config/upload",            post(handlers::config_api::upload))
        .route("/api/config/download",          get(handlers::config_api::download))
        // Static files
        .route("/static/*path",                 get(handlers::static_files::serve))
        .with_state(state)
        .layer(TraceLayer::new_for_http())
}
