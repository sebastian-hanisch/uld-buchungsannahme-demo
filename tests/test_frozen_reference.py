"""Eingefrorene Instanzen (tests/data/uldb2_frozen.json): 4 feste Anfragefolgen (Gewicht/Preis als Zahlen,
keine Zufallsziehung zur Testzeit) über verschiedene Restzeiten/Kapazitäten/Korrelationen/Schwellen, mit
denen alle drei Regeln reproduzierbare Kennzahlen liefern müssen.

Nach DEMO-PLAYBOOK Abschnitt 4 (NumPy-Versionsdrift) hängt kein Test hier von `np.random.default_rng` zur
Testzeit ab: die Gewichte und Preise selbst sind als Zahlen im JSON eingefroren (einmalig mit festen Seeds
erzeugt, siehe tools/gen_frozen_reference.py, und dann fest gespeichert), nur die Regeln selbst (reine
Python-Schleifen plus die DP-Rückwärtsrechnung) laufen bei jedem Testlauf neu."""
from __future__ import annotations

import json
import pathlib

import pytest

from uldb2_dp import dp_value_function, policy_dp
from uldb2_model import Request, policy_fcfs, policy_threshold, revenue_of

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "uldb2_frozen.json").read_text(encoding="utf-8"))
WR = (200.0, 2000.0)
PR = (2.0, 12.0)


def _ids():
    return [f"t{c['t']}-cap{c['cap']:.0f}-corr{c['corr']}-thr{c['threshold']}-seed{c['seed']}" for c in DATA]


@pytest.mark.parametrize("case", DATA, ids=_ids())
def test_frozen_instance_reproduces_measured_metrics(case):
    requests = [Request(weight_kg=w, price=p) for w, p in zip(case["weights"], case["prices"])]

    acc_fcfs = policy_fcfs(requests, case["cap"])
    acc_th = policy_threshold(requests, case["cap"], case["threshold"])
    V = dp_value_function(T=case["t"], capacity_kg=case["cap"], weight_range=WR, price_range=PR,
                           price_weight_corr=case["corr"])
    acc_dp = policy_dp(requests, case["cap"], V)

    for label, acc, exp in (("fcfs", acc_fcfs, case["fcfs"]), ("threshold", acc_th, case["threshold_policy"]),
                             ("dp", acc_dp, case["dp"])):
        assert [bool(a) for a in acc] == exp["accepted"], label
        assert revenue_of(acc, requests) == pytest.approx(exp["revenue"], rel=1e-9, abs=1e-6), label
        assert sum(acc) == exp["n_accepted"], label


def test_the_frozen_set_covers_the_sweep_stages():
    ts = {c["t"] for c in DATA}
    caps = {c["cap"] for c in DATA}
    corrs = {c["corr"] for c in DATA}
    assert ts >= {15, 25, 40}
    assert caps >= {1500.0, 2500.0}
    assert corrs >= {0.0, 0.3, 0.6}
    assert len(DATA) == 4
