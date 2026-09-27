"""Reproduktion der Vorab-Messreihe (nicht in CI): FCFS und Schwellenregeln gegen die DP-Regel (Bid-Price),
je Restzeit, Kapazität und Preis-Gewicht-Korrelation. Schreibt data/uldb2_results.json.

Reproduzierbarer Seed je Zelle über zlib.crc32 (nicht Pythons prozess-gesalzenes hash()) - ein erneuter Lauf
liefert bitgleich dieselbe Datei wie packen-planung/messreihe_uld_buchung/sweep_data.json, aus der
data/uldb2_results.json unverändert übernommen wurde (Bau-Gate, siehe tools/check_full.py)."""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uldb2_dp import dp_value_function, policy_dp  # noqa: E402
from uldb2_model import make_requests, policy_fcfs, policy_threshold, revenue_of  # noqa: E402


def cell_seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode("utf-8")) % (2**31)


WR = (200.0, 2000.0)
PR = (2.0, 12.0)
MID_PRICE_PER_KG = (PR[0] + PR[1]) / 2.0  # 7.0 - Schwelle, die ein Disponent ohne DP "aus dem Bauch" wählen würde

T_VALUES = [15, 25, 40]
CAP_VALUES = [1500.0, 2500.0]
CORR_VALUES = [0.0, 0.3, 0.6]
N_INSTANCES = 150


def run_sweep() -> dict:
    t0 = time.time()
    rows = []
    for T in T_VALUES:
        for cap in CAP_VALUES:
            for corr in CORR_VALUES:
                V = dp_value_function(T=T, capacity_kg=cap, weight_range=WR, price_range=PR, price_weight_corr=corr)
                rng = np.random.default_rng(cell_seed(T, cap, corr))
                rev_fcfs, rev_th_mid, rev_th_low, rev_dp = [], [], [], []
                util_fcfs, util_dp = [], []
                for _ in range(N_INSTANCES):
                    reqs = make_requests(rng, T, corr, WR, PR)
                    a_fcfs = policy_fcfs(reqs, cap)
                    a_th_mid = policy_threshold(reqs, cap, MID_PRICE_PER_KG)
                    a_th_low = policy_threshold(reqs, cap, PR[0])
                    a_dp = policy_dp(reqs, cap, V)
                    rev_fcfs.append(revenue_of(a_fcfs, reqs))
                    rev_th_mid.append(revenue_of(a_th_mid, reqs))
                    rev_th_low.append(revenue_of(a_th_low, reqs))
                    rev_dp.append(revenue_of(a_dp, reqs))
                    util_fcfs.append(sum(r.weight_kg for r, a in zip(reqs, a_fcfs) if a) / cap)
                    util_dp.append(sum(r.weight_kg for r, a in zip(reqs, a_dp) if a) / cap)
                rev_fcfs, rev_th_mid, rev_th_low, rev_dp = map(np.array, (rev_fcfs, rev_th_mid, rev_th_low, rev_dp))
                gap_fcfs = 100 * (rev_dp - rev_fcfs) / rev_dp.mean()
                gap_th_mid = 100 * (rev_dp - rev_th_mid) / rev_dp.mean()
                gap_th_low = 100 * (rev_dp - rev_th_low) / rev_dp.mean()
                rows.append(dict(
                    T=T, cap=cap, corr=corr,
                    mean_rev_fcfs=float(rev_fcfs.mean()), mean_rev_th_mid=float(rev_th_mid.mean()),
                    mean_rev_th_low=float(rev_th_low.mean()), mean_rev_dp=float(rev_dp.mean()),
                    gap_fcfs_pct=float(gap_fcfs.mean()), gap_fcfs_se=float(gap_fcfs.std(ddof=1) / np.sqrt(N_INSTANCES)),
                    gap_th_mid_pct=float(gap_th_mid.mean()), gap_th_mid_se=float(gap_th_mid.std(ddof=1) / np.sqrt(N_INSTANCES)),
                    gap_th_low_pct=float(gap_th_low.mean()), gap_th_low_se=float(gap_th_low.std(ddof=1) / np.sqrt(N_INSTANCES)),
                    util_fcfs_mean=float(np.mean(util_fcfs)), util_dp_mean=float(np.mean(util_dp)),
                ))
                print(f"T={T:2d} cap={cap:5.0f} corr={corr}  gap_fcfs={rows[-1]['gap_fcfs_pct']:5.1f}%  "
                      f"gap_th_mid={rows[-1]['gap_th_mid_pct']:5.1f}%  ({time.time()-t0:.0f}s)")

    out = dict(weight_range=list(WR), price_range=list(PR), mid_price_per_kg=MID_PRICE_PER_KG,
               n_instances=N_INSTANCES, rows=rows)
    print(f"\n{len(rows)} Zellen, {time.time()-t0:.0f}s gesamt")
    return out


def main():
    out = run_sweep()
    out_path = ROOT / "data" / "uldb2_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
