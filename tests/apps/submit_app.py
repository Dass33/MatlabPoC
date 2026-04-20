import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "streamlit"))

import streamlit as st
from config import DEFAULT_CONFIG
from submit import page_submit

st.session_state.setdefault("last_job_id", None)
st.session_state.setdefault("waiting", False)
st.session_state.setdefault("uploader_clear", 0)

page_submit(DEFAULT_CONFIG)
