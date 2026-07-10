"""UI-flow tests driving the real Streamlit script via AppTest.

These import and execute main.py, so they cover the tab wiring, sidebar, and
experiment selector that the pure-logic tests can't reach. MATLAB stays out of
the picture: MCR warm-up runs in a daemon thread that swallows import errors,
and any tab that would call MATLAB is either given a None job or mocked.
"""

from __future__ import annotations

import json

from streamlit.testing.v1 import AppTest

from connectors import storage

APP = "streamlit/main.py"


def _seed_completed_job(make_upload, name="run one"):
    job_id = storage.create_job([make_upload("a.tif", b"x")], {"foo": 1}, name=name)
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))
    return job_id


def test_app_renders_all_tabs_without_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    labels = [t.label for t in at.tabs]
    assert labels == [
        "Submit",
        "Kymograph Analysis",
        "Post-processing",
        "Population Analysis",
        "Overview",
        "Help",
    ]


def test_experiment_selector_absent_without_completed_jobs():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert not any(sb.label == "Active experiment" for sb in at.selectbox)


def test_experiment_selector_lists_completed_job(make_upload):
    _seed_completed_job(make_upload, name="my experiment")
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    selector = [sb for sb in at.selectbox if sb.label == "Active experiment"]
    assert len(selector) == 1
    # options are shown via format_func -> the job's display name
    assert selector[0].options == ["my experiment"]


def test_tutorial_banner_shows_with_query_param():
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["tutorial"] = "on"
    at.run()
    assert not at.exception
    assert any("New here?" in md.value for md in at.markdown)
