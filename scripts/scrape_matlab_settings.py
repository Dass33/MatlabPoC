"""Scrape `Setting.*` parameters from a MATLAB control script.

Not a MATLAB parser -- a line scraper for the flat `Setting.a.b = literal; % comment`
convention used in nsm-data-analysis control scripts. Dev-time tool: run it after
pulling the matlab submodule to see what changed.

Usage:
    python scripts/scrape_matlab_settings.py matlab/nsm-data-analysis/AnalyzeExperiment.m
    python scripts/scrape_matlab_settings.py --diff matlab/nsm-data-analysis/AnalyzeExperiment.m

Plain mode lists every scraped parameter. --diff compares against the app's
Config dataclass defaults and reports added / removed / changed parameters.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ASSIGN = re.compile(r"^\s*Setting\.([\w.]+)\s*=\s*(.+?);\s*(?:%\s*(.*))?$")
SWITCH = re.compile(r"^\s*switch\s+\S+")
CASE = re.compile(r"^\s*case\s+'([^']+)'")
END = re.compile(r"^\s*end\b")

# MATLAB setting path -> app config path, for params the app names differently
ALIASES = {
    "trajectoryDetecton.Title": "tracker",
    "kymographAnalysis.trajectoryProperties": "trajectoryProperties",
}

# populated by the app itself, never user-facing
IGNORED_PREFIXES = ("Path.",)


def matlab_literal(src: str):
    src = src.strip()
    if src.startswith("'") and src.endswith("'"):
        return src[1:-1]
    if src.startswith("{"):
        return re.findall(r"'([^']*)'", src)
    try:
        f = float(src)
        return (
            int(f)
            if f.is_integer() and "." not in src and "e" not in src.lower()
            else f
        )
    except ValueError:
        return src  # expression or variable reference, keep raw


def scrape(path: Path) -> list[dict]:
    params = []
    case_ctx = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if SWITCH.match(line):
            case_ctx = None
        elif m := CASE.match(line):
            case_ctx = m.group(1)
        elif END.match(line):
            case_ctx = None
        elif m := ASSIGN.match(line):
            name, raw, comment = m.groups()
            if name.startswith(IGNORED_PREFIXES):
                continue
            params.append(
                {
                    "path": name,
                    "value": matlab_literal(raw),
                    "comment": (comment or "").strip(),
                    "only_when": case_ctx,
                }
            )
    return params


def _normalize(v):
    if v == "true":
        return True
    if v == "false":
        return False
    return v


def _flatten(d: dict, prefix: str = "") -> dict:
    flat = {}
    for k, v in d.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            flat.update(_flatten(v, f"{path}."))
        else:
            flat[path] = v
    return flat


def print_params(params: list[dict]) -> None:
    for p in params:
        ctx = f"  [only: {p['only_when']}]" if p["only_when"] else ""
        val = repr(p["value"])
        if len(val) > 40:
            val = val[:37] + "..."
        print(f"{p['path']:50s} = {val:42s}{ctx}")
        if p["comment"]:
            print(f"{'':50s}   # {p['comment'][:100]}")


def print_diff(params: list[dict]) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "streamlit"))
    from dataclasses import asdict

    from config import Config

    app = _flatten(asdict(Config()))
    matlab = {ALIASES.get(p["path"], p["path"]): p for p in params}

    added = [p for path, p in matlab.items() if path not in app]
    removed = sorted(set(app) - set(matlab))
    changed = [
        (path, app[path], p["value"])
        for path, p in matlab.items()
        if path in app and _normalize(p["value"]) != app[path]
    ]

    if added:
        print("In MATLAB script but not in app Config:")
        for p in added:
            ctx = f"  [only: {p['only_when']}]" if p["only_when"] else ""
            print(f"  + {p['path']} = {p['value']!r}{ctx}")
            if p["comment"]:
                print(f"      # {p['comment'][:100]}")
    if removed:
        print("\nIn app Config but not in MATLAB script:")
        for path in removed:
            print(f"  - {path} = {app[path]!r}")
    if changed:
        print("\nDefault mismatches (app vs MATLAB):")
        for path, ours, theirs in changed:
            print(f"  ~ {path}: {ours!r} -> {theirs!r}")
    if not (added or removed or changed):
        print("No drift: MATLAB script and app Config agree.")


def main() -> None:
    args = sys.argv[1:]
    diff = "--diff" in args
    paths = [a for a in args if a != "--diff"]
    if len(paths) != 1:
        sys.exit(__doc__)
    params = scrape(Path(paths[0]))
    if diff:
        print_diff(params)
    else:
        print_params(params)


if __name__ == "__main__":
    main()
