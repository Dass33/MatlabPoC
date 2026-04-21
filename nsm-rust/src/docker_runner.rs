use std::path::PathBuf;

use bollard::{
    container::{
        Config, CreateContainerOptions, LogsOptions, RemoveContainerOptions,
        StartContainerOptions, WaitContainerOptions,
    },
    models::{HostConfig, Mount, MountTypeEnum},
    Docker,
};
use futures::StreamExt;

use crate::{config::AppConfig, models::{JobStatus, JobStatusFile}, job_manager::write_status};

pub async fn launch_matlab_container(
    docker: &Docker,
    config: &AppConfig,
    job_id: &str,
) -> anyhow::Result<String> {
    let host_job = config.host_data_dir.join(job_id).to_string_lossy().to_string();
    let out_dir  = config.data_dir.join(job_id).join("output");
    std::fs::create_dir_all(&out_dir)?;

    let container_cfg: Config<String> = Config {
        image: Some(config.matlab_image.clone()),
        cmd: Some(vec![
            "/opt/matlabruntime/R2025b".to_owned(),
            "/job/input".to_owned(),
            "/job/output".to_owned(),
        ]),
        host_config: Some(HostConfig {
            mounts: Some(vec![Mount {
                target:    Some("/job".to_owned()),
                source:    Some(host_job),
                typ:       Some(MountTypeEnum::BIND),
                read_only: Some(false),
                ..Default::default()
            }]),
            ..Default::default()
        }),
        ..Default::default()
    };

    let id = docker
        .create_container(None::<CreateContainerOptions<String>>, container_cfg)
        .await?
        .id;

    docker.start_container(&id, None::<StartContainerOptions<String>>).await?;
    tracing::info!("MATLAB container started: {} for job {}", &id[..12], job_id);

    let docker_clone = docker.clone();
    tokio::spawn(container_reaper(docker_clone, id.clone(), out_dir));

    Ok(id)
}

async fn container_reaper(docker: Docker, id: String, out_dir: PathBuf) {
    let exit_code = {
        let mut stream = docker.wait_container(&id, None::<WaitContainerOptions<String>>);
        match stream.next().await {
            Some(Ok(body)) => body.status_code,
            _              => -1,
        }
    };

    // Collect logs
    let log_opts = LogsOptions::<String> {
        stdout: true,
        stderr: true,
        ..Default::default()
    };
    let mut log_bytes = Vec::new();
    let mut log_stream = docker.logs(&id, Some(log_opts));
    while let Some(Ok(chunk)) = log_stream.next().await {
        use bollard::container::LogOutput;
        match chunk {
            LogOutput::StdOut { message } | LogOutput::StdErr { message } => {
                log_bytes.extend_from_slice(&message);
            }
            _ => {}
        }
    }
    let _ = tokio::fs::write(out_dir.join("matlab.log"), &log_bytes).await;

    // Only write status if MATLAB didn't write one itself
    let status_path = out_dir.join("status.json");
    if !status_path.exists() {
        let status = if exit_code == 0 {
            JobStatusFile { status: JobStatus::Completed, error: None }
        } else {
            JobStatusFile {
                status: JobStatus::Failed,
                error: Some(format!("Container exited with code {exit_code}")),
            }
        };
        let _ = write_status(&out_dir, &status);
    }

    let _ = docker.remove_container(
        &id,
        Some(RemoveContainerOptions { force: true, ..Default::default() }),
    ).await;

    tracing::info!("Container {} removed (exit {})", &id[..12.min(id.len())], exit_code);
}
