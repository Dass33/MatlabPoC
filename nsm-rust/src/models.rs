use std::collections::HashMap;
use serde::{Deserialize, Serialize};

// ── Job lifecycle ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum JobStatus {
    Processing,
    Completed,
    Failed,
    Unknown,
}

impl std::fmt::Display for JobStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JobStatus::Processing => write!(f, "processing"),
            JobStatus::Completed  => write!(f, "completed"),
            JobStatus::Failed     => write!(f, "failed"),
            JobStatus::Unknown    => write!(f, "unknown"),
        }
    }
}

impl JobStatus {
    pub fn icon(&self) -> &'static str {
        match self {
            JobStatus::Processing => "⏳",
            JobStatus::Completed  => "✅",
            JobStatus::Failed     => "❌",
            JobStatus::Unknown    => "❓",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobStatusFile {
    pub status: JobStatus,
    pub error: Option<String>,
}

impl Default for JobStatusFile {
    fn default() -> Self {
        JobStatusFile { status: JobStatus::Processing, error: None }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobMeta {
    pub job_id: String,
    pub name: Option<String>,
    pub filenames: Vec<String>,
    pub submitted_at: String,
    pub started_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<JobStatus>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

// ── NSM algorithm config ──────────────────────────────────────────────────────

/// Mirrors DEFAULT_CONFIG from Python config.py exactly (field names kept as-is for MATLAB compat).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NsmConfig {
    #[serde(rename = "exportOptionalFigures")]
    pub export_optional_figures: bool,
    #[serde(rename = "inputDataFormat")]
    pub input_data_format: String,
    #[serde(rename = "Dt")]
    pub dt: f64,
    #[serde(rename = "Dx")]
    pub dx: f64,
    #[serde(rename = "flipIntensity")]
    pub flip_intensity: bool,
    #[serde(rename = "flowEstimate")]
    pub flow_estimate: f64,
    #[serde(rename = "kymographPreprocessing")]
    pub kymograph_preprocessing: KymographPreprocessing,
    #[serde(rename = "Detection")]
    pub detection: Detection,
    pub tracker: String,
    #[serde(rename = "Tlength")]
    pub tlength: u32,
    #[serde(rename = "thresholdLimit")]
    pub threshold_limit: f64,
    #[serde(rename = "TmaxNo")]
    pub tmax_no: u32,
    #[serde(rename = "Linking")]
    pub linking: Linking,
    #[serde(rename = "trajectoryProperties")]
    pub trajectory_properties: Vec<String>,
    #[serde(rename = "outlierFiltering")]
    pub outlier_filtering: OutlierFilteringConfig,
    #[serde(rename = "populationAnalysis")]
    pub population_analysis: PopulationAnalysisConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KymographPreprocessing {
    #[serde(rename = "darkCalibration")]
    pub dark_calibration: serde_json::Value,
    #[serde(rename = "Wx")]
    pub wx: serde_json::Value,
    #[serde(rename = "Wt")]
    pub wt: serde_json::Value,
    pub ws: f64,
    #[serde(rename = "removeBackground")]
    pub remove_background: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Detection {
    #[serde(rename = "peakSign")]
    pub peak_sign: String,
    pub pfa: f64,
    #[serde(rename = "localOptimumRange")]
    pub local_optimum_range: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Linking {
    #[serde(rename = "minTrackLength")]
    pub min_track_length: u32,
    pub cut_off_distance: f64,
    pub unmatched_penalty_distance: f64,
    #[serde(rename = "maxNegativeGab")]
    pub max_negative_gab: u32,
    #[serde(rename = "maxPositiveGab")]
    pub max_positive_gab: u32,
    pub gab_closing_cut_off_distance: f64,
    pub gab_closing_penalty_distance: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutlierFilteringConfig {
    #[serde(rename = "referenceProperty")]
    pub reference_property: String,
    #[serde(rename = "filterProperties")]
    pub filter_properties: Vec<String>,
    #[serde(rename = "thresholdDirection")]
    pub threshold_direction: Vec<String>,
    #[serde(rename = "thresholdValue")]
    pub threshold_value: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PopulationAnalysisConfig {
    #[serde(rename = "Title")]
    pub title: String,
    pub properties: Vec<String>,
}

impl Default for NsmConfig {
    fn default() -> Self {
        NsmConfig {
            export_optional_figures: false,
            input_data_format: "tiff2".into(),
            dt: 0.007,
            dx: 0.066,
            flip_intensity: true,
            flow_estimate: -3.4,
            kymograph_preprocessing: KymographPreprocessing {
                dark_calibration: serde_json::Value::Number(8.into()),
                wx: serde_json::Value::Number(serde_json::Number::from(15)),
                wt: serde_json::Value::Number(serde_json::Number::from(50)),
                ws: 2.36,
                remove_background: "robustmean".into(),
            },
            detection: Detection {
                peak_sign: "negative".into(),
                pfa: 1e-5,
                local_optimum_range: 6,
            },
            tracker: "gabClosingTracker".into(),
            tlength: 4,
            threshold_limit: -2.0,
            tmax_no: 8,
            linking: Linking {
                min_track_length: 10,
                cut_off_distance: 20.0,
                unmatched_penalty_distance: 15.0,
                max_negative_gab: 2,
                max_positive_gab: 3,
                gab_closing_cut_off_distance: 40.0,
                gab_closing_penalty_distance: 30.0,
            },
            trajectory_properties: vec![
                "positionRefined".into(),
                "timeFrame".into(),
                "iOCprofile".into(),
                "N".into(),
                "iOC".into(),
                "STDiOC".into(),
                "D".into(),
                "velocity".into(),
            ],
            outlier_filtering: OutlierFilteringConfig {
                reference_property: "iOC".into(),
                filter_properties: vec![
                    "iOC".into(), "STDiOC".into(), "velocity".into(),
                    "N".into(), "positionStart".into(), "positionEnd".into(),
                ],
                threshold_direction: vec![
                    "both".into(), "upper".into(), "both".into(),
                    "lower".into(), "upper".into(), "lower".into(),
                ],
                threshold_value: vec![
                    "3std".into(), "3std".into(), "3std".into(),
                    "3std".into(), "3std".into(), "3std".into(),
                ],
            },
            population_analysis: PopulationAnalysisConfig {
                title: "robustMean".into(),
                properties: vec!["iOC".into(), "D".into(), "velocity".into()],
            },
        }
    }
}

// ── Collection (parsed from .mat) ─────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Collection {
    #[serde(rename = "iOC")]
    pub ioc: Vec<f64>,
    #[serde(rename = "STDiOC")]
    pub std_ioc: Vec<f64>,
    #[serde(rename = "D")]
    pub d: Vec<f64>,
    pub velocity: Vec<f64>,
    #[serde(rename = "N")]
    pub n: Vec<f64>,
    pub position_start: Vec<f64>,
    pub position_end: Vec<f64>,
    #[serde(rename = "iOCprofile")]
    pub ioc_profile: Vec<Vec<f64>>,
    #[serde(rename = "positionRefined")]
    pub position_refined: Vec<Vec<f64>>,
    #[serde(rename = "timeFrame")]
    pub time_frame: Vec<Vec<f64>>,
    #[serde(rename = "ExperimentTimeStamp")]
    pub experiment_time_stamp: Vec<String>,
}

impl Collection {
    pub fn len(&self) -> usize {
        self.ioc.len()
    }

    pub fn is_empty(&self) -> bool {
        self.ioc.is_empty()
    }

    /// Get a scalar property by name for generic algorithm code.
    pub fn scalar_prop(&self, name: &str) -> Option<&Vec<f64>> {
        match name {
            "iOC"           => Some(&self.ioc),
            "STDiOC"        => Some(&self.std_ioc),
            "D"             => Some(&self.d),
            "velocity"      => Some(&self.velocity),
            "N"             => Some(&self.n),
            "positionStart" => Some(&self.position_start),
            "positionEnd"   => Some(&self.position_end),
            _ => None,
        }
    }

    /// Apply a boolean keep-mask, returning a filtered Collection.
    pub fn filter(&self, keep: &[bool]) -> Collection {
        assert_eq!(keep.len(), self.len());
        let pick_scalar = |v: &Vec<f64>| -> Vec<f64> {
            v.iter().zip(keep).filter(|(_, &k)| k).map(|(x, _)| *x).collect()
        };
        let pick_vecs = |v: &Vec<Vec<f64>>| -> Vec<Vec<f64>> {
            v.iter().zip(keep).filter(|(_, &k)| k).map(|(x, _)| x.clone()).collect()
        };
        let pick_strings = |v: &Vec<String>| -> Vec<String> {
            v.iter().zip(keep).filter(|(_, &k)| k).map(|(x, _)| x.clone()).collect()
        };
        Collection {
            ioc:                   pick_scalar(&self.ioc),
            std_ioc:               pick_scalar(&self.std_ioc),
            d:                     pick_scalar(&self.d),
            velocity:              pick_scalar(&self.velocity),
            n:                     pick_scalar(&self.n),
            position_start:        pick_scalar(&self.position_start),
            position_end:          pick_scalar(&self.position_end),
            ioc_profile:           pick_vecs(&self.ioc_profile),
            position_refined:      pick_vecs(&self.position_refined),
            time_frame:            pick_vecs(&self.time_frame),
            experiment_time_stamp: pick_strings(&self.experiment_time_stamp),
        }
    }
}

// ── Per-property threshold config ─────────────────────────────────────────────

pub const DEFAULT_SIGMA: f64 = 6.0;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdConfig {
    pub sigma:     f64,
    pub direction: String,
    pub tv:        String,
    pub value:     f64,
    pub value_lo:  f64,
    pub value_hi:  f64,
}

impl Default for ThresholdConfig {
    fn default() -> Self {
        ThresholdConfig {
            sigma: DEFAULT_SIGMA,
            direction: "upper".into(),
            tv: "3std".into(),
            value: 0.0,
            value_lo: 0.0,
            value_hi: 0.0,
        }
    }
}

// ── Per-job postprocessing session state ──────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum TrajectoryOverride {
    Kept,
    Excluded,
}

#[derive(Debug, Clone)]
pub struct PostprocessingState {
    pub thresholds: HashMap<String, ThresholdConfig>,
    pub overrides:  HashMap<usize, TrajectoryOverride>,
    pub axis_x:     String,
    pub axis_y:     String,
    pub ioc_cal_on: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum TrajectoryState {
    AutoKept,
    AutoExcluded,
    ManualKept,
    ManualExcluded,
}

impl TrajectoryState {
    pub fn color(&self) -> &'static str {
        match self {
            TrajectoryState::AutoKept      => "#0072B2",
            TrajectoryState::AutoExcluded  => "#D55E00",
            TrajectoryState::ManualKept    => "#009E73",
            TrajectoryState::ManualExcluded => "#E69F00",
        }
    }
    pub fn symbol(&self) -> &'static str {
        match self {
            TrajectoryState::AutoKept      => "circle",
            TrajectoryState::AutoExcluded  => "x",
            TrajectoryState::ManualKept    => "diamond",
            TrajectoryState::ManualExcluded => "square",
        }
    }
    pub fn label(&self) -> &'static str {
        match self {
            TrajectoryState::AutoKept      => "auto-kept",
            TrajectoryState::AutoExcluded  => "auto-excluded",
            TrajectoryState::ManualKept    => "manual-kept",
            TrajectoryState::ManualExcluded => "manual-excluded",
        }
    }
    pub fn is_kept(&self) -> bool {
        matches!(self, TrajectoryState::AutoKept | TrajectoryState::ManualKept)
    }
}

pub fn compute_states(
    n: usize,
    not_outlier: &[bool],
    overrides: &HashMap<usize, TrajectoryOverride>,
) -> Vec<TrajectoryState> {
    (0..n)
        .map(|i| match overrides.get(&i) {
            Some(TrajectoryOverride::Kept)     => TrajectoryState::ManualKept,
            Some(TrajectoryOverride::Excluded) => TrajectoryState::ManualExcluded,
            None => if not_outlier[i] { TrajectoryState::AutoKept } else { TrajectoryState::AutoExcluded },
        })
        .collect()
}

// ── Population analysis results ───────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropStats {
    #[serde(rename = "MEAN")]
    pub mean: f64,
    #[serde(rename = "STD")]
    pub std: f64,
    #[serde(rename = "FWHM")]
    pub fwhm: f64,
    #[serde(rename = "RESOLUTION")]
    pub resolution: f64,
    #[serde(rename = "_hist_centers", skip_serializing_if = "Option::is_none")]
    pub hist_centers: Option<Vec<f64>>,
    #[serde(rename = "_hist_counts", skip_serializing_if = "Option::is_none")]
    pub hist_counts: Option<Vec<u64>>,
}

// ── Calibration result ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationResult {
    pub x:     Vec<f64>,
    #[serde(rename = "A")]
    pub a:     Vec<f64>,
    #[serde(rename = "Astd")]
    pub a_std: Vec<f64>,
    #[serde(rename = "AN")]
    pub a_n:   Vec<f64>,
}
