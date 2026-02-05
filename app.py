import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import tifffile
import SimPackage
import matlab
import json
import pandas as pd


st.set_page_config(
    page_title="Data Processing",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "User interface for NSM data processing algorithm"},
)


@st.cache_resource
def init_matalab():
    return SimPackage.initialize()


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
            "Kt (Background Estimation)", value=159.0, step=1.0, key="kt_val"
        )

    with st.sidebar.expander("Denoising"):
        config["space_filter"] = st.selectbox(
            "Space Filter",
            ["jinc", "gaussian", "laplacean_of_gaussian", "none"],
            index=0,
            key="space_filter"
        )
        config["sigma_x"] = st.number_input("Sigma X", value=2.97, step=0.1, key="sigma_x")
        config["time_filter"] = st.selectbox(
            "Time Filter", ["imgaussfilt", "none"], index=0, key="time_filter"
        )
        config["sigma_t"] = st.number_input("Sigma T", value=1.19, step=0.1, key="sigma_t")
        config["non_linear_filter"] = st.selectbox(
            "Non-Linear Filter", ["none", "nlm"], index=0, key="non_linear_filter"
        )

    with st.sidebar.expander("Detection"):
        config["pfa"] = st.number_input(
            "Probability of False Alarm (pfa)", value=1e-5, format="%.e", key="pfa"
        )
        config["local_min_range"] = st.number_input("Local Min Range", value=6, step=1, key="local_min_range")

    with st.sidebar.expander("Feature Extraction"):
        config["refinement_method"] = st.selectbox(
            "Refinement Method", ["centroid", "parabolic", "gaussian"], index=0, key="refinement_method"
        )
        config["fitting_radius"] = st.number_input("Fitting Radius", value=3, step=1, key="fitting_radius")

    with st.sidebar.expander("Linking / Tracking"):
        config["cut_off_distance"] = st.number_input(
            "Cut-off Distance", value=20.0, step=1.0, key="cut_off_distance"
        )
        config["unmatched_penalty"] = st.number_input(
            "Unmatched Penalty", value=15.0, step=1.0, key="unmatched_penalty"
        )
        config["flow_estimate"] = st.number_input("Flow Estimate", value=0.0, step=0.1, key="flow_estimate")
        config["min_track_len"] = st.number_input("Min Track Length", value=40, step=1, key="min_track_len")

        st.caption("Gap Closing")
        config["max_pos_gap"] = st.number_input("Max Positive Gap", value=3, step=1, key="max_pos_gap")
        config["max_neg_gap"] = st.number_input("Max Negative Gap", value=2, step=1, key="max_neg_gap")
        config["gap_closing_dist"] = st.number_input(
            "Gap Closing Dist", value=40.0, step=1.0, key="gap_closing_dist"
        )
        config["gap_closing_penalty"] = st.number_input(
            "Gap Closing Penalty", value=30.0, step=1.0, key="gap_closing_penalty"
        )

    config["plot_width"] = 12
    config["plot_height"] = 8
    config["padding"] = 2

    # Export config button
    st.sidebar.download_button(
        "Export Current Config",
        data=json.dumps(config, indent=4),
        file_name="config.json",
        mime="application/json",
        use_container_width=True
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


def run_matlab_analysis(my_lib, raw_data, config):
    """Executes the MATLAB analyze_image pipeline and returns processed results."""
    input_data = matlab.double(raw_data.astype(float).tolist())

    with st.spinner("Running MATLAB 'analyze_image' pipeline..."):
        detections, denoised_y, contrast_c, final_tracks = my_lib.analyze_image(
            input_data,
            "Kt",
            float(config["kt_val"]),
            "spaceFilter",
            config["space_filter"],
            "sigma_x",
            float(config["sigma_x"]),
            "timeFilter",
            config["time_filter"],
            "sigma_t",
            float(config["sigma_t"]),
            "nonLinearFilter",
            config["non_linear_filter"],
            "pfa",
            float(config["pfa"]),
            "localMinRange",
            int(config["local_min_range"]),
            "positionRefinementMethod",
            config["refinement_method"],
            "fittingRadius",
            int(config["fitting_radius"]),
            "cut_off_distance",
            float(config["cut_off_distance"]),
            "unmatched_penalty_distance",
            float(config["unmatched_penalty"]),
            "flowEstimate",
            float(config["flow_estimate"]),
            "maxPositiveGab",
            float(config["max_pos_gap"]),
            "maxNegativeGab",
            float(config["max_neg_gap"]),
            "gab_closing_cut_off_distance",
            float(config["gap_closing_dist"]),
            "gab_closing_penalty_distance",
            float(config["gap_closing_penalty"]),
            "minTrackLength",
            float(config["min_track_len"]),
            nargout=4,
        )

    # Convert to numpy arrays for visualization
    results = {
        "detections": detections,
        "denoised_y": np.array(denoised_y),
        "contrast_c": np.array(contrast_c),
        "final_tracks": final_tracks,
        "det_frames": np.array(detections["frame"]).flatten() - 1,
        "det_positions": np.array(detections["position"]).flatten() - 1,
        "det_positions_refined": np.array(detections["position_refined"]).flatten() - 1,
    }

    return results


def render_tracks_plot(denoised_y, final_tracks, config):
    """Helper to render the tracks plot."""
    fig, ax = plt.subplots(figsize=(config["plot_width"], config["plot_height"]))
    im = ax.imshow(-denoised_y, aspect="auto", cmap="viridis", origin="lower")

    n_tracks = 0
    if final_tracks:
        try:
            n_tracks = int(final_tracks.get("nTracks", 0))

            if n_tracks > 0:
                frames_data = final_tracks["frames"]
                positions_data = final_tracks["positions_refined"]

                # Handle single track edge case
                if n_tracks == 1:
                    if not isinstance(frames_data, list):
                        frames_data = [frames_data]
                        positions_data = [positions_data]

                for i in range(n_tracks):
                    t_pos = np.array(positions_data[i]).flatten() - 1
                    t_frame = np.array(frames_data[i]).flatten() - 1
                    ax.plot(t_pos, t_frame, "-", linewidth=1, alpha=0.9)

        except Exception as e:
            st.error(f"Error parsing tracks: {e}")
            st.write("Debug - final_tracks keys:", final_tracks.keys())

    plt.colorbar(im, ax=ax)
    ax.set_title(f"Tracks (Count: {n_tracks})")

    # Apply horizontal padding using columns
    if config["padding"] > 0:
        _, col, _ = st.columns([config["padding"], 10, config["padding"]])
        with col:
            st.pyplot(fig, use_container_width=True)
    else:
        st.pyplot(fig, use_container_width=True)


def render_image_tab(
    image, config, points_x=None, points_y=None, label=None, color="red"
):
    """Helper to render an image tab with optional scatter overlay."""
    fig, ax = plt.subplots(figsize=(config["plot_width"], config["plot_height"]))
    im = ax.imshow(image, aspect="auto", cmap="viridis", origin="lower")

    if points_x is not None and points_y is not None:
        ax.scatter(points_x, points_y, color=color, s=10, label=label)
        ax.legend()

    plt.colorbar(im, ax=ax)

    # Apply horizontal padding using columns
    if config["padding"] > 0:
        _, col, _ = st.columns([config["padding"], 10, config["padding"]])
        with col:
            st.pyplot(fig, use_container_width=True)
    else:
        st.pyplot(fig, use_container_width=True)


def display_results(raw_data, results, config):
    """Renders the results tabs and details table."""
    det_frames = results["det_frames"]
    det_positions = results["det_positions"]
    det_positions_refined = results["det_positions_refined"]
    detections = results["detections"]
    denoised_y = results["denoised_y"]
    contrast_c = results["contrast_c"]
    final_tracks = results["final_tracks"]

    tabs = st.tabs(["Tracks", "Denoised (Y)", "Contrast (C)", "Raw (R)"])

    with tabs[0]:
        render_tracks_plot(denoised_y, final_tracks, config)

    with tabs[1]:
        render_image_tab(
            -denoised_y,
            config,
            det_positions,
            det_frames,
            label="Detections",
            color="red",
        )

    with tabs[2]:
        render_image_tab(
            -contrast_c,
            config,
            det_positions_refined,
            det_frames,
            label="Refined",
            color="white",
        )

    with tabs[3]:
        fig, ax = plt.subplots(figsize=(config["plot_width"], config["plot_height"]))
        im = ax.imshow(raw_data, aspect="auto", cmap="gray", origin="lower")
        plt.colorbar(im, ax=ax)

        # Apply horizontal padding using columns
        if config["padding"] > 0:
            _, col, _ = st.columns([config["padding"], 10, config["padding"]])
            with col:
                st.pyplot(fig, use_container_width=True)
        else:
            st.pyplot(fig, use_container_width=True)

    if len(det_frames) > 0:
        with st.expander("Detection Details"):
            df = pd.DataFrame({
                "Frame": det_frames + 1,
                "Position": det_positions + 1,
                "Position Refined": det_positions_refined + 1,
                "Contrast": np.array(detections["contrast"]).flatten(),
                "SNR": np.array(detections["snr"]).flatten(),
            })
            st.dataframe(df)


def run():
    config, uploaded_files, run_analysis = render_sidebar_config()

    if "results" not in st.session_state:
        st.session_state.results = {}

    with st.spinner("Loading MATLAB Runtime..."):
        my_lib = init_matalab()

    if uploaded_files:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Clear Results", use_container_width=True):
                st.session_state.results = {}
                st.rerun()

        if run_analysis:
            # Identify files that need processing
            files_to_process = [
                f for f in uploaded_files if f.name not in st.session_state.results
            ]

            if not files_to_process:
                st.sidebar.info("All files already processed with current session.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, uploaded_file in enumerate(files_to_process):
                    status_text.text(
                        f"Processing {uploaded_file.name} ({i + 1}/{len(files_to_process)})..."
                    )
                    try:
                        raw_data = tifffile.imread(uploaded_file)
                        results = run_matlab_analysis(my_lib, raw_data, config)
                        st.session_state.results[uploaded_file.name] = {
                            "raw_data": raw_data,
                            "results": results,
                        }
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                        st.exception(e)
                    progress_bar.progress((i + 1) / len(files_to_process))

                status_text.text("Processing complete!")
                st.success(f"Processed {len(files_to_process)} new files.")

        # Filter session state to only include currently uploaded files
        current_file_names = {f.name for f in uploaded_files}
        available_results = [
            name
            for name in st.session_state.results.keys()
            if name in current_file_names
        ]

        if available_results:
            selected_file = st.selectbox(
                "Select file to view detailed results",
                options=available_results,
            )
            if selected_file:
                data = st.session_state.results[selected_file]
                display_results(data["raw_data"], data["results"], config)

            # Aggregated Results Section
            with st.expander("Aggregated Results", expanded=False):
                all_detections = []
                all_tracks_summary = []
                for name in available_results:
                    res = st.session_state.results[name]["results"]

                    # Detections
                    det = res["detections"]
                    df = pd.DataFrame({
                        "File": name,
                        "Frame": np.array(det["frame"]).flatten(),
                        "Position": np.array(det["position"]).flatten(),
                        "Position Refined": np.array(det["position_refined"]).flatten(),
                        "Contrast": np.array(det["contrast"]).flatten(),
                        "SNR": np.array(det["snr"]).flatten(),
                    })
                    all_detections.append(df)

                    # Tracks Summary
                    ft = res["final_tracks"]
                    n_tracks = int(ft.get("nTracks", 0) if isinstance(ft, dict) else 0)
                    all_tracks_summary.append({
                        "File": name,
                        "Track Count": n_tracks,
                    })

                if all_tracks_summary:
                    st.write("### Tracks Summary")
                    st.dataframe(
                        pd.DataFrame(all_tracks_summary), use_container_width=True
                    )

                if all_detections:
                    combined_df = pd.concat(all_detections, ignore_index=True)
                    st.write(f"### Detections (Total: {len(combined_df)})")
                    st.dataframe(
                        combined_df.head(100), use_container_width=True
                    )  # Show preview

                    col_csv, col_json = st.columns(2)
                    with col_csv:
                        csv = combined_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download CSV",
                            csv,
                            "all_detections.csv",
                            "text/csv",
                            key="download-csv",
                            use_container_width=True,
                        )

                    with col_json:
                        # Prepare a serializable version of all results for JSON
                        json_results = {}
                        for name in available_results:
                            res = st.session_state.results[name]["results"]
                            # Convert detections to dict and listify numpy arrays
                            det = {
                                k: np.array(v).tolist()
                                for k, v in res["detections"].items()
                            }
                            # Final tracks summary
                            ft = res["final_tracks"]
                            summary = {
                                "nTracks": int(
                                    ft.get("nTracks", 0) if isinstance(ft, dict) else 0
                                )
                            }
                            json_results[name] = {
                                "detections": det,
                                "summary": summary,
                            }

                        st.download_button(
                            "Download JSON Results",
                            json.dumps(json_results, indent=4),
                            "all_results.json",
                            "application/json",
                            key="download-json",
                            use_container_width=True,
                        )
        elif not run_analysis:
            st.info("Click 'Run Analysis' to process the uploaded files.")
    else:
        st.info("Please upload .tiff files to begin.")


if __name__ == "__main__":
    run()
