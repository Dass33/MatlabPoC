use anyhow::Result;
use serde::Serialize;
use std::path::Path;

use crate::postprocess::CollectionPostprocessed;
use crate::population::Population;

#[derive(Serialize)]
struct TrajectoriesJson {
    #[serde(rename = "iOC")]
    ioc: Vec<f64>,
    #[serde(rename = "D")]
    d: Vec<f64>,
    velocity: Vec<f64>,
    #[serde(rename = "N")]
    n: Vec<f64>,
    #[serde(rename = "positionStart")]
    position_start: Vec<f64>,
    #[serde(rename = "positionEnd")]
    position_end: Vec<f64>,
    #[serde(rename = "sweepIdx")]
    sweep_idx: Vec<usize>,
    #[serde(rename = "sweepLegends")]
    sweep_legends: Vec<String>,
}

pub fn save_trajectories(output_dir: &Path, collections: &[CollectionPostprocessed]) -> Result<()> {
    let mut ioc = Vec::new();
    let mut d = Vec::new();
    let mut velocity = Vec::new();
    let mut n = Vec::new();
    let mut position_start = Vec::new();
    let mut position_end = Vec::new();
    let mut sweep_idx = Vec::new();
    let mut sweep_legends = Vec::new();

    for (i, c) in collections.iter().enumerate() {
        let sweep_num = i + 1;
        for j in 0..c.ioc.len() {
            ioc.push(c.ioc[j]);
            d.push(c.d[j]);
            velocity.push(c.velocity[j]);
            n.push(c.n[j]);
            position_start.push(c.position_start[j]);
            position_end.push(c.position_end[j]);
            sweep_idx.push(sweep_num);
        }
        sweep_legends.push(c.sweep_legend.clone());
    }

    let data = TrajectoriesJson {
        ioc,
        d,
        velocity,
        n,
        position_start,
        position_end,
        sweep_idx,
        sweep_legends,
    };

    let path = output_dir.join("trajectories.json");
    let json = serde_json::to_string_pretty(&data)?;
    atomic_write(&path, json.as_bytes())?;
    Ok(())
}

#[derive(Serialize)]
struct SummaryJson {
    sweeps: Vec<SweepSummary>,
}

#[derive(Serialize)]
struct SweepSummary {
    legend: String,
    #[serde(rename = "nTrajectories")]
    n_trajectories: usize,
    #[serde(rename = "MEAN")]
    mean: serde_json::Map<String, serde_json::Value>,
    #[serde(rename = "FWHM")]
    fwhm: serde_json::Map<String, serde_json::Value>,
    #[serde(rename = "RESOLUTION")]
    resolution: serde_json::Map<String, serde_json::Value>,
}

pub fn save_summary(
    output_dir: &Path,
    populations: &[Population],
    collections: &[CollectionPostprocessed],
    properties: &[String],
) -> Result<()> {
    let mut sweeps = Vec::new();
    for (pop, col) in populations.iter().zip(collections.iter()) {
        let mut mean_map = serde_json::Map::new();
        let mut fwhm_map = serde_json::Map::new();
        let mut res_map = serde_json::Map::new();
        for prop in properties {
            if let Some(&v) = pop.mean.get(prop) {
                mean_map.insert(prop.clone(), serde_json::json!(v));
            }
            if let Some(&v) = pop.fwhm.get(prop) {
                fwhm_map.insert(prop.clone(), serde_json::json!(v));
            }
            if let Some(&v) = pop.resolution.get(prop) {
                res_map.insert(prop.clone(), serde_json::json!(v));
            }
        }
        sweeps.push(SweepSummary {
            legend: col.sweep_legend.clone(),
            n_trajectories: pop.n_trajectories,
            mean: mean_map,
            fwhm: fwhm_map,
            resolution: res_map,
        });
    }
    let summary = SummaryJson { sweeps };
    let path = output_dir.join("summary.json");
    let json = serde_json::to_string_pretty(&summary)?;
    atomic_write(&path, json.as_bytes())?;
    Ok(())
}

pub fn atomic_write(path: &Path, data: &[u8]) -> Result<()> {
    let dir = path.parent().unwrap_or(Path::new("."));
    let tmp = tempfile::NamedTempFile::new_in(dir)?;
    std::fs::write(tmp.path(), data)?;
    tmp.persist(path)?;
    Ok(())
}
