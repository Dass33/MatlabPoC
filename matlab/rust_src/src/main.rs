mod config;
mod detection;
mod gap;
mod io;
mod kymo;
mod linking;
mod population;
mod postprocess;
mod preprocess;
mod refinement;
mod render;
mod trajectory;

use anyhow::{bail, Context, Result};
use config::{sweep_legend, sweep_pairs, Config};
use io::output::{atomic_write, save_summary, save_trajectories};
use io::tiff_loader::load_tiff2;
use kymo::KymoMatrix;
use postprocess::{collection_postprocessing, CollectionPostprocessed};
use population::analyze_population_robust_mean;
use rayon::prelude::*;
use serde_json::json;
use std::path::{Path, PathBuf};
use tracing::{error, info};

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into()),
        )
        .init();

    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: nsm-algorithm <input_dir> <output_dir>");
        std::process::exit(1);
    }

    let input_dir = PathBuf::from(&args[1]);
    let output_dir = PathBuf::from(&args[2]);

    if let Err(e) = run(&input_dir, &output_dir) {
        error!("Pipeline failed: {:#}", e);
        write_status_best_effort(&output_dir, "failed", &format!("{:#}", e));
        std::process::exit(1);
    }
}

fn run(input_dir: &Path, output_dir: &Path) -> Result<()> {
    std::fs::create_dir_all(output_dir)?;
    write_status(output_dir, "processing", "")?;

    // Load config from job directory (input/../config.json)
    let config_path = input_dir
        .parent()
        .context("input_dir has no parent")?
        .join("config.json");
    let config_text = std::fs::read_to_string(&config_path)
        .with_context(|| format!("reading {}", config_path.display()))?;
    let config: Config =
        serde_json::from_str(&config_text).context("parsing config.json")?;

    info!("Config loaded. Building sweep pairs.");
    let pairs = sweep_pairs(&config);
    let n_sweeps = pairs.len();
    info!("{} sweep(s)", n_sweeps);

    // Discover TIFF files
    let mut tiff_files: Vec<PathBuf> = std::fs::read_dir(input_dir)?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.eq_ignore_ascii_case("tiff"))
                .unwrap_or(false)
        })
        .collect();
    tiff_files.sort();

    if tiff_files.is_empty() {
        bail!("No .tiff files found in {}", input_dir.display());
    }

    info!("{} TIFF file(s) found", tiff_files.len());

    // Create kymographs directory
    let kymo_dir = output_dir.join("kymographs");
    std::fs::create_dir_all(&kymo_dir)?;

    // Per-sweep collections (concatenated across all TIFFs)
    let mut sweep_collections: Vec<Vec<trajectory::TrajectoryResult>> =
        (0..n_sweeps).map(|_| Vec::new()).collect();
    let dark = get_dark_value(&config);

    let per_file: Vec<Result<Vec<Vec<trajectory::TrajectoryResult>>>> = tiff_files
        .par_iter()
        .map(|tiff_path| {
            info!("Processing {}", tiff_path.display());
            let raw = load_tiff2(tiff_path)
                .with_context(|| format!("loading {}", tiff_path.display()))?;

            let dx = config.dx;
            let dt = raw.dt;

            // Construct KymoMatrix from the flat pixel buffer — zero-copy move
            let im = KymoMatrix { data: raw.im, nt: raw.nt, nx: raw.nx };

            let wx_vec: Vec<f64> = pairs.iter().map(|&(wx, _)| wx).collect();
            let wt_vec: Vec<f64> = pairs.iter().map(|&(_, wt)| wt).collect();

            let contrasts = preprocess::preprocess(&im, dark, &wx_vec, &wt_vec);

            let file_stem = tiff_path.file_stem().unwrap_or_default().to_string_lossy();

            let mut sweep_results: Vec<Vec<trajectory::TrajectoryResult>> =
                (0..n_sweeps).map(|_| Vec::new()).collect();

            for (sweep_idx, (c, (&wx, &wt))) in contrasts
                .iter()
                .zip(wx_vec.iter().zip(wt_vec.iter()))
                .enumerate()
            {
                let tracks = run_tracker(c, &config, dx, dt);
                let traj_results = trajectory::analyze_tracks(&tracks, c, wx, dx, dt);

                let kymo_name = format!("{}.png", file_stem);
                let kymo_path = kymo_dir.join(&kymo_name);
                if let Err(e) = render::render_kymograph(c, &tracks, &kymo_path, 150) {
                    error!("Kymograph render failed for {}: {}", kymo_name, e);
                }

                sweep_results[sweep_idx].extend(traj_results);
            }

            Ok(sweep_results)
        })
        .collect();

    for file_result in per_file {
        for (sweep_idx, traj) in file_result?.into_iter().enumerate() {
            sweep_collections[sweep_idx].extend(traj);
        }
    }

    // Build postprocessed collections
    let mut postprocessed: Vec<CollectionPostprocessed> = Vec::new();

    for (sweep_idx, results) in sweep_collections.iter().enumerate() {
        if results.is_empty() {
            bail!(
                "No trajectories detected in sweep {}/{}. Check pfa and flowEstimate.",
                sweep_idx + 1,
                n_sweeps
            );
        }
        let (wx, wt) = pairs[sweep_idx];
        let legend = sweep_legend(wx, wt);
        let col = CollectionPostprocessed::from_trajectory_results(results, &legend);
        let (filtered, _calibrated) =
            collection_postprocessing(col, &config.outlier_filtering, &config.ioc_calibration);
        postprocessed.push(filtered);
    }

    // Population analysis
    let properties = &config.population_analysis.properties;
    let populations: Vec<population::Population> = postprocessed
        .iter()
        .map(|col| analyze_population_robust_mean(col, properties))
        .collect();

    // Write outputs
    save_trajectories(output_dir, &postprocessed)?;
    save_summary(output_dir, &populations, &postprocessed, properties)?;

    write_status(output_dir, "completed", "")?;
    info!("Done.");
    Ok(())
}

