"""Buchungsannahme mit Gewichtslimit: Anfragemodell und die beiden einfachen Regeln (FCFS, feste
Preisschwelle). Mechanisch aus packen-planung/messreihe_uld_buchung/buchung.py in ein eigenes Modul
übernommen (Logik UNVERÄNDERT, nur die Modulgrenze neu) - die DP-Bid-Price-Regel steht in uldb2_dp.py
(eigenes Modul, siehe Detailplan Abschnitt 10).

Anders als revenue-management-demo (zwei Frachtklassen, JEDE Buchung verbraucht genau EINE diskrete
Kapazitätseinheit, geschlossene Littlewood-Formel) verbraucht hier JEDE Buchungsanfrage ein ZUFÄLLIGES
Gewicht aus einem gemeinsamen Gewichtslimit - ein Online-Rucksackproblem (Bid-Price-Kontrolle) statt eines
Klassenschutz-Problems mit Einheitsnachfrage."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Request:
    weight_kg: float
    price: float


def make_requests(rng: np.random.Generator, T: int, price_weight_corr: float,
                   weight_range=(200.0, 2000.0), price_range=(2.0, 12.0)) -> list[Request]:
    """T Anfragen in zufälliger Ankunftsreihenfolge. `price_weight_corr` in [0, 1] steuert, wie stark der
    Preis je kg mit dem Gewicht abnimmt (schwere Sendungen sind typischerweise Massengut mit niedrigerem
    Preis je kg - 0 = Preis je kg unabhängig vom Gewicht, 1 = stark fallend)."""
    reqs = []
    for _ in range(T):
        w = float(rng.uniform(*weight_range))
        base_price_per_kg = float(rng.uniform(*price_range))
        w_frac = (w - weight_range[0]) / (weight_range[1] - weight_range[0])
        price_per_kg = base_price_per_kg * (1.0 - price_weight_corr * 0.6 * w_frac)
        reqs.append(Request(w, price_per_kg * w))
    return reqs


def revenue_of(accepted: list[bool], requests: list[Request]) -> float:
    return sum(r.price for r, a in zip(requests, accepted) if a)


def policy_fcfs(requests: list[Request], capacity_kg: float) -> list[bool]:
    """Erste-Anfrage-zuerst: annehmen, solange das Gewicht noch passt, unabhängig vom Preis."""
    remaining = capacity_kg
    accepted = []
    for r in requests:
        ok = r.weight_kg <= remaining + 1e-9
        accepted.append(ok)
        if ok:
            remaining -= r.weight_kg
    return accepted


def policy_threshold(requests: list[Request], capacity_kg: float, min_price_per_kg: float) -> list[bool]:
    """Myopische Schwellenregel: annehmen, wenn es passt UND der Preis je kg mindestens min_price_per_kg ist -
    kennt weder die Restzeit noch die künftige Nachfrage."""
    remaining = capacity_kg
    accepted = []
    for r in requests:
        ok = r.weight_kg <= remaining + 1e-9 and (r.price / r.weight_kg) >= min_price_per_kg - 1e-9
        accepted.append(ok)
        if ok:
            remaining -= r.weight_kg
    return accepted
