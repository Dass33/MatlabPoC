use std::{
    io::Write,
    path::{Path, PathBuf},
};

use chrono::Local;
use uuid::Uuid;

use crate::models::{JobMeta, JobStatus, JobStatusFile};

// ── Path helpers ──────────────────────────────────────────────────────────────

pub fn job_dirs(data_dir: &Path, job_id: &str) -> (PathBuf, PathBuf, PathBuf) {
    let base = data_dir.join(job_id);
    let inp  = base.join("input");
    let out  = base.join("output");
    (base, inp, out)
}

pub fn generate_job_id() -> String {
    let ts  = Local::now().format("%Y%m%d_%H%M%S");
    let hex = &Uuid::new_v4().simple().to_string()[..6];
    format!("{ts}_{hex}")
}

// ── Status I/O ────────────────────────────────────────────────────────────────

pub fn write_status(out_dir: &Path, status: &JobStatusFile) -> std::io::Result<()> {
    let json = serde_json::to_vec_pretty(status).unwrap_or_default();
    let path = out_dir.join("status.json");
    std::fs::write(path, json)
}

pub fn read_status(out_dir: &Path) -> JobStatusFile {
    let path = out_dir.join("status.json");
    if !path.exists() {
        return JobStatusFile::default();
    }
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(JobStatusFile { status: JobStatus::Unknown, error: Some("Could not parse status.json".into()) })
}

// ── Meta I/O ──────────────────────────────────────────────────────────────────

pub fn write_meta(job_dir: &Path, meta: &JobMeta) -> anyhow::Result<()> {
    let json = serde_json::to_string_pretty(meta)?;
    std::fs::write(job_dir.join("meta.json"), json)?;
    Ok(())
}

pub fn read_meta(job_dir: &Path) -> anyhow::Result<JobMeta> {
    let text = std::fs::read_to_string(job_dir.join("meta.json"))?;
    Ok(serde_json::from_str(&text)?)
}

// ── Job listing ───────────────────────────────────────────────────────────────

pub fn list_all_jobs(data_dir: &Path) -> Vec<JobMeta> {
    let mut jobs = Vec::new();
    let Ok(entries) = std::fs::read_dir(data_dir) else { return jobs };
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() { continue; }
        let Ok(mut meta) = read_meta(&path) else { continue };
        let (_, _, out) = job_dirs(data_dir, meta.job_id.as_str());
        let status = read_status(&out);
        meta.status = Some(status.status);
        meta.error  = status.error;
        jobs.push(meta);
    }
    jobs.sort_by(|a, b| b.submitted_at.cmp(&a.submitted_at));
    jobs
}

pub fn list_completed_jobs(data_dir: &Path) -> Vec<JobMeta> {
    list_all_jobs(data_dir)
        .into_iter()
        .filter(|j| j.status == Some(JobStatus::Completed))
        .collect()
}

pub fn count_running_jobs(data_dir: &Path) -> usize {
    list_all_jobs(data_dir)
        .iter()
        .filter(|j| j.status == Some(JobStatus::Processing))
        .count()
}

// ── Submission ────────────────────────────────────────────────────────────────

pub struct SubmitFiles {
    pub name:          String,
    pub filenames:     Vec<String>,
    pub file_bytes:    Vec<(String, Vec<u8>)>,
    pub config:        serde_json::Value,
    pub dark_cal_bytes: Option<Vec<u8>>,
}

pub fn create_job(data_dir: &Path, submit: &SubmitFiles) -> anyhow::Result<String> {
    let job_id = generate_job_id();
    let (base, inp, out) = job_dirs(data_dir, &job_id);
    std::fs::create_dir_all(&inp)?;
    std::fs::create_dir_all(&out)?;

    for (fname, bytes) in &submit.file_bytes {
        std::fs::write(inp.join(fname), bytes)?;
    }

    if let Some(dark) = &submit.dark_cal_bytes {
        std::fs::write(base.join("dark_cal.mat"), dark)?;
    }

    std::fs::write(base.join("config.json"), serde_json::to_string_pretty(&submit.config)?)?;

    let now = Local::now().to_rfc3339();
    let meta = JobMeta {
        job_id: job_id.clone(),
        name: if submit.name.trim().is_empty() { None } else { Some(submit.name.trim().to_owned()) },
        filenames: submit.filenames.clone(),
        submitted_at: now.clone(),
        started_at: now,
        status: None,
        error: None,
    };
    write_meta(&base, &meta)?;

    Ok(job_id)
}

// ── ZIP download ──────────────────────────────────────────────────────────────

pub fn create_zip(data_dir: &Path, job_id: &str) -> anyhow::Result<Vec<u8>> {
    let (base, _, out) = job_dirs(data_dir, job_id);
    let buf = Vec::new();
    let mut zip = zip::ZipWriter::new(std::io::Cursor::new(buf));

    let opts = zip::write::FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    let add_file = |zip: &mut zip::ZipWriter<_>, src: PathBuf, name: &str| -> anyhow::Result<()> {
        if src.exists() {
            zip.start_file(name, opts)?;
            zip.write_all(&std::fs::read(&src)?)?;
        }
        Ok(())
    };

    add_file(&mut zip, base.join("config.json"), "config.json")?;
    add_file(&mut zip, out.join("collection_postprocessed.json"), "collection_postprocessed.json")?;
    add_file(&mut zip, out.join("population.json"), "population.json")?;
    add_file(&mut zip, out.join("Setting.json"), "Setting.json")?;

    // collection.mat
    let mat_path = out.join("collection").join("collection.mat");
    add_file(&mut zip, mat_path, "collection.mat")?;

    // kymographs
    let kymo_dir = out.join("kymographs");
    if kymo_dir.is_dir() {
        for entry in std::fs::read_dir(&kymo_dir)?.flatten() {
            let p = entry.path();
            if p.extension().and_then(|e| e.to_str()) == Some("png") {
                let name = format!("kymographs/{}", p.file_name().unwrap().to_string_lossy());
                add_file(&mut zip, p, &name)?;
            }
        }
    }

    let inner = zip.finish()?;
    Ok(inner.into_inner())
}
