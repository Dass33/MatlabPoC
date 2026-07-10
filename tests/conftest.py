from __future__ import annotations

import io

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect the job store to a per-test tmp dir.

    `job_dirs()` reads `env.DATA_DIR` at call time, but `storage` binds
    `DATA_DIR` by value at import (`from env import DATA_DIR`), so both bindings
    must be patched or `list_all_jobs` reads the real ./data/jobs.
    """
    import env
    from connectors import storage

    jobs = tmp_path / "jobs"
    jobs.mkdir()
    monkeypatch.setattr(env, "DATA_DIR", jobs)
    monkeypatch.setattr(storage, "DATA_DIR", jobs)
    return jobs


class FakeUpload(io.BytesIO):
    """Minimal stand-in for a Streamlit UploadedFile (needs .name and .seek)."""

    def __init__(self, name: str, data: bytes = b""):
        super().__init__(data)
        self.name = name


@pytest.fixture
def make_upload():
    return FakeUpload


@pytest.fixture
def tiny_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "black").save(buf, format="PNG")
    return buf.getvalue()
