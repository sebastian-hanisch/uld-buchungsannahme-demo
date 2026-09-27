"""Jede Zahl aus dem README wird hier gegen data/uldb2_results.json nachgerechnet (DEMO-PLAYBOOK Abschnitt 4:
erst messen, dann Text schreiben - keine Behauptung ohne Test)."""
import pytest

import uldb2_results as R

D = R.load_results()
REF = R.find_cell(D, 25, 2500.0, 0.3)
SHORT = R.find_cell(D, 15, 2500.0, 0.3)
LONG = R.find_cell(D, 40, 2500.0, 0.3)


def test_befund1_fcfs_verliert_viel_umsatz_konsistent_ueber_alle_zellen():
    s = R.fcfs_gap_summary(D)
    assert s["mean"] == pytest.approx(30.39372750338653, rel=1e-9)
    assert s["min"] == pytest.approx(20.13077531174796, rel=1e-9)
    assert s["max"] == pytest.approx(36.97540528840736, rel=1e-9)


def test_befund2_feste_preisschwelle_holt_das_meiste_aber_nicht_alles():
    s = R.threshold_mid_gap_summary(D)
    assert s["mean"] == pytest.approx(6.360443236914212, rel=1e-9)
    assert s["min"] == pytest.approx(2.741391014624129, rel=1e-9)
    assert s["max"] == pytest.approx(14.596956513829573, rel=1e-9)


def test_befund2_schwelle_wird_mit_mehr_restzeit_schwaecher():
    assert SHORT["gap_th_mid_pct"] == pytest.approx(3.4825041661552176, rel=1e-9)
    assert LONG["gap_th_mid_pct"] == pytest.approx(9.300541084606394, rel=1e-9)
    assert SHORT["gap_th_mid_pct"] < LONG["gap_th_mid_pct"]


def test_befund3_niedrige_schwelle_verhaelt_sich_praktisch_wie_fcfs():
    fcfs_mean = R.fcfs_gap_summary(D)["mean"]
    th_low_mean = R.threshold_low_gap_summary(D)["mean"]
    assert th_low_mean == pytest.approx(29.476873722881706, rel=1e-9)
    assert abs(fcfs_mean - th_low_mean) < 1.0


def test_befund4_dp_regel_erreicht_mehr_umsatz_bei_weniger_auslastung():
    ug = R.utilization_gap_cell(D, 25, 2500.0, 0.3)
    assert ug["util_fcfs"] == pytest.approx(0.9526734168145848, rel=1e-9)
    assert ug["util_dp"] == pytest.approx(0.9107738403098121, rel=1e-9)
    assert ug["util_dp"] < ug["util_fcfs"]
    assert ug["rev_dp"] > ug["rev_fcfs"]


def test_befund5_korrelation_ist_ein_schwaecherer_hebel_als_die_restzeit():
    corr_rows = R.correlation_rows(D, 25, 2500.0)
    gaps = [r["gap_fcfs_pct"] for r in corr_rows]
    assert gaps[0] == pytest.approx(28.718707251850343, rel=1e-9)
    assert gaps[1] == pytest.approx(32.12433980376092, rel=1e-9)
    assert gaps[2] == pytest.approx(31.094175868993915, rel=1e-9)
    # Spannweite über die Korrelation ist deutlich kleiner als die Spannweite über die Restzeit (Befund 2).
    corr_span = max(gaps) - min(gaps)
    time_span = LONG["gap_th_mid_pct"] - SHORT["gap_th_mid_pct"]
    assert corr_span < time_span


def test_referenzzelle_stuetzt_den_ein_satz_befund():
    """Basiszelle des Ein-Satz-Befunds (T=25, 2.500 kg, Korrelation 0,3)."""
    assert REF["gap_fcfs_pct"] == pytest.approx(32.12433980376092, rel=1e-9)
    assert REF["gap_th_mid_pct"] == pytest.approx(6.712129400161513, rel=1e-9)


def test_alle_18_zellen_vorhanden():
    assert len(R.cells(D)) == 18
