from __future__ import annotations

import base64
import html
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from env import TZ, job_dirs

log = logging.getLogger(__name__)

_MICRO_PROPS = frozenset({"iOC", "STDiOC"})
_SCALED_KEYS = frozenset({"MEAN", "STD", "FWHM"})

_KEY_PARAMS = [
    ("Dt", ("Dt",)),
    ("Dx", ("Dx",)),
    ("flowEstimate", ("flowEstimate",)),
    ("flipIntensity", ("flipIntensity",)),
    ("tracker", ("tracker",)),
    ("Detection.peakSign", ("Detection", "peakSign")),
    ("Detection.pfa", ("Detection", "pfa")),
    ("Linking.minTrackLength", ("Linking", "minTrackLength")),
    ("kymographPreprocessing.removeBackground", ("kymographPreprocessing", "removeBackground")),
    ("kymographPreprocessing.Wx", ("kymographPreprocessing", "Wx")),
    ("kymographPreprocessing.Wt", ("kymographPreprocessing", "Wt")),
]

_SCATTER_PAIRS = [("iOC", "velocity"), ("iOC", "D"), ("N", "iOC")]

_CSS = """
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
  line-height: 1.5;
}
h1 { font-size: 1.6rem; margin-bottom: 0.2rem; }
h2 { font-size: 1.2rem; margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th { background: #f4f4f4; }
.meta { color: #555; font-size: 0.9rem; }
.meta div { margin: 0.1rem 0; }
figure { display: inline-block; margin: 0.5rem; text-align: center; max-width: 260px; vertical-align: top; }
figure img { max-width: 100%; border: 1px solid #ddd; }
figcaption { font-size: 0.8rem; color: #555; word-break: break-all; }
details summary { cursor: pointer; font-weight: 600; margin-top: 1rem; }
pre { background: #f4f4f4; padding: 1rem; overflow-x: auto; white-space: pre-wrap; }
.note { color: #777; font-style: italic; }
"""


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("[report] could not read %s: %s", path, e)
        return None


def _display_val(prop: str, key: str, val: float) -> float:
    if prop in _MICRO_PROPS and key in _SCALED_KEYS:
        return val * 1e6
    return val


def _build_header(job_id: str, meta: dict[str, Any] | None) -> str:
    meta = meta or {}
    name = meta.get("name") or job_id
    filenames = meta.get("filenames") or []
    parent_job_id = meta.get("parent_job_id")

    lines = [
        f"<h1>{html.escape(str(name))}</h1>",
        '<div class="meta">',
        f"<div>Job ID: {html.escape(job_id)}</div>",
        f"<div>Submitted: {html.escape(str(meta.get('submitted_at', '-')))}</div>",
        f"<div>Input files: {html.escape(', '.join(filenames)) if filenames else '-'}</div>",
        f"<div>Report generated: {html.escape(datetime.now(TZ).isoformat(timespec='seconds'))}</div>",
    ]
    if parent_job_id:
        lines.append(f"<div>Cloned from: {html.escape(str(parent_job_id))}</div>")
    lines.append("</div>")
    return "\n".join(lines)


def _build_population_section(population: dict[str, Any] | None) -> str:
    if population is None:
        return ""
    props = population.get("properties") or []
    results = population.get("results") or {}
    keys = ["MEAN", "STD", "FWHM", "RESOLUTION"]

    rows = []
    for prop in props:
        r = results.get(prop, {})
        label = f"{prop} (µ)" if prop in _MICRO_PROPS else prop
        cells = "".join(
            f"<td>{_display_val(prop, k, r[k]):.6g}</td>" if k in r else "<td>-</td>"
            for k in keys
        )
        rows.append(f"<tr><td>{html.escape(label)}</td>{cells}</tr>")

    header_cells = "".join(f"<th>{k}</th>" for k in keys)
    caption = (
        f"Method: {html.escape(str(population.get('method', '-')))}, "
        f"trajectories: {html.escape(str(population.get('n_trajectories', '-')))}"
    )
    return f"""
<h2>Population Statistics</h2>
<p class="meta">{caption}</p>
<table>
<thead><tr><th>Property</th>{header_cells}</tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
"""


