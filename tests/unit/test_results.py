"""Unit tests for streamlit/results.py."""
from __future__ import annotations

import json

import numpy as np
import scipy.io

from results import list_kymographs, load_summary, load_trajectories


class TestLoadSummary:
    def test_missing_file_returns_none(self, tmp_path):
        assert load_summary(tmp_path) is None

    def test_valid_json_parsed_to_dict(self, tmp_path):
        payload = {"sweeps": [{"MEAN": {"iOC": 1.5}, "legend": "Wx=10"}]}
        (tmp_path / "summary.json").write_text(json.dumps(payload))
        result = load_summary(tmp_path)
        assert result is not None
        assert result["sweeps"][0]["MEAN"]["iOC"] == 1.5

    def test_malformed_json_calls_st_error_and_returns_none(self, tmp_path, mocker):
        mock_error = mocker.patch("streamlit.error")
        (tmp_path / "summary.json").write_text("{bad json")
        result = load_summary(tmp_path)
        assert result is None
        mock_error.assert_called_once()


class TestListKymographs:
    def test_no_kymographs_dir_returns_empty(self, tmp_path):
        assert list_kymographs(tmp_path) == []

    def test_empty_kymographs_dir_returns_empty(self, tmp_path):
        (tmp_path / "kymographs").mkdir()
        assert list_kymographs(tmp_path) == []

    def test_three_pngs_returned_sorted(self, tmp_path):
        kymo_dir = tmp_path / "kymographs"
        kymo_dir.mkdir()
        for name in ("c_run.png", "a_run.png", "b_run.png"):
            (kymo_dir / name).touch()
        result = list_kymographs(tmp_path)
        assert [p.name for p in result] == ["a_run.png", "b_run.png", "c_run.png"]

    def test_non_png_files_excluded(self, tmp_path):
        kymo_dir = tmp_path / "kymographs"
        kymo_dir.mkdir()
        (kymo_dir / "track.png").touch()
        (kymo_dir / "track.jpg").touch()
        (kymo_dir / "notes.txt").touch()
        result = list_kymographs(tmp_path)
        assert len(result) == 1
        assert result[0].name == "track.png"


class TestLoadTrajectories:
    def test_missing_file_returns_none(self, tmp_path):
        assert load_trajectories(tmp_path) is None

    def test_valid_mat_returns_expected_keys(self, tmp_path, mat_fixture):
        mat_fixture.rename(tmp_path / "trajectories.mat")
        result = load_trajectories(tmp_path)
        assert result is not None
        expected_keys = {"iOC", "D", "velocity", "N", "positionStart", "positionEnd", "sweepIdx", "sweepLegends"}
        assert expected_keys.issubset(result.keys())

    def test_arrays_are_1d(self, tmp_path, mat_fixture):
        mat_fixture.rename(tmp_path / "trajectories.mat")
        result = load_trajectories(tmp_path)
        for key in ("iOC", "D", "velocity", "N", "positionStart", "positionEnd", "sweepIdx"):
            assert result[key].ndim == 1, f"{key} should be 1-D"

    def test_sweep_idx_is_integer_array(self, tmp_path, mat_fixture):
        mat_fixture.rename(tmp_path / "trajectories.mat")
        result = load_trajectories(tmp_path)
        assert result["sweepIdx"].dtype in (int, "int32", "int64", "int_")

    def test_sweep_legends_is_list_of_strings(self, tmp_path, mat_fixture):
        mat_fixture.rename(tmp_path / "trajectories.mat")
        result = load_trajectories(tmp_path)
        assert isinstance(result["sweepLegends"], list)
        assert all(isinstance(s, str) for s in result["sweepLegends"])
        assert result["sweepLegends"][0] == "Wx=10,Wt=30"

    def test_corrupt_mat_calls_st_error_and_returns_none(self, tmp_path, mocker):
        mock_error = mocker.patch("streamlit.error")
        (tmp_path / "trajectories.mat").write_bytes(b"not a mat file")
        result = load_trajectories(tmp_path)
        assert result is None
        mock_error.assert_called_once()
