import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
import streamlit as st
from app.session import get_aggregated_results

def test_get_aggregated_results_empty():
    # Mock streamlit session state
    st.session_state.results = {}
    combined_df, tracks_summary_df = get_aggregated_results([])
    assert combined_df.empty
    assert tracks_summary_df.empty

def test_get_aggregated_results_with_data():
    # Setup mock data
    mock_results = {
        "file1.tif": {
            "results": {
                "detections": {
                    "frame": [1, 2],
                    "position": [10, 20],
                    "position_refined": [10.1, 20.2],
                    "contrast": [0.5, 0.6],
                    "snr": [5, 6]
                },
                "final_tracks": {"nTracks": 5}
            }
        }
    }
    
    # Mock streamlit session state
    st.session_state.results = mock_results
    
    combined_df, tracks_summary_df = get_aggregated_results(["file1.tif"])
    
    assert len(combined_df) == 2
    assert combined_df.iloc[0]["File"] == "file1.tif"
    assert len(tracks_summary_df) == 1
    assert tracks_summary_df.iloc[0]["Track Count"] == 5