/// Run the gap-closing tracker on one kymograph slice.
fn run_tracker(
    c: &KymoMatrix,
    config: &Config,
    dx: f64,
    dt: f64,
) -> Vec<linking::Track> {
    let nt = c.nt;
    let border_range = config.detection.local_optimum_range;
    // flowEstimate in config is in px/frame (same units used by tracker)
    let flow_px = config.flow_estimate;

    // Detection
    let detections = detection::detect(
        c,
        &config.detection.peak_sign,
        config.detection.pfa,
        config.detection.local_optimum_range,
        border_range,
    );

    if detections.is_empty() {
        return vec![];
    }

    // Position refinement
    let fitting_radius = config.detection.local_optimum_range;
    let refined = refinement::refine_centroid(&detections, c, fitting_radius);

    // Build spot list
    let spots: Vec<linking::Spot> = detections
        .iter()
        .zip(refined.iter())
        .enumerate()
        .map(|(id, (d, &pr))| linking::Spot {
            spot_id: id,
            frame: d.frame,
            position: d.position,
            position_refined: pr,
            intensity: d.intensity,
            contrast: c.get(d.frame, d.position),
        })
        .collect();

    // Frame-to-frame linking
    let edges = linking::spot_linking(
        &spots,
        nt,
        config.linking.cut_off_distance,
        config.linking.unmatched_penalty_distance,
        flow_px,
    );

    // Compute std_jump_distance for gap filling
    let jump_distances: Vec<f64> = edges.iter().map(|&(_, _, jd)| jd.abs()).collect();
    let gap_range = gap::compute_gap_local_optimum_range(&jump_distances);

    let tracklets = linking::join_linked_spots(&edges, &spots);

    // Gap closing
    let (matches, unmatched) = linking::tracklet_linking(
        &tracklets,
        config.linking.max_negative_gap,
        config.linking.max_positive_gap,
        config.linking.gab_closing_cut_off_distance,
        config.linking.gab_closing_penalty_distance,
        flow_px,
    );

    let raw_tracks = linking::join_linked_tracklets(&matches, &unmatched, &tracklets);

    // Delete negative gaps, filter, fill gaps
    let cleaned = gap::delete_negative_gap_spots(raw_tracks);
    let filtered = gap::filter_tracks(cleaned, config.linking.min_track_length);
    let gap_filled = gap::gap_filling(
        filtered,
        c,
        &config.detection.peak_sign,
        gap_range,
        fitting_radius,
    );

    gap_filled
}

fn get_dark_value(config: &Config) -> f64 {
    match &config.kymograph_preprocessing.dark_calibration {
        serde_json::Value::Number(n) => n.as_f64().unwrap_or(0.0),
        _ => 0.0,
    }
}

fn write_status(output_dir: &Path, status: &str, error_msg: &str) -> Result<()> {
    let val = if error_msg.is_empty() {
        json!({"status": status, "error": null})
    } else {
        json!({"status": status, "error": error_msg})
    };
    let path = output_dir.join("status.json");
    let data = format!("{}\n", serde_json::to_string(&val)?);
    atomic_write(&path, data.as_bytes())
}

fn write_status_best_effort(output_dir: &Path, status: &str, error_msg: &str) {
    let _ = std::fs::create_dir_all(output_dir);
    let _ = write_status(output_dir, status, error_msg);
}
