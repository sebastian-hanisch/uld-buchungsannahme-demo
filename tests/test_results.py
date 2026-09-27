"""uldb2_results.py: Zell-Zuordnung (AP 0: alle 18 Reglerkombinationen liegen exakt auf einer gemessenen
Zelle), abgeleitete Kennzahlen, Meldungstext."""
import pytest

import uldb2_constants as C
import uldb2_results as R

D = R.load_results()


def test_alle_reglerkombinationen_liegen_auf_einer_gemessenen_zelle():
    """AP 0: die drei Sweep-Regler (T x Kapazität x Korrelation) bilden genau die 18 gemessenen Zellen ab."""
    for t in C.T_OPTIONS:
        for cap in C.CAP_OPTIONS:
            for corr in C.CORR_OPTIONS:
                cell = R.find_cell(D, t, cap, corr)
                assert cell["T"] == t and cell["cap"] == cap and cell["corr"] == corr
    assert len(R.cells(D)) == len(C.T_OPTIONS) * len(C.CAP_OPTIONS) * len(C.CORR_OPTIONS) == 18


def test_find_cell_raises_on_unmeasured_combination():
    with pytest.raises(KeyError):
        R.find_cell(D, 20, 2500.0, 0.3)


def test_time_rows_returns_the_three_restzeit_stages_in_order():
    rows = R.time_rows(D, 2500.0, 0.3)
    assert [r["T"] for r in rows] == list(C.T_OPTIONS)
    assert all(r["cap"] == 2500.0 and r["corr"] == 0.3 for r in rows)


def test_regime_rows_covers_all_18_cells_and_is_not_a_dead_column():
    """Nullspalten-Signal: keine Kennzahl der Regime-Tabelle ist über alle 18 Zellen konstant."""
    rows = R.regime_rows(D)
    assert len(rows) == 18
    for key in ("gap_fcfs_pct", "gap_th_mid_pct", "util_fcfs_mean", "util_dp_mean"):
        values = {r[key] for r in rows}
        assert len(values) > 1, key


def test_judgment_text_mentions_both_gaps_and_the_cell():
    cell = R.find_cell(D, 25, 2500.0, 0.3)
    text = R.judgment_text(cell)
    assert "FCFS" in text and "Preisschwelle" in text and "T = 25" in text


def test_correlation_rows_defaults_match_the_reference_cell():
    rows = R.correlation_rows(D)
    assert [r["corr"] for r in rows] == list(C.CORR_OPTIONS)
    assert all(r["T"] == 25 and r["cap"] == 2500.0 for r in rows)
