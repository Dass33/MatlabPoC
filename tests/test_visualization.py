from unittest.mock import MagicMock, patch

import numpy as np

from app.visualization import render_image_tab


def test_render_image_tab_no_errors():
    # Mock streamlit
    with (
        patch("streamlit.columns") as mock_cols,
        patch("streamlit.pyplot") as mock_pyplot,
    ):
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock()]

        image = np.zeros((10, 10))
        config = {"plot_width": 5, "plot_height": 5, "padding": 1}

        # Should run without raising exceptions
        render_image_tab(image, config)

        assert mock_cols.called
        assert mock_pyplot.called
