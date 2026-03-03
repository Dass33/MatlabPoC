use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum SweepParam {
    Single(f64),
    Multi(Vec<f64>),
}

impl SweepParam {
    pub fn to_vec(&self) -> Vec<f64> {
        match self {
            SweepParam::Single(v) => vec![*v],
            SweepParam::Multi(v) => v.clone(),
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct KymographPreprocessing {
    #[serde(rename = "Wx")]
    pub wx: SweepParam,
    #[serde(rename = "Wt")]
    pub wt: SweepParam,
    pub ws: f64,
    #[serde(rename = "darkCalibration")]
    pub dark_calibration: serde_json::Value,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Detection {
    #[serde(rename = "peakSign")]
    pub peak_sign: String,
    pub pfa: f64,
    #[serde(rename = "localOptimumRange")]
    pub local_optimum_range: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Linking {
    #[serde(rename = "minTrackLength")]
    pub min_track_length: usize,
    pub cut_off_distance: f64,
    pub unmatched_penalty_distance: f64,
    #[serde(rename = "maxNegativeGab")]
    pub max_negative_gap: i32,
    #[serde(rename = "maxPositiveGab")]
    pub max_positive_gap: i32,
    pub gab_closing_cut_off_distance: f64,
    pub gab_closing_penalty_distance: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct OutlierFiltering {
    #[serde(rename = "referenceProperty")]
    pub reference_property: String,
    #[serde(rename = "filterProperties")]
    pub filter_properties: Vec<String>,
    #[serde(rename = "thresholdDirection")]
    pub threshold_direction: Vec<String>,
    #[serde(rename = "thresholdValue")]
    pub threshold_value: Vec<ThresholdValue>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum ThresholdValue {
    Named(String),
    Fixed(f64),
    FixedPair(Vec<f64>),
}

#[derive(Debug, Clone, Deserialize)]
pub struct PopulationAnalysis {
    #[serde(rename = "Title")]
    pub title: String,
    pub properties: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    #[serde(rename = "Dt")]
    pub dt: f64,
    #[serde(rename = "Dx")]
    pub dx: f64,
    #[serde(rename = "flipIntensity")]
    pub flip_intensity: bool,
    #[serde(rename = "flowEstimate")]
    pub flow_estimate: f64,
    #[serde(rename = "inputDataFormat")]
    #[serde(default = "default_format")]
    pub input_data_format: String,
    #[serde(rename = "kymographPreprocessing")]
    pub kymograph_preprocessing: KymographPreprocessing,
    #[serde(rename = "Detection")]
    pub detection: Detection,
    #[serde(rename = "Linking")]
    pub linking: Linking,
    #[serde(rename = "trajectoryProperties")]
    pub trajectory_properties: Vec<String>,
    #[serde(rename = "iOCcalibration")]
    pub ioc_calibration: String,
    #[serde(rename = "outlierFiltering")]
    pub outlier_filtering: OutlierFiltering,
    #[serde(rename = "populationAnalysis")]
    pub population_analysis: PopulationAnalysis,
    pub tracker: Option<String>,
}

fn default_format() -> String {
    "tiff2".to_string()
}

/// Compute sweep pairs: outer product Wt × Wx in column-major order (matching MATLAB meshgrid + (:))
pub fn sweep_pairs(config: &Config) -> Vec<(f64, f64)> {
    let wx_vec = config.kymograph_preprocessing.wx.to_vec();
    let wt_vec = config.kymograph_preprocessing.wt.to_vec();
    // meshgrid(Wx, Wt) then (:) — column-major: outer loop Wt, inner loop Wx
    let mut pairs = Vec::new();
    for &wt in &wt_vec {
        for &wx in &wx_vec {
            pairs.push((wx, wt));
        }
    }
    pairs
}

pub fn sweep_legend(wx: f64, wt: f64) -> String {
    format!("Wx={},Wt={}", wx as i64, wt as i64)
}
