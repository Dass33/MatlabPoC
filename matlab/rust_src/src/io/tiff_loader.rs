use anyhow::{bail, Context, Result};
use std::path::Path;
use tiff::decoder::{Decoder, DecodingResult};

pub struct RawData {
    /// Image pixels [Nt × Nx] in row-major flat layout: index = t * nx + x
    pub im: Vec<f64>,
    pub nt: usize,
    pub nx: usize,
    pub dt: f64,
    pub dx: f64,
    pub temperature_start: f64,
    pub temperature_end: f64,
}

/// Load a tiff2-format file pair (.tiff + .txt).
/// The .tiff is a single-page image with rows=Nt, cols=Nx.
/// The .txt has tab-separated cells; row 6 col 2 = FPS, rows 19-20 col 2 = temperatures.
pub fn load_tiff2(tiff_path: &Path) -> Result<RawData> {
    let txt_path = tiff_path.with_extension("txt");

    let (fps, temp_start, temp_end) = parse_txt(&txt_path)
        .with_context(|| format!("reading metadata {}", txt_path.display()))?;

    let (im, nt, nx) = decode_tiff(tiff_path)
        .with_context(|| format!("decoding TIFF {}", tiff_path.display()))?;

    Ok(RawData {
        im,
        nt,
        nx,
        dt: 1.0 / fps,
        dx: 6.6 / 100.0,
        temperature_start: temp_start,
        temperature_end: temp_end,
    })
}

fn parse_txt(path: &Path) -> Result<(f64, f64, f64)> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("opening {}", path.display()))?;

    let mut fps: Option<f64> = None;
    let mut temp_start: f64 = 20.0;
    let mut temp_end: f64 = 20.0;

    for line in content.lines() {
        if let Some(val) = strip_prefix_value(line, "FPS:") {
            fps = val.parse().ok();
        } else if let Some(val) = strip_prefix_value(line, "SensorPCB Temperature before grab:") {
            temp_start = parse_temp(val);
        } else if let Some(val) = strip_prefix_value(line, "SensorPCB Temperature after grab:") {
            temp_end = parse_temp(val);
        }
    }

    let fps = fps.with_context(|| format!("FPS not found in {}", path.display()))?;
    Ok((fps, temp_start, temp_end))
}

fn strip_prefix_value<'a>(line: &'a str, prefix: &str) -> Option<&'a str> {
    line.trim()
        .strip_prefix(prefix)
        .map(|s| s.trim())
}

fn parse_temp(s: &str) -> f64 {
    // value may be "42.125 C" or "42.125°C"
    s.split_whitespace()
        .next()
        .and_then(|v| v.trim_end_matches("°C").parse().ok())
        .unwrap_or(20.0)
}

fn decode_tiff(path: &Path) -> Result<(Vec<f64>, usize, usize)> {
    let file = std::fs::File::open(path)?;
    let mut decoder = Decoder::new(std::io::BufReader::new(file))?;

    let (width, height) = decoder.dimensions()?;
    // Single-page TIFF: rows=Nt (height), cols=Nx (width)
    let nt = height as usize;
    let nx = width as usize;

    let result = decoder.read_image()?;
    let flat: Vec<f64> = match result {
        DecodingResult::U8(v) => v.into_iter().map(|x| x as f64).collect(),
        DecodingResult::U16(v) => v.into_iter().map(|x| x as f64).collect(),
        DecodingResult::U32(v) => v.into_iter().map(|x| x as f64).collect(),
        DecodingResult::F32(v) => v.into_iter().map(|x| x as f64).collect(),
        DecodingResult::F64(v) => v,
        _ => bail!("unsupported TIFF pixel type"),
    };

    if flat.len() != nt * nx {
        bail!("TIFF pixel count {} != {}×{}", flat.len(), nt, nx);
    }

    Ok((flat, nt, nx))
}
