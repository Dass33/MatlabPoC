#!/usr/bin/env python3
"""Generate synthetic test fixtures: test_sample.tiff + test_sample.txt.

Run from the project root:
    python tests/fixtures/generate_synthetic.py

Requires: numpy, tifffile  (pip install tifffile)

The generated files are committed to the repository so tests do not need
tifffile at runtime.  Re-run this script only when the synthetic data spec
needs to change (and update golden outputs afterwards with --update-golden).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_OUT = Path(__file__).parent

SEED = 42
N_FRAMES = 500
N_PIX = 200
N_TRACKS = 5

BACKGROUND = 40.0
NOISE_STD = 2.0
PSF_SIGMA = 2.36     # pixels (matches config ws)
TRACK_VELOCITY = -3.4  # px/frame (matches config flowEstimate)
TRACK_DURATION = 80  # frames
TRACK_AMPLITUDE = 80.0  # above background; bright particles → negative peaks after flip


def _generate_tiff(output_path: Path) -> None:
    import tifffile  # only needed when regenerating fixtures

    rng = np.random.default_rng(SEED)

    # Shape: (N_FRAMES, N_PIX) — rows are time, columns are space, matching real data.
    image = np.full((N_FRAMES, N_PIX), BACKGROUND, dtype=np.float64)
    image += rng.normal(0.0, NOISE_STD, size=image.shape)

    start_positions = rng.uniform(50, 150, size=N_TRACKS)
    start_frames = rng.integers(0, N_FRAMES - TRACK_DURATION, size=N_TRACKS)

    x = np.arange(N_PIX, dtype=float)
    for i in range(N_TRACKS):
        for t_rel in range(TRACK_DURATION):
            t_abs = int(start_frames[i]) + t_rel
            pos = start_positions[i] + TRACK_VELOCITY * t_rel
            psf = TRACK_AMPLITUDE * np.exp(-0.5 * ((x - pos) / PSF_SIGMA) ** 2)
            image[t_abs, :] += psf

    tifffile.imwrite(str(output_path), image.astype(np.float64))
    print(f"[generate] {output_path}  shape={image.shape}  dtype=float64")


def _generate_txt(output_path: Path) -> None:
    # Format must match the exact layout readcell() in loadRawData.m expects
    # for dataType='tiff2'.  readcell skips blank lines, so:
    #   non-blank row 6  → FPS  (lines{6,2})
    #   non-blank row 19 → SensorPCB Temperature before grab  (lines{19,2})
    #   non-blank row 20 → SensorPCB Temperature after grab   (lines{20,2})
    content = f"""\
## Stream Statistics
Frame count: {N_FRAMES}
Lost frames: 0
Error frames: 0
Missing packets: 0
FPS: 142.27
Network: 0.0 Mbits

## Configuration
nr_of_videos: 1
nr_of_images: {N_FRAMES}
exposure_time: 20.0
width: {N_PIX}
height: 32
offset_x: 0
offset_y: 0
combine_number_of_frames: 1
combine_frame_height: 32

## SensorPCB Temperature
SensorPCB Temperature before grab: 42.125 C
SensorPCB Temperature after grab: 42.125 C
"""
    output_path.write_text(content)
    print(f"[generate] {output_path}")


def main() -> None:
    tiff_path = _OUT / "test_sample.tiff"
    txt_path = _OUT / "test_sample.txt"
    _generate_tiff(tiff_path)
    _generate_txt(txt_path)
    print("[generate] done.")


if __name__ == "__main__":
    main()
