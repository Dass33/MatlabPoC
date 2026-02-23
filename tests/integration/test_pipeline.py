"""Integration test: synthetic input → matlab-algorithm container → output validation.

Run with:
    pytest tests/integration/ --run-integration

Optional flags:
    --update-golden   write new golden reference values after a passing run
    --check-golden    compare outputs against committed golden reference values

Requires:
    - matlab-algorithm:latest image built locally  (see scripts/build_matlab.sh)
    - Docker daemon running
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from config import DEFAULT_CONFIG
from job_manager import job_dirs, read_status
from results import list_kymographs, load_summary, load_trajectories

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_GOLDEN = _FIXTURES / "golden"
_MATLAB_IMAGE = "matlab-algorithm:latest"
_RUNTIME = "/opt/matlabruntime/R2025b"
_TIMEOUT_S = 300


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def synthetic_job(tmp_path, monkeypatch):
    """Set up a job directory with synthetic input and integration-test config."""
    import job_manager
    monkeypatch.setattr(job_manager, "DATA_DIR", tmp_path)

    job_id = "integration_test"
    base = tmp_path / job_id
    inp = base / "input"
    out = base / "output"
    inp.mkdir(parents=True)
    out.mkdir(parents=True)

    shutil.copy(_FIXTURES / "test_sample.tiff", inp / "test_sample.tiff")
    shutil.copy(_FIXTURES / "test_sample.txt", inp / "test_sample.txt")

    # Smaller windows and more permissive detection for 500-frame synthetic data.
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy via JSON round-trip
    cfg["kymographPreprocessing"]["Wx"] = 10
    cfg["kymographPreprocessing"]["Wt"] = 30
    cfg["Detection"]["pfa"] = 1e-4
    cfg["Linking"]["minTrackLength"] = 5

    (base / "config.json").write_text(json.dumps(cfg, indent=2))
    return base, job_id


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run_matlab_container(job_dir: Path) -> None:
    """Run the MATLAB container synchronously and raise on non-zero exit."""
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{job_dir}:/job:rw",
            _MATLAB_IMAGE,
            _RUNTIME, "/job/input", "/job/output",
        ],
        timeout=_TIMEOUT_S,
        check=True,
    )


def _write_golden(traj: dict, summary: dict) -> None:
    _GOLDEN.mkdir(exist_ok=True)
    ref = {
        "n_trajectories": int(len(traj["iOC"])),
        "mean_iOC": float(summary["sweeps"][0]["MEAN"]["iOC"]),
    }
    (_GOLDEN / "reference.json").write_text(json.dumps(ref, indent=2))
    print(f"\n[golden] Written: {ref}")


def _check_golden(traj: dict, summary: dict) -> None:
    ref_file = _GOLDEN / "reference.json"
    if not ref_file.exists():
        pytest.skip("No golden reference — run with --update-golden first")
    ref = json.loads(ref_file.read_text())

    n = len(traj["iOC"])
    ref_n = ref["n_trajectories"]
    assert abs(n - ref_n) / max(ref_n, 1) <= 0.20, (
        f"Trajectory count {n} deviates from golden {ref_n} by more than 20%"
    )

    mean_iOC = summary["sweeps"][0]["MEAN"]["iOC"]
    ref_iOC = ref["mean_iOC"]
    assert abs(mean_iOC - ref_iOC) / max(abs(ref_iOC), 1e-9) <= 0.15, (
        f"mean iOC {mean_iOC:.4g} deviates from golden {ref_iOC:.4g} by more than 15%"
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_pipeline_runs_and_produces_outputs(synthetic_job, request):
    job_dir, job_id = synthetic_job

    _run_matlab_container(job_dir)

    status = read_status(job_id)
    assert status["status"] == "completed", (
        f"Pipeline did not complete. status={status['status']!r}, error={status.get('error')}"
    )

    _, _, out = job_dirs(job_id)
    assert (out / "trajectories.mat").exists(), "trajectories.mat not generated"
    assert (out / "summary.json").exists(), "summary.json not generated"
    assert list_kymographs(out), "no kymograph PNGs generated"

    traj = load_trajectories(out)
    assert traj is not None
    assert len(traj["iOC"]) > 0, "pipeline ran but detected zero trajectories"

    summary = load_summary(out)
    assert summary is not None
    assert len(summary.get("sweeps", [])) == 1, "expected exactly one sweep in summary"

    if request.config.getoption("--update-golden"):
        _write_golden(traj, summary)
    elif request.config.getoption("--check-golden"):
        _check_golden(traj, summary)
