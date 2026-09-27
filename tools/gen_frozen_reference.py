"""Erzeugt tests/data/uldb2_frozen.json einmalig: 4 feste Anfragefolgen (Gewicht/Preis als Zahlen, über die
Sweep-Stufen T/Kapazität/Korrelation verteilt, mit unterschiedlichen Preisschwellen) samt den mit dem
AKTUELLEN Code berechneten Annahme-Entscheidungen/Umsätzen aller drei Regeln. NICHT Teil der CI und NICHT
bei jedem Testlauf ausgeführt - die eingefrorene Datei ist die Referenz, dieses Skript nur ihr Ursprung
(erneut ausführen nur nach einer bewussten Modelländerung, dann die neue Datei manuell prüfen)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from uldb2_dp import dp_value_function, policy_dp  # noqa: E402
from uldb2_model import make_requests, policy_fcfs, policy_threshold, revenue_of  # noqa: E402

WR = (200.0, 2000.0)
PR = (2.0, 12.0)

CASES_IN = [
    dict(t=15, cap=1500.0, corr=0.0, threshold=7.0, seed=5),
    dict(t=25, cap=2500.0, corr=0.3, threshold=7.0, seed=7),
    dict(t=40, cap=2500.0, corr=0.6, threshold=2.0, seed=3),
    dict(t=25, cap=1500.0, corr=0.3, threshold=9.5, seed=9),
]


def _bools(acc):
    return [bool(x) for x in acc]


def main():
    out = []
    for c in CASES_IN:
        rng = np.random.default_rng(c["seed"])
        reqs = make_requests(rng, c["t"], c["corr"], WR, PR)
        weights = [r.weight_kg for r in reqs]
        prices = [r.price for r in reqs]

        V = dp_value_function(T=c["t"], capacity_kg=c["cap"], weight_range=WR, price_range=PR,
                               price_weight_corr=c["corr"])
        acc_fcfs = policy_fcfs(reqs, c["cap"])
        acc_th = policy_threshold(reqs, c["cap"], c["threshold"])
        acc_dp = policy_dp(reqs, c["cap"], V)

        out.append(dict(
            t=c["t"], cap=c["cap"], corr=c["corr"], threshold=c["threshold"], seed=c["seed"],
            weights=weights, prices=prices,
            fcfs=dict(accepted=_bools(acc_fcfs), revenue=revenue_of(acc_fcfs, reqs), n_accepted=int(sum(acc_fcfs))),
            threshold_policy=dict(accepted=_bools(acc_th), revenue=revenue_of(acc_th, reqs), n_accepted=int(sum(acc_th))),
            dp=dict(accepted=_bools(acc_dp), revenue=revenue_of(acc_dp, reqs), n_accepted=int(sum(acc_dp))),
        ))

    out_path = ROOT / "tests" / "data" / "uldb2_frozen.json"
    out_path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out_path, len(out), "cases")
    for c in out:
        print(c["t"], c["cap"], c["corr"], c["threshold"], "fcfs_rev", c["fcfs"]["revenue"], "dp_rev", c["dp"]["revenue"])


if __name__ == "__main__":
    main()