def _build_postprocessing_section(postprocessed: dict[str, Any] | None) -> str:
    if postprocessed is None:
        return ""
    n_kept = postprocessed.get("n_kept", "?")
    n_total = postprocessed.get("n_total", "?")
    return f"""
<h2>Postprocessing</h2>
<p>{html.escape(str(n_kept))} of {html.escape(str(n_total))} trajectories kept.</p>
"""


def _build_kymographs_section(kymo_dir: Path) -> str:
    files = sorted(kymo_dir.glob("*.png")) if kymo_dir.is_dir() else []
    if not files:
        return '<h2>Kymographs</h2>\n<p class="note">No kymographs available.</p>'

    figures = []
    for f in files:
        try:
            b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        except OSError as e:
            log.warning("[report] could not read kymograph %s: %s", f, e)
            continue
        figures.append(
            f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(f.name)}">'
            f"<figcaption>{html.escape(f.name)}</figcaption></figure>"
        )
    body = "\n".join(figures) if figures else '<p class="note">No kymographs available.</p>'
    return f"<h2>Kymographs</h2>\n{body}"


def _config_lookup(config: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = config
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _build_key_params_section(config: dict[str, Any] | None) -> str:
    if config is None:
        return ""
    rows = []
    for label, path in _KEY_PARAMS:
        val = _config_lookup(config, path)
        if val is None:
            continue
        rows.append(f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(val))}</td></tr>")
    if not rows:
        return ""
    return f"""
<h2>Key Parameters</h2>
<table>
<thead><tr><th>Parameter</th><th>Value</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
"""


def _scatter_png(x_prop: str, y_prop: str, x: list[float], y: list[float]) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = min(len(x), len(y))
    x_vals = [v * 1e6 if x_prop in _MICRO_PROPS else v for v in x[:n]]
    y_vals = [v * 1e6 if y_prop in _MICRO_PROPS else v for v in y[:n]]
    x_label = f"{x_prop} (µ)" if x_prop in _MICRO_PROPS else x_prop
    y_label = f"{y_prop} (µ)" if y_prop in _MICRO_PROPS else y_prop

    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    try:
        ax.scatter(x_vals, y_vals, s=8)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    finally:
        plt.close(fig)

    caption = f"{x_prop} vs {y_prop}"
    return (
        f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(caption)}">'
        f"<figcaption>{html.escape(caption)}</figcaption></figure>"
    )


def _build_data_section(collection: dict[str, Any] | None, calibrated: bool) -> str:
    if not collection:
        return ""
    try:
        figures = []
        for x_prop, y_prop in _SCATTER_PAIRS:
            x = collection.get(x_prop)
            y = collection.get(y_prop)
            if not x or not y:
                continue
            figures.append(_scatter_png(x_prop, y_prop, x, y))
        if not figures:
            return ""
        note = "Kept trajectories" + (", iOC calibrated" if calibrated else "")
        return f'<h2>Data</h2>\n<p class="note">{note}.</p>\n{"".join(figures)}'
    except Exception as e:
        log.warning("[report] could not build data plots: %s", e)
        return ""


def _build_config_section(config: dict[str, Any] | None) -> str:
    if config is None:
        return ""
    pretty = html.escape(json.dumps(config, indent=2))
    return f"""
<h2>Configuration</h2>
<details>
<summary>Full config</summary>
<pre>{pretty}</pre>
</details>
"""


def build_report(job_id: str) -> str:
    base, _, out = job_dirs(job_id)

    meta = _read_json(base / "meta.json")
    config = _read_json(base / "config.json")
    population = _read_json(out / "population.json")
    postprocessed = _read_json(out / "collection_postprocessed.json")
    collection = (postprocessed or {}).get("collection")
    calibrated = bool((postprocessed or {}).get("calibration"))

    sections = [
        _build_header(job_id, meta),
        _build_kymographs_section(out / "kymographs"),
        _build_postprocessing_section(postprocessed),
        _build_data_section(collection, calibrated),
        _build_population_section(population),
        _build_key_params_section(config),
        _build_config_section(config),
    ]

    title = html.escape(str((meta or {}).get("name") or job_id))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Report - {title}</title>
<style>{_CSS}</style>
</head>
<body>
{"".join(s for s in sections if s)}
</body>
</html>
"""
