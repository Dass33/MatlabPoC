import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


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

        if config["padding"] > 0:
            _, col, _ = st.columns([config["padding"], 10, config["padding"]])
            with col:
                st.pyplot(fig, use_container_width=True)
        else:
            st.pyplot(fig, use_container_width=True)

    if len(det_frames) > 0:
        with st.expander("Detection Details"):
            df = pd.DataFrame(
                {
                    "Frame": det_frames + 1,
                    "Position": det_positions + 1,
                    "Position Refined": det_positions_refined + 1,
                    "Contrast": np.array(detections["contrast"]).flatten(),
                    "SNR": np.array(detections["snr"]).flatten(),
                }
            )
            st.dataframe(df)
