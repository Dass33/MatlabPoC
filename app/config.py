import json

import streamlit as st

# Default configuration values
DEFAULT_CONFIG = {
    "kt_val": 159.0,
    "space_filter": "jinc",
    "sigma_x": 2.97,
    "time_filter": "imgaussfilt",
    "sigma_t": 1.19,
    "non_linear_filter": "none",
    "pfa": 1e-5,
    "local_min_range": 6,
    "refinement_method": "centroid",
    "fitting_radius": 3,
    "cut_off_distance": 20.0,
    "unmatched_penalty": 15.0,
    "flow_estimate": 0.0,
    "min_track_len": 40,
    "max_pos_gap": 3,
    "max_neg_gap": 2,
    "gap_closing_dist": 40.0,
    "gap_closing_penalty": 30.0,
    "plot_width": 12,
    "plot_height": 8,
    "padding": 2,
}


def render_sidebar_config():
    """Renders sidebar and returns a dictionary of configuration parameters."""
    st.sidebar.header("Configuration")

    # --- Configuration Import/Export ---
    with st.sidebar.expander("💾 Save/Load Config"):
        uploaded_config = st.file_uploader("Load Config (JSON)", type=["json"])
        if uploaded_config:
            try:
                loaded_conf = json.load(uploaded_config)
                for k, v in loaded_conf.items():
                    if k in st.session_state and st.session_state[k] != v:
                        st.session_state[k] = v
                st.success("Config loaded!")
            except Exception as e:
                st.error(f"Error loading config: {e}")

    config = {}

    with st.sidebar.expander("Preprocessing", expanded=True):
        config["kt_val"] = st.number_input(
            "Kt (Background Estimation)",
            value=DEFAULT_CONFIG["kt_val"],
            step=1.0,
            key="kt_val",
        )

    with st.sidebar.expander("Denoising"):
        config["space_filter"] = st.selectbox(
            "Space Filter",
            ["jinc", "gaussian", "laplacean_of_gaussian", "none"],
            index=["jinc", "gaussian", "laplacean_of_gaussian", "none"].index(
                DEFAULT_CONFIG["space_filter"]
            ),
            key="space_filter",
        )
        config["sigma_x"] = st.number_input(
            "Sigma X", value=DEFAULT_CONFIG["sigma_x"], step=0.1, key="sigma_x"
        )
        config["time_filter"] = st.selectbox(
            "Time Filter",
            ["imgaussfilt", "none"],
            index=["imgaussfilt", "none"].index(DEFAULT_CONFIG["time_filter"]),
            key="time_filter",
        )
        config["sigma_t"] = st.number_input(
            "Sigma T", value=DEFAULT_CONFIG["sigma_t"], step=0.1, key="sigma_t"
        )
        config["non_linear_filter"] = st.selectbox(
            "Non-Linear Filter",
            ["none", "nlm"],
            index=["none", "nlm"].index(DEFAULT_CONFIG["non_linear_filter"]),
            key="non_linear_filter",
        )

    with st.sidebar.expander("Detection"):
        config["pfa"] = st.number_input(
            "Probability of False Alarm (pfa)",
            value=DEFAULT_CONFIG["pfa"],
            format="%.e",
            key="pfa",
        )
        config["local_min_range"] = st.number_input(
            "Local Min Range",
            value=DEFAULT_CONFIG["local_min_range"],
            step=1,
            key="local_min_range",
        )

    with st.sidebar.expander("Feature Extraction"):
        config["refinement_method"] = st.selectbox(
            "Refinement Method",
            ["centroid", "parabolic", "gaussian"],
            index=["centroid", "parabolic", "gaussian"].index(
                DEFAULT_CONFIG["refinement_method"]
            ),
            key="refinement_method",
        )
        config["fitting_radius"] = st.number_input(
            "Fitting Radius",
            value=DEFAULT_CONFIG["fitting_radius"],
            step=1,
            key="fitting_radius",
        )

    with st.sidebar.expander("Linking / Tracking"):
        config["cut_off_distance"] = st.number_input(
            "Cut-off Distance",
            value=DEFAULT_CONFIG["cut_off_distance"],
            step=1.0,
            key="cut_off_distance",
        )
        config["unmatched_penalty"] = st.number_input(
            "Unmatched Penalty",
            value=DEFAULT_CONFIG["unmatched_penalty"],
            step=1.0,
            key="unmatched_penalty",
        )
        config["flow_estimate"] = st.number_input(
            "Flow Estimate",
            value=DEFAULT_CONFIG["flow_estimate"],
            step=0.1,
            key="flow_estimate",
        )
        config["min_track_len"] = st.number_input(
            "Min Track Length",
            value=DEFAULT_CONFIG["min_track_len"],
            step=1,
            key="min_track_len",
        )

        st.caption("Gap Closing")
        config["max_pos_gap"] = st.number_input(
            "Max Positive Gap",
            value=DEFAULT_CONFIG["max_pos_gap"],
            step=1,
            key="max_pos_gap",
        )
        config["max_neg_gap"] = st.number_input(
            "Max Negative Gap",
            value=DEFAULT_CONFIG["max_neg_gap"],
            step=1,
            key="max_neg_gap",
        )
        config["gap_closing_dist"] = st.number_input(
            "Gap Closing Dist",
            value=DEFAULT_CONFIG["gap_closing_dist"],
            step=1.0,
            key="gap_closing_dist",
        )
        config["gap_closing_penalty"] = st.number_input(
            "Gap Closing Penalty",
            value=DEFAULT_CONFIG["gap_closing_penalty"],
            step=1.0,
            key="gap_closing_penalty",
        )

    config["plot_width"] = DEFAULT_CONFIG["plot_width"]
    config["plot_height"] = DEFAULT_CONFIG["plot_height"]
    config["padding"] = DEFAULT_CONFIG["padding"]

    # Export config button
    st.sidebar.download_button(
        "Export Current Config",
        data=json.dumps(config, indent=4),
        file_name="config.json",
        mime="application/json",
        use_container_width=True,
    )

    run_analysis = st.sidebar.button(
        "Run Analysis", type="primary", use_container_width=True
    )

    st.sidebar.subheader("Data Input")
    uploaded_files = st.sidebar.file_uploader(
        "Upload .tiff files", type=["tif", "tiff"], accept_multiple_files=True
    )

    run_analysis = run_analysis and len(uploaded_files) > 0

    return config, uploaded_files, run_analysis
