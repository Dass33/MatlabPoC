import numpy as np
import pandas as pd
import streamlit as st


def init_session_state():
    if "results" not in st.session_state:
        st.session_state.results = {}


def clear_results():
    st.session_state.results = {}
    st.rerun()


def get_aggregated_results(available_results):
    """Combines detections and track counts from multiple files."""
    all_detections = []
    all_tracks_summary = []

    for name in available_results:
        res = st.session_state.results[name]["results"]

        # Detections
        det = res["detections"]
        df = pd.DataFrame(
            {
                "File": name,
                "Frame": np.array(det["frame"]).flatten(),
                "Position": np.array(det["position"]).flatten(),
                "Position Refined": np.array(det["position_refined"]).flatten(),
                "Contrast": np.array(det["contrast"]).flatten(),
                "SNR": np.array(det["snr"]).flatten(),
            }
        )
        all_detections.append(df)

        # Tracks Summary
        ft = res["final_tracks"]
        n_tracks = int(ft.get("nTracks", 0) if isinstance(ft, dict) else 0)
        all_tracks_summary.append(
            {
                "File": name,
                "Track Count": n_tracks,
            }
        )

    combined_df = (
        pd.concat(all_detections, ignore_index=True)
        if all_detections
        else pd.DataFrame()
    )
    tracks_summary_df = (
        pd.DataFrame(all_tracks_summary) if all_tracks_summary else pd.DataFrame()
    )

    return combined_df, tracks_summary_df


def prepare_json_export(available_results):
    """Prepares a serializable dictionary of all results."""
    json_results = {}
    for name in available_results:
        res = st.session_state.results[name]["results"]
        det = {k: np.array(v).tolist() for k, v in res["detections"].items()}
        ft = res["final_tracks"]
        summary = {"nTracks": int(ft.get("nTracks", 0) if isinstance(ft, dict) else 0)}
        json_results[name] = {
            "detections": det,
            "summary": summary,
        }
    return json_results
