"""End-to-end tests for the MCR worker subprocess bridge.

Runs the real mcr_worker.py child process with a fake nsm_algorithms module
injected via PYTHONPATH, so the spawn/protocol/restart logic in algorithms.py
is exercised without MATLAB.
"""

from __future__ import annotations

import textwrap

import pytest

from connectors import algorithms

FAKE_PKG = textwrap.dedent(
    """
    import json

    class _Pkg:
        def runOutlierFiltering(self, collection_json, setting_json, nargout=1):
            data = json.loads(collection_json)
            if data.get("boom"):
                raise ValueError("matlab says no")
            return json.dumps([True, False])

        def runPopulationAnalysis(self, collection_json, setting_json, nargout=1):
            return json.dumps({"echo": json.loads(setting_json)})

        def runPostprocessing(self, c, s, k, f, nargout=1):
            return json.dumps({"notOutlier": [1]})

    def initialize():
        return _Pkg()
    """
)


@pytest.fixture
def worker(tmp_path, monkeypatch):
    (tmp_path / "nsm_algorithms.py").write_text(FAKE_PKG)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    monkeypatch.setattr(algorithms, "_pkg", None)
    yield
    if algorithms._pkg is not None and algorithms._pkg.alive():
        algorithms._pkg._kill()


def test_roundtrip_through_worker_process(worker):
    pkg = algorithms._get_pkg()
    assert pkg.alive()
    result = pkg.runOutlierFiltering('{"iOC": [1.0]}', "{}")
    assert result == "[true, false]"
    assert pkg.runPopulationAnalysis("{}", '{"bins": 5}') == '{"echo": {"bins": 5}}'


def test_matlab_error_propagates_and_worker_survives(worker):
    pkg = algorithms._get_pkg()
    with pytest.raises(RuntimeError, match="matlab says no"):
        pkg.runOutlierFiltering('{"boom": true}', "{}")
    # the worker survives an in-MATLAB error and keeps serving
    assert pkg.alive()
    assert pkg.runOutlierFiltering('{"iOC": [1.0]}', "{}") == "[true, false]"


def test_dead_worker_is_restarted_on_next_call(worker):
    first = algorithms._get_pkg()
    first._proc.kill()
    first._proc.wait()
    second = algorithms._get_pkg()
    assert second is not first
    assert second.runOutlierFiltering("{}", "{}") == "[true, false]"


def test_call_on_dying_worker_raises_then_recovers(worker):
    pkg = algorithms._get_pkg()
    pkg._proc.kill()
    pkg._proc.wait()
    with pytest.raises(RuntimeError, match="runOutlierFiltering failed"):
        pkg.runOutlierFiltering("{}", "{}")
    assert algorithms._get_pkg().runOutlierFiltering("{}", "{}") == "[true, false]"


def test_import_failure_surfaces_as_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))  # no nsm_algorithms here
    monkeypatch.setattr(algorithms, "_pkg", None)
    with pytest.raises(RuntimeError, match="failed to start"):
        algorithms._get_pkg()
