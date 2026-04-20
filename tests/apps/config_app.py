import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "streamlit"))

import streamlit as st
from config import render_config_sidebar

config = render_config_sidebar()
st.session_state["_config"] = config
