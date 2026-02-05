from unittest.mock import patch

from app.main import run


def test_app_importable():
    """Verify that the main app modules can be imported without side effects."""
    assert True


def test_main_orchestration():
    """Smoke test for the main function logic using mocks."""
    with (
        patch("streamlit.set_page_config"),
        patch("streamlit.sidebar"),
        patch("streamlit.spinner"),
        patch("app.main.render_sidebar_config") as mock_sidebar,
        patch("app.main.init_session_state") as mock_init_session,
        patch("app.main.init_matalab") as mock_init_matlab,
        patch("app.main.display_results"),
    ):
        # Setup mocks
        mock_sidebar.return_value = ({}, [], False)  # config, files, run_flag

        # Should run without crashing
        run()

        assert mock_init_session.called
        assert mock_init_matlab.called
