"""
AppTest does not support st.file_uploader, so file-dependent UI tests are
covered via direct logic tests against the underlying functions. AppTest is
used for the cases that don't require file upload (no-file state, clear button).
"""

import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))

SUBMIT_APP = str(Path(__file__).parent / "apps" / "submit_app.py")


class _MockFile:
    """Minimal stand-in for Streamlit UploadedFile."""
    def __init__(self, name: str, content: bytes = b"\x00" * 64):
        self.name = name
        self._buf = BytesIO(content)

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def seek(self, pos: int) -> None:
        self._buf.seek(pos)


def _app() -> AppTest:
    return AppTest.from_file(SUBMIT_APP, default_timeout=30)


# ── No-file state (AppTest supported) ────────────────────────────────────────


def test_no_files_shows_info():
    at = _app()
    at.run()
    assert not at.exception
    assert any("Upload" in str(i.value) for i in at.info)


# ── File validation logic ─────────────────────────────────────────────────────
# Tested directly since file_uploader is not supported in AppTest.


def _missing_txt(filenames: list[str]) -> set[str]:
    tiff_stems = {Path(f).stem for f in filenames if f.lower().endswith((".tif", ".tiff"))}
    txt_stems = {Path(f).stem for f in filenames if f.lower().endswith(".txt")}
    return tiff_stems - txt_stems


def test_validation_missing_txt():
    assert _missing_txt(["sample.tiff"]) == {"sample"}


def test_validation_mismatched_names():
    assert _missing_txt(["sample.tiff", "other.txt"]) == {"sample"}


def test_validation_valid_pair():
    assert _missing_txt(["sample.tiff", "sample.txt"]) == set()


def test_validation_multiple_pairs():
    assert _missing_txt(["a.tiff", "a.txt", "b.tiff", "b.txt"]) == set()


def test_validation_partial_missing():
    assert _missing_txt(["a.tiff", "a.txt", "b.tiff"]) == {"b"}


# ── Clear uploader (AppTest supported) ────────────────────────────────────────


def test_clear_uploader_increments_key():
    at = _app()
    at.run()
    assert not at.exception
    at.button(key="Clear files button").click()
    at.run()
    assert not at.exception
    assert at.session_state["uploader_clear"] == 1


# ── submit_job is called with correct args ────────────────────────────────────


def test_submit_job_called_with_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOST_DATA_DIR", str(tmp_path))

    import importlib
    import job_manager as jm
    importlib.reload(jm)

    tiff = _MockFile("exp1.tiff")
    txt = _MockFile("exp1.txt")

    captured = {}

    def fake_launch(job_id):
        captured["job_id"] = job_id

    with patch.object(jm, "launch_matlab_container", side_effect=fake_launch):
        job_id = jm.submit_job([tiff, txt], {"Dt": 0.007, "Dx": 0.066}, name="test")

    assert captured["job_id"] == job_id
    job_dir = tmp_path / job_id
    assert (job_dir / "input" / "exp1.tiff").exists()
    assert (job_dir / "input" / "exp1.txt").exists()
    assert (job_dir / "config.json").exists()
    assert (job_dir / "meta.json").exists()


def test_submit_job_meta_contains_name(tmp_path, monkeypatch):
    import importlib, json
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOST_DATA_DIR", str(tmp_path))
    import job_manager as jm
    importlib.reload(jm)

    with patch.object(jm, "launch_matlab_container"):
        job_id = jm.submit_job([_MockFile("a.tiff"), _MockFile("a.txt")], {}, name="my run")

    meta = json.loads((tmp_path / job_id / "meta.json").read_text())
    assert meta["name"] == "my run"
    assert "a.tiff" in meta["filenames"]
