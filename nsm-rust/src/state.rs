use std::{collections::HashMap, path::Path, sync::Arc};
use tokio::sync::RwLock;

use crate::{
    config::AppConfig,
    models::{Collection, PostprocessingState, PropStats, ThresholdConfig, DEFAULT_SIGMA},
};

pub type SharedState = Arc<AppState>;

pub struct AppState {
    pub config:   AppConfig,
    pub tera:     tera::Tera,
    pub docker:   bollard::Docker,
    // Per-job caches (populated lazily)
    pub pp_states:   RwLock<HashMap<String, PostprocessingState>>,
    pub pop_results: RwLock<HashMap<String, HashMap<String, PropStats>>>,
    pub collections: RwLock<HashMap<String, Arc<Collection>>>,
}

impl AppState {
    pub fn new(config: AppConfig, tera: tera::Tera, docker: bollard::Docker) -> Arc<Self> {
        Arc::new(AppState {
            config,
            tera,
            docker,
            pp_states:   RwLock::new(HashMap::new()),
            pop_results: RwLock::new(HashMap::new()),
            collections: RwLock::new(HashMap::new()),
        })
    }

    /// Load collection from disk, caching the result.
    pub async fn get_or_load_collection(
        &self,
        job_id: &str,
    ) -> anyhow::Result<Arc<Collection>> {
        {
            let cache = self.collections.read().await;
            if let Some(c) = cache.get(job_id) {
                return Ok(Arc::clone(c));
            }
        }
        let mat_path = self.config.data_dir
            .join(job_id)
            .join("output")
            .join("collection")
            .join("collection.mat");
        let col = crate::mat_reader::load_collection(&mat_path)?;
        let arc = Arc::new(col);
        self.collections.write().await.insert(job_id.to_owned(), Arc::clone(&arc));
        Ok(arc)
    }

    /// Initialise per-job postprocessing state if not already present.
    pub async fn get_or_init_pp_state(
        &self,
        job_id: &str,
        filter_props: &[String],
        threshold_directions: &[String],
        threshold_values: &[String],
    ) -> PostprocessingState {
        {
            let map = self.pp_states.read().await;
            if let Some(s) = map.get(job_id) {
                return s.clone();
            }
        }
        let thresholds: HashMap<String, ThresholdConfig> = filter_props
            .iter()
            .zip(threshold_directions.iter().chain(std::iter::repeat(&"upper".to_string())))
            .zip(threshold_values.iter().chain(std::iter::repeat(&"3std".to_string())))
            .map(|((prop, dir), tv)| {
                (
                    prop.clone(),
                    ThresholdConfig {
                        sigma:     DEFAULT_SIGMA,
                        direction: dir.clone(),
                        tv:        tv.clone(),
                        value:     0.0,
                        value_lo:  0.0,
                        value_hi:  0.0,
                    },
                )
            })
            .collect();

        let state = PostprocessingState {
            thresholds,
            overrides: HashMap::new(),
            axis_x: "iOC".into(),
            axis_y: "velocity".into(),
            ioc_cal_on: true,
        };
        self.pp_states.write().await.insert(job_id.to_owned(), state.clone());
        state
    }

    /// Read postprocessing config from the stored config.json for a job.
    pub fn job_config_path(&self, job_id: &str) -> std::path::PathBuf {
        self.config.data_dir.join(job_id).join("config.json")
    }

    pub fn load_nsm_config_for_job(&self, job_id: &str) -> anyhow::Result<crate::models::NsmConfig> {
        let path = self.job_config_path(job_id);
        if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            Ok(serde_json::from_str(&text)?)
        } else {
            Ok(crate::models::NsmConfig::default())
        }
    }
}

/// Render a Tera template, checking for HTMX request header.
/// If HX-Request header is present, renders the fragment template; otherwise wraps in base.html.
pub fn render_page(
    tera: &tera::Tera,
    fragment_template: &str,
    ctx: &tera::Context,
    is_htmx: bool,
) -> Result<String, tera::Error> {
    if is_htmx {
        tera.render(fragment_template, ctx)
    } else {
        let mut full_ctx = ctx.clone();
        full_ctx.insert("_content_template", fragment_template);
        tera.render("base.html", &full_ctx)
    }
}

pub fn is_htmx(headers: &axum::http::HeaderMap) -> bool {
    headers.contains_key("hx-request")
}

/// Shorthand for reading the base path for a job.
pub fn job_base(data_dir: &Path, job_id: &str) -> std::path::PathBuf {
    data_dir.join(job_id)
}
