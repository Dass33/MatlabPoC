use anyhow::Result;
use plotters::prelude::*;
use std::path::Path;

use crate::kymo::KymoMatrix;
use crate::linking::Track;

/// Render kymograph C[Nt × Nx] with track overlays to a PNG file.
pub fn render_kymograph(
    c: &KymoMatrix,
    tracks: &[Track],
    output_path: &Path,
    dpi: u32,
) -> Result<()> {
    let nt = c.nt;
    let nx = c.nx;
    if nt == 0 || nx == 0 {
        anyhow::bail!("empty kymograph");
    }

    // Scale image to roughly DPI-equivalent size
    let px_w = (nx as f64 * dpi as f64 / 72.0) as u32;
    let px_h = (nt as f64 * dpi as f64 / 72.0) as u32;
    let px_w = px_w.max(400).min(4000);
    let px_h = px_h.max(200).min(4000);

    let root = BitMapBackend::new(output_path, (px_w, px_h)).into_drawing_area();
    root.fill(&WHITE)?;

    // Color limits — c.data is already flat, no copy needed
    let vmin = c.data.iter().cloned().fold(f64::INFINITY, f64::min);
    let vmax = c.data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let range = (vmax - vmin).max(1e-10);

    // Heatmap: pixel-by-pixel
    let cell_w = px_w as f64 / nx as f64;
    let cell_h = px_h as f64 / nt as f64;

    for t in 0..nt {
        for x in 0..nx {
            let val = (c.get(t, x) - vmin) / range;
            let (r, g, b) = viridis(val);
            let px0 = (x as f64 * cell_w) as i32;
            let py0 = (t as f64 * cell_h) as i32;
            let px1 = ((x + 1) as f64 * cell_w) as i32;
            let py1 = ((t + 1) as f64 * cell_h) as i32;
            root.draw(&Rectangle::new(
                [(px0, py0), (px1, py1)],
                ShapeStyle::from(RGBColor(r, g, b)).filled(),
            ))?;
        }
    }

    // Track overlays
    for (track_idx, track) in tracks.iter().enumerate() {
        if track.frames.is_empty() {
            continue;
        }
        let color = track_color(track_idx);
        let points: Vec<(i32, i32)> = track
            .frames
            .iter()
            .zip(track.positions_refined.iter())
            .map(|(&t, &x)| {
                let px = (x * cell_w) as i32;
                let py = (t as f64 * cell_h) as i32;
                (px, py)
            })
            .collect();

        if points.len() > 1 {
            root.draw(&PathElement::new(points, ShapeStyle::from(color).stroke_width(1)))?;
        }
    }

    root.present()?;
    Ok(())
}

/// Approximate viridis colormap: returns (R, G, B) for t in [0, 1].
fn viridis(t: f64) -> (u8, u8, u8) {
    let t = t.clamp(0.0, 1.0);
    // Control points (from matplotlib viridis)
    let lut: &[(f64, f64, f64, f64)] = &[
        (0.0, 0.267_004, 0.004_874, 0.329_415),
        (0.25, 0.190_631, 0.407_061, 0.556_734),
        (0.5, 0.127_568, 0.566_949, 0.550_556),
        (0.75, 0.369_214, 0.788_888, 0.382_914),
        (1.0, 0.993_248, 0.906_157, 0.143_936),
    ];
    let (r, g, b) = interp_colormap(lut, t);
    ((r * 255.0) as u8, (g * 255.0) as u8, (b * 255.0) as u8)
}

fn interp_colormap(lut: &[(f64, f64, f64, f64)], t: f64) -> (f64, f64, f64) {
    if lut.is_empty() {
        return (0.0, 0.0, 0.0);
    }
    let n = lut.len();
    if t <= lut[0].0 {
        return (lut[0].1, lut[0].2, lut[0].3);
    }
    if t >= lut[n - 1].0 {
        return (lut[n - 1].1, lut[n - 1].2, lut[n - 1].3);
    }
    let idx = lut.partition_point(|&(x, _, _, _)| x < t);
    let lo = &lut[idx - 1];
    let hi = &lut[idx];
    let alpha = (t - lo.0) / (hi.0 - lo.0);
    (
        lo.1 + alpha * (hi.1 - lo.1),
        lo.2 + alpha * (hi.2 - lo.2),
        lo.3 + alpha * (hi.3 - lo.3),
    )
}

/// Jet-like track color cycling
fn track_color(idx: usize) -> RGBColor {
    let colors = [
        RGBColor(255, 0, 0),
        RGBColor(0, 200, 0),
        RGBColor(0, 0, 255),
        RGBColor(255, 165, 0),
        RGBColor(128, 0, 128),
        RGBColor(0, 200, 200),
        RGBColor(255, 105, 180),
        RGBColor(165, 42, 42),
    ];
    colors[idx % colors.len()]
}
