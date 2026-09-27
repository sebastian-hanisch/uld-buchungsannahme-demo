"""uldb2_pdf_export.py: PDF baut ohne Fehler und enthält die erwartete Byte-Signatur."""
import numpy as np
import pytest

import uldb2_results as R
from uldb2_dp import dp_value_function, policy_dp
from uldb2_model import make_requests, policy_fcfs, policy_threshold, revenue_of
from uldb2_pdf_export import generate_uldb2_pdf


@pytest.fixture
def sample():
    settings = dict(t=25, cap=2500.0, corr=0.3, threshold=7.0, seed=0)
    rng = np.random.default_rng(settings["seed"])
    requests = make_requests(rng, settings["t"], settings["corr"], (200.0, 2000.0), (2.0, 12.0))
    Vt = dp_value_function(T=settings["t"], capacity_kg=settings["cap"], weight_range=(200.0, 2000.0),
                            price_range=(2.0, 12.0), price_weight_corr=settings["corr"])
    accepted = {
        "fcfs": policy_fcfs(requests, settings["cap"]),
        "threshold": policy_threshold(requests, settings["cap"], settings["threshold"]),
        "dp": policy_dp(requests, settings["cap"], Vt),
    }
    revenue = {k: revenue_of(a, requests) for k, a in accepted.items()}
    n_accepted = {k: sum(a) for k, a in accepted.items()}
    utilization = {k: sum(r.weight_kg for r, ok in zip(requests, a) if ok) / settings["cap"] for k, a in accepted.items()}
    live = dict(requests=requests, accepted=accepted, revenue=revenue, n_accepted=n_accepted, utilization=utilization)
    D = R.load_results()
    cell = R.find_cell(D, settings["t"], settings["cap"], settings["corr"])
    return settings, live, cell


def test_pdf_starts_with_the_pdf_magic_bytes(sample):
    settings, live, cell = sample
    pdf_bytes = generate_uldb2_pdf(settings, live, cell)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 500


def test_pdf_builds_for_an_empty_acceptance_pattern():
    """Randfall: Kapazität 0 -> keine Buchung angenommen, die Anfrageliste bleibt trotzdem vollständig."""
    settings = dict(t=5, cap=0.0, corr=0.0, threshold=7.0, seed=1)
    rng = np.random.default_rng(1)
    requests = make_requests(rng, 5, 0.0, (200.0, 2000.0), (2.0, 12.0))
    accepted = {"fcfs": [False] * 5, "threshold": [False] * 5, "dp": [False] * 5}
    live = dict(requests=requests, accepted=accepted, revenue={"fcfs": 0.0, "threshold": 0.0, "dp": 0.0},
                n_accepted={"fcfs": 0, "threshold": 0, "dp": 0}, utilization={"fcfs": 0.0, "threshold": 0.0, "dp": 0.0})
    D = R.load_results()
    cell = R.find_cell(D, 25, 2500.0, 0.3)
    pdf_bytes = generate_uldb2_pdf(settings, live, cell)
    assert pdf_bytes[:5] == b"%PDF-"
