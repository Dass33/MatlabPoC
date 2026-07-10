"""End-to-end coverage of the postprocessing and population tabs against REAL
MATLAB, driven through the Streamlit script with AppTest.

Flow mirrors real usage:
  seed collection.mat -> Post-processing "Accept & Save" (runs real MATLAB
  run_postprocessing, writes collection_postprocessed.json) -> Population
  "Run Population Analysis" (runs real MATLAB run_population_analysis).

Requires the MATLAB runtime, so it is skipped by a plain `pytest` run. Enable
with scripts/run_matlab_tests.sh (or -m integration once LD_LIBRARY_PATH is set).
"""

from __future__ import annotations

import json

import pytest

# Skip cleanly when the compiled MATLAB package / runtime isn't available.
try:
    import nsm_algorithms  # type: ignore[import-not-found]  # noqa: F401
except Exception as e:  # noqa: BLE001
    pytest.skip(
        f"compiled MATLAB runtime unavailable ({e})", allow_module_level=True
    )

from streamlit.testing.v1 import AppTest  # noqa: E402

from connectors import algorithms, storage  # noqa: E402
from sample_data import sample_collection, write_collection_mat  # noqa: E402

pytestmark = pytest.mark.integration

APP = "streamlit/main.py"


@pytest.fixture(scope="module", autouse=True)
def _require_mcr():
    try:
        algorithms._get_pkg()
    except Exception as e:  # runtime present but init fails
        pytest.skip(f"MCR unavailable: {e}")


# robustMean returns null stats below a minimum trajectory count, so keep the
# sample comfortably above it for a meaningful population result.
_N_TRAJ = 40


def _seed_job_with_collection(make_upload, name="e2e job"):
    job_id = storage.create_job([make_upload("a.tif", b"x")], {}, name=name)
    _, _, out = storage.job_dirs(job_id)
    write_collection_mat(out, sample_collection(n=_N_TRAJ, length=30))
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))
    return job_id


def _run_app(job_id):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["active_experiment"] = job_id
    return at.run()


def test_postprocessing_accept_save_writes_postprocessed_collection(make_upload):
    job_id = _seed_job_with_collection(make_upload)
    at = _run_app(job_id)
    assert not at.exception

    # scatter + thresholds rendered; find & click Accept & Save (real MATLAB run)
    accept = [b for b in at.button if b.key == f"pp_apply_{job_id}"]
    assert len(accept) == 1, "Accept & Save button not rendered"
    accept[0].click().run()
    assert not at.exception

    _, _, out = storage.job_dirs(job_id)
    pp = out / "collection_postprocessed.json"
    assert pp.exists(), "postprocessing did not persist collection_postprocessed.json"
    data = json.loads(pp.read_text())
    assert data["n_total"] == _N_TRAJ
    assert 0 < data["n_kept"] <= _N_TRAJ
    assert "iOC" in data["collection"]


def test_population_analysis_runs_and_persists(make_upload):
    job_id = _seed_job_with_collection(make_upload)

    # First produce the postprocessed collection the population tab consumes.
    at = _run_app(job_id)
    [b for b in at.button if b.key == f"pp_apply_{job_id}"][0].click().run()
    _, _, out = storage.job_dirs(job_id)
    assert (out / "collection_postprocessed.json").exists()

    # Narrow the property selection to physical props that yield real stats.
    # (The default selection includes N, which nulls the whole MATLAB result for
    # this synthetic data — see the flagged _display_val None-handling issue.)
    at.multiselect(key=f"pop_props_{job_id}").set_value(["iOC", "D", "velocity"]).run()

    # Now drive the population tab: click Run Population Analysis (real MATLAB).
    run_btn = [b for b in at.button if b.key == f"pop_run_{job_id}"]
    assert len(run_btn) == 1, "Run Population Analysis button not rendered"
    run_btn[0].click().run()
    assert not at.exception

    pop = out / "population.json"
    assert pop.exists(), "population analysis did not persist population.json"
    saved = json.loads(pop.read_text())
    assert saved["method"] in ("robustMean", "gaussFit")
    assert "iOC" in saved["results"]
    assert "MEAN" in saved["results"]["iOC"]
