"""Bid-Price-Kontrolle: DP-Rückwärtsrechnung über ein diskretisiertes Kapazitätsgitter und die daraus
abgeleitete Annahmeregel. Mechanisch aus packen-planung/messreihe_uld_buchung/buchung.py in ein eigenes Modul
übernommen (Logik UNVERÄNDERT, nur die Modulgrenze zu uldb2_model.py neu) - siehe Detailplan Abschnitt 10.

Anders als revenue-management-demo (geschlossene Littlewood-Formel, weil jede Buchung genau eine Einheit
verbraucht) gibt es hier keine feste Einheitengröße - die Littlewood-Formel funktioniert dafür nicht,
die DP-Regel ersetzt sie."""
from __future__ import annotations

import numpy as np

from uldb2_model import Request

CAP_STEP = 50.0  # kg-Auflösung des Kapazitätsgitters für die dynamische Programmierung


def dp_value_function(T: int, capacity_kg: float, weight_range: tuple[float, float],
                       price_range: tuple[float, float], price_weight_corr: float,
                       n_weight_buckets: int = 12, n_price_buckets: int = 8) -> np.ndarray:
    """Bellman-Rückwärtsrechnung V[t][c] = Erwartungswert des optimalen Restgewinns ab Periode t mit
    Restkapazität c (diskretisiert in CAP_STEP-Schritten). Die Anfrageverteilung ist ein festes Gitter aus
    Gewichts- x Preisstufen mit Gleichverteilung je Stufe (bekannte, stationäre Nachfrage - wie bei
    Littlewood in revenue-management-demo, hier nur zweidimensional statt zweiklassig)."""
    n_cap = int(round(capacity_kg / CAP_STEP)) + 1
    w_lo, w_hi = weight_range
    p_lo, p_hi = price_range
    w_grid = np.linspace(w_lo, w_hi, n_weight_buckets)
    p_grid = np.linspace(p_lo, p_hi, n_price_buckets)
    V = np.zeros((T + 1, n_cap))
    for t in range(T - 1, -1, -1):
        for c in range(n_cap):
            cap_kg = c * CAP_STEP
            best_accum = 0.0
            n_combo = 0
            for w in w_grid:
                w_frac = (w - w_lo) / (w_hi - w_lo)
                for base_p in p_grid:
                    price_per_kg = base_p * (1.0 - price_weight_corr * 0.6 * w_frac)
                    price = price_per_kg * w
                    n_combo += 1
                    c_idx = int(round(w / CAP_STEP))
                    if c_idx <= c:
                        gain_accept = price + V[t + 1, c - c_idx]
                        gain_reject = V[t + 1, c]
                        best_accum += max(gain_accept, gain_reject)
                    else:
                        best_accum += V[t + 1, c]
            V[t, c] = best_accum / n_combo
    return V


def policy_dp(requests: list[Request], capacity_kg: float, V: np.ndarray) -> list[bool]:
    """Nimmt eine Anfrage an, wenn ihr Preis den DP-Bid-Price (V[t+1][c] - V[t+1][c - Gewichtsstufe]) übersteigt.

    Die Zulässigkeit wird gegen die ECHTE, kontinuierliche Restkapazität geprüft (nicht gerundet) - sonst
    kann eine Anfrage angenommen werden, die in Wirklichkeit nicht mehr passt (bis zu CAP_STEP/2 Rundungsfehler,
    beim Bauen der Vorab-Messreihe gefunden: 450 Testläufe überschritten die Kapazität). Nur der
    Bid-Price-Vergleich selbst nutzt die diskretisierte Wertfunktion, das ist nur eine Heuristik für DIE
    Entscheidung, keine harte Grenze."""
    n_cap = V.shape[1]
    remaining = capacity_kg
    accepted = []
    for t, r in enumerate(requests):
        if r.weight_kg > remaining + 1e-9:
            accepted.append(False)
            continue
        c = min(int(round(remaining / CAP_STEP)), n_cap - 1)
        c_idx = int(round(r.weight_kg / CAP_STEP))
        c_after = max(c - c_idx, 0)
        bid_price = (V[t + 1, c] - V[t + 1, c_after]) if t + 1 < V.shape[0] else 0.0
        ok = r.price >= bid_price - 1e-9
        accepted.append(ok)
        if ok:
            remaining -= r.weight_kg
    return accepted
