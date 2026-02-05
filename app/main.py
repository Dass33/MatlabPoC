import json
import sys
import os

# Setup paths
current_file = os.path.abspath(__file__)
app_dir = os.path.dirname(current_file)
project_root = os.path.dirname(app_dir)
sim_package_path = os.path.join(project_root, 'SimPackage')

# Add paths to sys.path
# sim_package_path must be before project_root to avoid namespace package conflict
if sim_package_path not in sys.path:
    sys.path.insert(0, sim_package_path)
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import tifffile

from app.analysis import init_matlab, run_matlab_analysis
from app.config import render_sidebar_config
from app.session import (
    clear_results,
    get_aggregated_results,
    init_session_state,
    prepare_json_export,
)
from app.visualization import display_results

st.set_page_config(
    page_title="Data Processing",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "User interface for NSM data processing algorithm"},
)


def run():
    # 1. Setup
    init_session_state()
    config, uploaded_files, run_analysis = render_sidebar_config()

    with st.spinner("Loading MATLAB Runtime..."):
        my_lib = init_matlab()

    if not uploaded_files:
        st.info("Please upload .tiff files to begin.")
        return

    # 2. Sidebar Actions
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Clear Results", use_container_width=True):
            clear_results()

    # 3. Processing
    if run_analysis and my_lib:
        files_to_process = [
            f for f in uploaded_files if f.name not in st.session_state.results
        ]

        if not files_to_process:
            st.sidebar.info("All files already processed.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, uploaded_file in enumerate(files_to_process):
                status_text.text(f"Processing {uploaded_file.name}...")
                try:
                    raw_data = tifffile.imread(uploaded_file)
                    results = run_matlab_analysis(my_lib, raw_data, config)
                    if results:
                        st.session_state.results[uploaded_file.name] = {
                            "raw_data": raw_data,
                            "results": results,
                        }
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")
                progress_bar.progress((i + 1) / len(files_to_process))

            status_text.text("Processing complete!")
            st.success(f"Processed {len(files_to_process)} new files.")

    # 4. Results Display
    current_file_names = {f.name for f in uploaded_files}
    available_results = [
        name for name in st.session_state.results.keys() if name in current_file_names
    ]

    if available_results:
        selected_file = st.selectbox(
            "Select file to view detailed results",
            options=available_results,
        )
        if selected_file:
            data = st.session_state.results[selected_file]
            display_results(data["raw_data"], data["results"], config)

        # 5. Aggregated Results
        st.divider()
        with st.expander("Aggregated Results", expanded=False):
            combined_df, tracks_summary_df = get_aggregated_results(available_results)

            if not tracks_summary_df.empty:
                st.write("### Tracks Summary")
                st.dataframe(tracks_summary_df, use_container_width=True)

            if not combined_df.empty:
                st.write(f"### Detections (Total: {len(combined_df)})")
                st.dataframe(combined_df.head(100), use_container_width=True)

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
                    json_data = prepare_json_export(available_results)
                    st.download_button(
                        "Download JSON Results",
                        json.dumps(json_data, indent=4),
                        "all_results.json",
                        "application/json",
                        key="download-json",
                        use_container_width=True,
                    )
    elif not run_analysis:
        st.info("Click 'Run Analysis' to process the uploaded files.")


if __name__ == "__main__":
    run()
