"""Abnahmekriterien der fünf Presets (Detailplan Abschnitt 7) - jedes einzeln gegen die vorgerechnete
Messreihe (data/uldb2_results.json) prüfbar, damit ein Preset nie eine Geschichte erzählt, die die Zahlen
nicht tragen."""
from __future__ import annotations

import uldb2_constants as C
import uldb2_results as R
from uldb2_format import fmt_num


def _cell_for(name: str, data: dict) -> dict:
    p = C.PRESETS[name]
    return R.find_cell(data, p["t"], p["cap"], p["corr"])


def check_standard(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Standard", data)
    gap_fcfs, gap_th = cell["gap_fcfs_pct"], cell["gap_th_mid_pct"]
    ok = gap_fcfs >= 25.0 and gap_th <= 10.0
    return ok, (f"Rückstand FCFS {fmt_num(gap_fcfs, 1)} % (>= 25 % erwartet), Rückstand feste Schwelle "
                f"{fmt_num(gap_th, 1)} % (<= 10 % erwartet)")


def check_viel_restzeit(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Viel Restzeit", data)
    gap_th = cell["gap_th_mid_pct"]
    ok = gap_th >= 8.0
    return ok, f"Rückstand feste Schwelle {fmt_num(gap_th, 1)} % (>= 8 % erwartet: hier verliert sie am meisten)"


def check_wenig_restzeit(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Wenig Restzeit", data)
    gap_th = cell["gap_th_mid_pct"]
    ok = gap_th <= 5.0
    return ok, f"Rückstand feste Schwelle {fmt_num(gap_th, 1)} % (<= 5 % erwartet: fast so gut wie die optimale Regel)"


def check_zu_niedrige_schwelle(data: dict) -> tuple[bool, str]:
    """Aggregierter Befund über alle 18 Zellen (nicht eine einzelne Zelle): eine Schwelle nahe der
    Preisuntergrenze verhält sich im Mittel praktisch wie FCFS."""
    fcfs = R.fcfs_gap_summary(data)["mean"]
    th_low = R.threshold_low_gap_summary(data)["mean"]
    ok = abs(fcfs - th_low) <= 3.0
    return ok, (f"Mittlerer Rückstand über alle 18 Zellen: FCFS {fmt_num(fcfs, 1)} %, Schwelle 2 EUR/kg "
                f"{fmt_num(th_low, 1)} % (Abstand <= 3 Prozentpunkte erwartet)")


def check_weniger_auslastung_mehr_umsatz(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Weniger Auslastung, mehr Umsatz", data)
    util_fcfs, util_dp = cell["util_fcfs_mean"], cell["util_dp_mean"]
    rev_fcfs, rev_dp = cell["mean_rev_fcfs"], cell["mean_rev_dp"]
    ok = util_dp < util_fcfs and rev_dp > rev_fcfs
    return ok, (f"Auslastung FCFS {fmt_num(100*util_fcfs, 1)} % gegen DP-Regel {fmt_num(100*util_dp, 1)} % "
                f"(DP < FCFS erwartet), Umsatz FCFS {rev_fcfs:.0f} gegen DP-Regel {rev_dp:.0f} (DP > FCFS erwartet)")


CHECKS = {
    "Standard": check_standard,
    "Viel Restzeit": check_viel_restzeit,
    "Wenig Restzeit": check_wenig_restzeit,
    "Zu niedrige Schwelle": check_zu_niedrige_schwelle,
    "Weniger Auslastung, mehr Umsatz": check_weniger_auslastung_mehr_umsatz,
}


def check_all(data: dict) -> dict[str, tuple[bool, str]]:
    return {name: fn(data) for name, fn in CHECKS.items()}
