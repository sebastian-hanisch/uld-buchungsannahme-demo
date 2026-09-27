"""Buchungsannahme mit Gewichtslimit - Laden und Auswerten der vorgerechneten Messreihe
(data/uldb2_results.json, 18 Zellen x 150 Instanzen, aus packen-planung/messreihe_uld_buchung/sweep_data.json,
bitgleich als data/uldb2_results.json übernommen, siehe tools/sweep.py und tools/check_full.py).

Die drei Regler (Restzeit T, Gewichtslimit, Preis-Gewicht-Korrelation) bilden genau die drei
Sweep-Dimensionen ab (AP 0 bestätigt: alle 18 Kombinationen liegen exakt auf einer gemessenen Zelle, siehe
tests/test_results.py) - `find_cell` ist deshalb ein exakter Treffer, keine Näherung auf die
nächstliegende Zelle. Die Preisschwelle ist dagegen ein reiner Live-Regler (siehe uldb2_constants.py) - die
hier ausgewerteten Zahlen zu Schwellenregeln beziehen sich immer auf die zwei GEMESSENEN Schwellen (Mitte
des Preisbereichs "th_mid" = 7 EUR/kg, Preisuntergrenze "th_low" = 2 EUR/kg), unabhängig vom aktuellen
Reglerstand."""
from __future__ import annotations

import functools
import json
import pathlib

from uldb2_format import fmt_num

DATA_PATH = pathlib.Path(__file__).parent / "data" / "uldb2_results.json"

T_OPTIONS = (15, 25, 40)
CAP_OPTIONS = (1500.0, 2500.0)
CORR_OPTIONS = (0.0, 0.3, 0.6)


@functools.lru_cache(maxsize=1)
def load_results(path: pathlib.Path | None = None) -> dict:
    p = path or DATA_PATH
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def cells(data: dict) -> list[dict]:
    return data["rows"]


def find_cell(data: dict, T: int, cap: float, corr: float) -> dict:
    """Exakter Treffer (AP 0: die Reglerstufen SIND die gemessenen Zellen)."""
    for r in cells(data):
        if r["T"] == T and abs(r["cap"] - cap) < 1e-9 and abs(r["corr"] - corr) < 1e-9:
            return r
    raise KeyError((T, cap, corr))


def time_rows(data: dict, cap: float, corr: float) -> list[dict]:
    """Rückstand über die Restzeit (für die Kerngrafik), festes Gewichtslimit/Korrelation."""
    return [find_cell(data, T, cap, corr) for T in T_OPTIONS]


def regime_rows(data: dict) -> list[dict]:
    """Alle 18 Zellen für die Regime-Tabelle."""
    out = []
    for c in cells(data):
        out.append({
            "T": c["T"], "cap": c["cap"], "corr": c["corr"],
            "gap_fcfs_pct": c["gap_fcfs_pct"], "gap_th_mid_pct": c["gap_th_mid_pct"],
            "gap_th_low_pct": c["gap_th_low_pct"],
            "util_fcfs_mean": c["util_fcfs_mean"], "util_dp_mean": c["util_dp_mean"],
        })
    return out


def fcfs_gap_summary(data: dict) -> dict:
    """Befund 1 (ERGEBNIS.md): FCFS-Rückstand über alle 18 Zellen."""
    gaps = [c["gap_fcfs_pct"] for c in cells(data)]
    return {"mean": sum(gaps) / len(gaps), "min": min(gaps), "max": max(gaps)}


def threshold_mid_gap_summary(data: dict) -> dict:
    """Befund 2: Rückstand der festen Preisschwelle (Mitte des Preisbereichs, 7 EUR/kg)."""
    gaps = [c["gap_th_mid_pct"] for c in cells(data)]
    return {"mean": sum(gaps) / len(gaps), "min": min(gaps), "max": max(gaps)}


def threshold_low_gap_summary(data: dict) -> dict:
    """Befund 3: Rückstand einer zu niedrigen Preisschwelle (Preisuntergrenze, 2 EUR/kg) - praktisch FCFS."""
    gaps = [c["gap_th_low_pct"] for c in cells(data)]
    return {"mean": sum(gaps) / len(gaps), "min": min(gaps), "max": max(gaps)}


def utilization_gap_cell(data: dict, T: int = 25, cap: float = 2500.0, corr: float = 0.3) -> dict:
    """Befund 4: die optimale Regel erreicht mehr Umsatz bei WENIGER Auslastung - Beispielzelle."""
    cell = find_cell(data, T, cap, corr)
    return {
        "util_fcfs": cell["util_fcfs_mean"], "util_dp": cell["util_dp_mean"],
        "rev_fcfs": cell["mean_rev_fcfs"], "rev_dp": cell["mean_rev_dp"],
    }


def correlation_rows(data: dict, T: int = 25, cap: float = 2500.0) -> list[dict]:
    """Befund 5: Korrelation ist ein schwächerer Hebel als die Restzeit - FCFS-Rückstand über die drei
    Korrelationsstufen bei festem T/Kapazität."""
    return [find_cell(data, T, cap, corr) for corr in CORR_OPTIONS]


def judgment_text(cell: dict) -> str:
    """Meldung für die gezeigte Zelle (Kernabschnitt ①): FCFS- und Schwellen-Rückstand gegenüber der
    DP-Regel, bezogen auf die zwei GEMESSENEN Schwellen (siehe Moduldoc oben)."""
    return (f"Bei T = {cell['T']}, {cell['cap']:.0f} kg Gewichtslimit und Korrelation {cell['corr']:g} verliert "
            f"FCFS im Mittel {fmt_num(cell['gap_fcfs_pct'], 1)} % Umsatz gegenüber der DP-Regel, eine feste "
            f"Preisschwelle von 7 EUR/kg nur {fmt_num(cell['gap_th_mid_pct'], 1)} % (150 Instanzen dieser Zelle).")
