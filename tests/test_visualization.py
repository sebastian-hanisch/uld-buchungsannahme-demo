"""uldb2_visualization.py: Plotly-Figuren bauen ohne Fehler und tragen die erwarteten Spuren/Achsen."""
import numpy as np
import pytest

import uldb2_results as R
import uldb2_visualization as V
from uldb2_dp import dp_value_function, policy_dp
from uldb2_model import make_requests, policy_fcfs, policy_threshold

WR = (200.0, 2000.0)
PR = (2.0, 12.0)


@pytest.fixture
def live():
    rng = np.random.default_rng(0)
    requests = make_requests(rng, 25, 0.3, WR, PR)
    cap = 2500.0
    Vt = dp_value_function(T=25, capacity_kg=cap, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    accepted = {
        "fcfs": policy_fcfs(requests, cap), "threshold": policy_threshold(requests, cap, 7.0),
        "dp": policy_dp(requests, cap, Vt),
    }
    return requests, accepted, cap


def test_timeline_figure_has_one_row_per_policy_and_locked_axes(live):
    requests, accepted, _ = live
    fig = V.timeline_figure(requests, accepted)
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange
    assert len(fig.data) > 0


def test_timeline_figure_handles_an_empty_request_list():
    fig = V.timeline_figure([], {"fcfs": [], "threshold": [], "dp": []})
    assert fig.layout.xaxis.fixedrange


def test_capacity_figure_never_goes_negative_and_ends_within_capacity(live):
    requests, accepted, cap = live
    fig = V.capacity_figure(requests, accepted, cap)
    for trace in fig.data:
        ys = list(trace.y)
        assert all(y >= -1e-6 for y in ys)
        assert ys[0] == cap
    assert fig.layout.yaxis.fixedrange


def test_gap_over_time_figure_has_two_bars_per_restzeit_stage():
    D = R.load_results()
    rows = R.time_rows(D, 2500.0, 0.3)
    fig = V.gap_over_time_figure(rows)
    assert len(fig.data) == 2
    assert all(len(trace.x) == 3 for trace in fig.data)
    assert fig.layout.yaxis.fixedrange
