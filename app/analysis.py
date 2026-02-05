import matlab
import numpy as np
import streamlit as st

try:
    import SimPackage
except ImportError:
    SimPackage = None  # type: ignore


@st.cache_resource
def init_matalab():
    if SimPackage is None:
        st.error("SimPackage not found. Please ensure it is installed.")
        return None
    return SimPackage.initialize()


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
