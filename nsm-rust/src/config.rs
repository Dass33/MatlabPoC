use std::{net::SocketAddr, path::PathBuf, time::Duration};
use anyhow::Context;

#[derive(Debug, Clone)]
pub struct AppConfig {
    pub data_dir:      PathBuf,
    pub host_data_dir: PathBuf,
    pub matlab_image:  String,
    pub max_workers:   usize,
    pub poll_interval: Duration,
    pub listen_addr:   SocketAddr,
}

impl AppConfig {
    pub fn from_env() -> anyhow::Result<Self> {
        let data_dir = PathBuf::from(
            std::env::var("DATA_DIR").unwrap_or_else(|_| "./data/jobs".into()),
        );
        let host_data_dir = PathBuf::from(
            std::env::var("HOST_DATA_DIR").unwrap_or_else(|_| data_dir.to_string_lossy().to_string()),
        );
        let matlab_image =
            std::env::var("MATLAB_IMAGE").unwrap_or_else(|_| "matlab-algorithm:latest".into());
        let max_workers = std::env::var("MAX_WORKERS")
            .unwrap_or_else(|_| "2".into())
            .parse::<usize>()
            .context("MAX_WORKERS must be a non-negative integer")?;
        let poll_secs = std::env::var("POLL_INTERVAL_S")
            .unwrap_or_else(|_| "5".into())
            .parse::<u64>()
            .context("POLL_INTERVAL_S must be a non-negative integer")?;
        let port = std::env::var("PORT")
            .unwrap_or_else(|_| "3000".into())
            .parse::<u16>()
            .context("PORT must be a valid port number")?;

        std::fs::create_dir_all(&data_dir)?;

        Ok(AppConfig {
            data_dir,
            host_data_dir,
            matlab_image,
            max_workers,
            poll_interval: Duration::from_secs(poll_secs),
            listen_addr: SocketAddr::from(([0, 0, 0, 0], port)),
        })
    }
}
