"""
Layer 2 integration tests for population analysis.
Require Docker + matlab-algorithm:latest. Run with: pytest --run-integration
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))


@pytest.mark.integration
def test_population_analysis_robustmean(postprocessed_job):
    import matlab_bridge

    jm = postprocessed_job["jm"]
    _, _, out = jm.job_dirs(postprocessed_job["job_id"])
    data = json.loads((out / "collection_postprocessed.json").read_text())
    collection = data["collection"]

    props = [p for p in ("iOC", "D", "velocity", "N") if p in collection]
    result = matlab_bridge.run_population_analysis(
        collection,
        {"Title": "robustMean", "properties": props},
    )

    for prop in props:
        assert prop in result
        for key in ("MEAN", "STD", "FWHM", "RESOLUTION"):
            assert key in result[prop], f"Missing {key} in result[{prop}]"


@pytest.mark.integration
def test_population_analysis_gaussfit(postprocessed_job):
    import matlab_bridge

    jm = postprocessed_job["jm"]
    _, _, out = jm.job_dirs(postprocessed_job["job_id"])
    data = json.loads((out / "collection_postprocessed.json").read_text())
    collection = data["collection"]

    props = [p for p in ("iOC", "D", "velocity") if p in collection]
    result = matlab_bridge.run_population_analysis(
        collection,
        {"Title": "gaussFit", "properties": props},
    )

    for prop in props:
        assert prop in result
        assert "MEAN" in result[prop]
        assert "STD" in result[prop]


@pytest.mark.integration
def test_population_saves_json(postprocessed_job):
    import matlab_bridge
    import numpy as np

    jm = postprocessed_job["jm"]
    _, _, out = jm.job_dirs(postprocessed_job["job_id"])
    data = json.loads((out / "collection_postprocessed.json").read_text())
    collection = data["collection"]
    props = [p for p in ("iOC", "D", "velocity") if p in collection]

    result = matlab_bridge.run_population_analysis(
        collection, {"Title": "robustMean", "properties": props}
    )

    def _default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(type(obj))

    pop_path = out / "population.json"
    pop_path.write_text(json.dumps({
        "method": "robustMean",
        "properties": props,
        "n_trajectories": data["n_kept"],
        "results": {
            p: {k: v for k, v in r.items() if not k.startswith("_")}
            for p, r in result.items()
        },
    }, indent=2, default=_default))

    assert pop_path.exists()
    saved = json.loads(pop_path.read_text())
    assert saved["method"] == "robustMean"
    assert set(saved["properties"]) == set(props)
    assert "results" in saved


@pytest.mark.integration
def test_population_no_postprocessed_file(completed_job):
    """population.py should show a warning when no postprocessed file exists."""
    jm = completed_job["jm"]
    _, _, out = jm.job_dirs(completed_job["job_id"])

    pp_path = out / "collection_postprocessed.json"
    existed = pp_path.exists()
    backed_up = None
    if existed:
        backed_up = pp_path.read_bytes()
        pp_path.unlink()

    try:
        import sys
        from pathlib import Path
        from streamlit.testing.v1 import AppTest

        test_file = Path("/tmp/test_population_page.py")
        test_file.write_text(f"""
import sys
sys.path.insert(0, "{Path(__file__).parent.parent / "streamlit"}")
from population import page_population_analysis
page_population_analysis("{completed_job["job_id"]}")
""")
        at = AppTest.from_file(str(test_file), default_timeout=15)
        at.run()
        assert not at.exception
        assert any(at.warning) or any(at.info)
    finally:
        if backed_up is not None:
            pp_path.write_bytes(backed_up)
        if test_file.exists():
            test_file.unlink()
