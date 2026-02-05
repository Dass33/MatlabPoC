from app.config import DEFAULT_CONFIG


def test_default_config_keys():
    expected_keys = [
        "kt_val",
        "space_filter",
        "sigma_x",
        "time_filter",
        "sigma_t",
        "non_linear_filter",
        "pfa",
        "local_min_range",
        "refinement_method",
        "fitting_radius",
        "cut_off_distance",
        "unmatched_penalty",
        "flow_estimate",
        "min_track_len",
        "max_pos_gap",
        "max_neg_gap",
        "gap_closing_dist",
        "gap_closing_penalty",
    ]
    for key in expected_keys:
        assert key in DEFAULT_CONFIG
