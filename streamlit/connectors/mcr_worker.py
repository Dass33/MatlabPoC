"""Standalone MCR worker process.

Loads the compiled nsm_algorithms package (and with it the whole MATLAB
Runtime: JVM, TBB, its own libstdc++) in a process of its own, so a native
fault in that stack can never take down the Streamlit server. algorithms.py
spawns this script and talks a JSON-lines protocol:

  stdin           <- {"id": int, "fn": str, "args": [str, ...]}
  response pipe   -> {"id": int, "result": str} or {"id": int, "error": str}

Responses go to a dedicated pipe (fd passed as argv[1]) because the MCR
prints licensing and warning noise to stdout, which stays attached to the
container log. Must not import streamlit or any app module.
"""

from __future__ import annotations

import json
import os
import sys
import traceback


def main() -> int:
    out = os.fdopen(int(sys.argv[1]), "w", buffering=1)
    try:
        import nsm_algorithms  # type: ignore[import-not-found]

        pkg = nsm_algorithms.initialize()
    except Exception:
        out.write(json.dumps({"ready": False, "error": traceback.format_exc()}) + "\n")
        return 1
    out.write(json.dumps({"ready": True}) + "\n")

    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        try:
            result = getattr(pkg, req["fn"])(*req["args"], nargout=1)
            resp = {"id": req["id"], "result": str(result)}
        except Exception:
            resp = {"id": req["id"], "error": traceback.format_exc()}
        out.write(json.dumps(resp) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
