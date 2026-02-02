import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import tifffile
import SimPackage
import matlab
import pandas as pd

# Set page config
st.set_page_config(page_title="NSM Data Processing", layout="wide")

@st.cache_resource
def load_matlab_lib():
    """Initialize the MATLAB Runtime once."""
    print("Initializing MATLAB Runtime...")
    return SimPackage.initialize()

def run_app():
    st.title("NSM Data Processing")
    st.markdown("This is user interface for NSM Data Processing Matlab algoritm.")

    # Sidebar for parameters
    st.sidebar.header("Configuration")
    
    with st.sidebar.expander("Preprocessing", expanded=True):
        kt_val = st.number_input("Kt (Background Estimation)", value=159.0, step=1.0)
    
    with st.sidebar.expander("Denoising"):
        space_filter = st.selectbox("Space Filter", ["jinc", "gaussian", "laplacean_of_gaussian", "none"], index=0)
        sigma_x = st.number_input("Sigma X", value=2.97, step=0.1)
        time_filter = st.selectbox("Time Filter", ["imgaussfilt", "none"], index=0)
        sigma_t = st.number_input("Sigma T", value=1.19, step=0.1)
        non_linear_filter = st.selectbox("Non-Linear Filter", ["none", "nlm"], index=0)

    with st.sidebar.expander("Detection"):
        pfa = st.number_input("Probability of False Alarm (pfa)", value=1e-5, format="%.e")
        local_min_range = st.number_input("Local Min Range", value=6, step=1)

    with st.sidebar.expander("Feature Extraction"):
        refinement_method = st.selectbox("Refinement Method", ["centroid", "parabolic", "gaussian"], index=0)
        fitting_radius = st.number_input("Fitting Radius", value=3, step=1)

    with st.sidebar.expander("Linking / Tracking"):
        cut_off_distance = st.number_input("Cut-off Distance", value=20.0, step=1.0)
        unmatched_penalty = st.number_input("Unmatched Penalty", value=15.0, step=1.0)
        flow_estimate = st.number_input("Flow Estimate", value=0.0, step=0.1)
        min_track_len = st.number_input("Min Track Length", value=40, step=1)
        
        st.caption("Gap Closing")
        max_pos_gap = st.number_input("Max Positive Gap", value=3, step=1)
        max_neg_gap = st.number_input("Max Negative Gap", value=2, step=1)
        gap_closing_dist = st.number_input("Gap Closing Dist", value=40.0, step=1.0)
        gap_closing_penalty = st.number_input("Gap Closing Penalty", value=30.0, step=1.0)

    with st.sidebar.expander("Image Manipulation"):
        do_flip_ud = st.checkbox("Flip Vertical (Upside Down)", value=False)
        do_flip_lr = st.checkbox("Flip Horizontal (Left-Right)", value=False)

    with st.sidebar.expander("Visualization Settings"):
        track_color_mode = st.radio("Track Color Mode", ["Single", "Multiple (Cycle)"], index=1)
        if track_color_mode == "Single":
            track_color = st.color_picker("Track Color", "#FF0000")
        else:
            track_palette = st.selectbox("Color Palette", ["hsv", "rainbow", "autumn", "spring", "cool", "Set1"], index=0)
            st.caption("Palettes like 'autumn' or 'spring' avoid blue tones.")

    st.sidebar.subheader("Data Input")
    uploaded_file = st.sidebar.file_uploader("Upload .tiff file", type=['tif', 'tiff'])

    # Initialize Library
    with st.spinner("Loading MATLAB Runtime..."):
        my_lib = load_matlab_lib()

    if uploaded_file is not None:
        try:
            # Load Data
            raw_data = tifffile.imread(uploaded_file)
            
            # Apply Image Manipulation
            if do_flip_ud:
                raw_data = np.flipud(raw_data)
            if do_flip_lr:
                raw_data = np.fliplr(raw_data)
            
            st.sidebar.success(f"Loaded file: {uploaded_file.name}")

            if st.button("Run Analysis", type="primary"):
                # Convert to MATLAB type
                input_data = matlab.double(raw_data.astype(float).tolist())
                
                with st.spinner("Running MATLAB 'analyze_image' pipeline..."):
                    # Call MATLAB function with all parameters
                    # Returns [Detections, Y, C, FinalTracks]
                    detections, denoised_y, contrast_c, final_tracks = my_lib.analyze_image(
                        input_data, 
                        'Kt', float(kt_val),
                        'spaceFilter', space_filter,
                        'sigma_x', float(sigma_x),
                        'timeFilter', time_filter,
                        'sigma_t', float(sigma_t),
                        'nonLinearFilter', non_linear_filter,
                        'pfa', float(pfa),
                        'localMinRange', int(local_min_range),
                        'positionRefinementMethod', refinement_method,
                        'fittingRadius', int(fitting_radius),
                        'cut_off_distance', float(cut_off_distance),
                        'unmatched_penalty_distance', float(unmatched_penalty),
                        'flowEstimate', float(flow_estimate),
                        'maxPositiveGab', float(max_pos_gap),
                        'maxNegativeGab', float(max_neg_gap),
                        'gab_closing_cut_off_distance', float(gap_closing_dist),
                        'gab_closing_penalty_distance', float(gap_closing_penalty),
                        'minTrackLength', float(min_track_len),
                        nargout=4
                    )
                    
                    # Convert back to numpy
                    denoised_y = np.array(denoised_y)
                    contrast_c = np.array(contrast_c)
                    
                    # Extract detections for plotting
                    # MATLAB uses 1-based indexing, Python uses 0-based. Subtract 1 for alignment.
                    det_frames = np.array(detections['frame']).flatten() - 1
                    det_positions = np.array(detections['position']).flatten() - 1
                    det_positions_refined = np.array(detections['position_refined']).flatten() - 1

                st.success(f"Processing Complete! Found {len(det_frames)} detections.")

                # Visualization
                # Use origin='lower' to match MATLAB's surf/imagesc behavior where appropriate
                # (MATLAB showKymograph uses surf which puts row 1 at bottom? Verified: yes, standard axes)
                
                tabs = st.tabs(["Tracks", "Denoised (Y)", "Contrast (C)", "Raw (R)"])
                
                with tabs[0]:
                    st.subheader("Final Tracks")
                    fig0, ax0 = plt.subplots(figsize=(10, 6))
                    # Plot image with origin='lower' so Row 0 is at bottom
                    im0 = ax0.imshow(-denoised_y, aspect='auto', cmap='viridis', origin='lower')
                    
                    # Plot Tracks
                    n_tracks = 0
                    if final_tracks:
                        # MATLAB struct becomes dict. 
                        # Check nTracks to see if we have data.
                        # Note: MATLAB fields might be returned as lists or single values depending on size.
                        try:
                            n_tracks = int(final_tracks.get('nTracks', 0))
                            
                            if n_tracks > 0:
                                # Access cell arrays. In Python, these usually become lists.
                                # If nTracks=1, MATLAB engine might return the single item directly, not in a list.
                                
                                frames_data = final_tracks['frames']
                                positions_data = final_tracks['positions_refined'] # Use refined positions like showKymograph

                                # If n_tracks > 1, these should be lists. 
                                # If n_tracks == 1, they might be the array itself.
                                if n_tracks == 1:
                                    # If it's not a list, wrap it.
                                    # Note: A single numpy array is not a list.
                                    if not isinstance(frames_data, list):
                                        frames_data = [frames_data]
                                        positions_data = [positions_data]
                                
                                # Prepare colors if in cycle mode
                                if track_color_mode == "Multiple (Cycle)":
                                    cmap = plt.get_cmap(track_palette)
                                    colors = cmap(np.linspace(0, 1, n_tracks))
                                
                                for i in range(n_tracks):
                                    # Get coordinate arrays for this track
                                    # MATLAB uses 1-based indexing. Subtract 1 for Python.
                                    t_pos = np.array(positions_data[i]).flatten() - 1
                                    t_frame = np.array(frames_data[i]).flatten() - 1
                                    
                                    color = track_color if track_color_mode == "Single" else colors[i]
                                    ax0.plot(t_pos, t_frame, '-', color=color, linewidth=1, alpha=0.9)

                        except Exception as e:
                            st.error(f"Error parsing tracks: {e}")
                            st.write("Debug - final_tracks keys:", final_tracks.keys())
                    
                    plt.colorbar(im0, ax=ax0)
                    ax0.set_title(f"Tracks (Count: {n_tracks})")
                    st.pyplot(fig0)

                with tabs[1]:
                    st.subheader("Denoised Image (Y) with Detections")
                    fig1, ax1 = plt.subplots(figsize=(10, 6))
                    im1 = ax1.imshow(-denoised_y, aspect='auto', cmap='viridis', origin='lower')
                    ax1.scatter(det_positions, det_frames, color='red', s=10, label='Detections')
                    plt.colorbar(im1, ax=ax1)
                    ax1.set_title("Denoised (-Y)")
                    ax1.legend()
                    st.pyplot(fig1)

                with tabs[2]:
                    st.subheader("Contrast Image (C) with Refined Positions")
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    im2 = ax2.imshow(-contrast_c, aspect='auto', cmap='viridis', origin='lower')
                    ax2.scatter(det_positions_refined, det_frames, color='white', s=10, label='Refined')
                    plt.colorbar(im2, ax=ax2)
                    ax2.set_title("Contrast (-C)")
                    ax2.legend()
                    st.pyplot(fig2)

                with tabs[3]:
                    st.subheader("Raw Data (R)")
                    fig3, ax3 = plt.subplots(figsize=(10, 6))
                    im3 = ax3.imshow(raw_data, aspect='auto', cmap='gray', origin='lower')
                    plt.colorbar(im3, ax=ax3)
                    st.pyplot(fig3)
                
                # Show detections table
                if len(det_frames) > 0:
                    with st.expander("Detection Details"):
                        df = pd.DataFrame({
                            'Frame': det_frames + 1,
                            'Position': det_positions + 1,
                            'Position Refined': det_positions_refined + 1,
                            'Contrast': np.array(detections['contrast']).flatten(),
                            'SNR': np.array(detections['snr']).flatten()
                        })
                        st.dataframe(df)
        
        except Exception as e:
            st.error(f"Error reading file or processing: {e}")
            st.write("Full Error Details:")
            st.exception(e)
    else:
        st.info("Please upload a .tiff file to begin.")

if __name__ == "__main__":
    run_app()
