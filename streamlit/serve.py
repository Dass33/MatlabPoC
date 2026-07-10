"""Container entrypoint: streamlit server + idle probe.

The idle probe thread (see idle.py) must run from server start, not from the
first script run: a container kept alive only by reconnecting legacy tabs
never runs a script, so a probe started lazily from main.py would never get
the chance to kick those zombie sessions.

Server flags come from STREAMLIT_* environment variables (set in the
Dockerfile). bootstrap.run does not read them by itself the way the
`streamlit run` CLI does, so they are collected here and passed explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path

from streamlit import config as st_config
from streamlit.web import bootstrap

from idle import start_probe_writer


def _env_flag_options() -> dict:
    """Collect STREAMLIT_* env config the way the `streamlit run` CLI would.

    Iterates streamlit's internal config template (an internal API - recheck
    on streamlit upgrades; scripts/check_legacy_reconnect.py covers this).
    """
    opts = {}
    for key, option in st_config._config_options_template.items():
        val = os.environ.get(option.env_var)
        if val is None:
            continue
        if option.type is bool:
            opts[key] = val.lower() in ("true", "1", "y", "yes")
        elif option.type in (int, float):
            opts[key] = option.type(val)
        else:
            opts[key] = val
    return opts


def main() -> None:
    flag_options = _env_flag_options()
    bootstrap.load_config_options(flag_options)
    start_probe_writer()
    bootstrap.run(str(Path(__file__).parent / "main.py"), False, [], flag_options)


if __name__ == "__main__":
    main()
