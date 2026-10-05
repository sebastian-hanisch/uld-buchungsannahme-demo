"""Unabhängiges Orakel für die Bid-Price-DP: (1) die Wertfunktion gegen die LP-Form der Bellman-Gleichung (minimale Lösung von V = E[max(...)], HiGHS) und gegen eine vektorisierte
Neuimplementierung, (2) der erwartete Erlös der DP-Regel über ALLE Anfragefolgen eines Gitters mit Gewichten in 50-kg-Vielfachen ist exakt V[0, c0] (dann ist die Diskretisierung
verlustfrei und die Regel beweisbar optimal), (3) die drei Annahmeregeln gegen eine eigene Neuimplementierung auf Zufallsfolgen mit Gleichständen (Preis exakt auf der Schwelle,
Gewicht exakt gleich der Restkapazität) und die Kapazitätsgrenze."""

import itertools

import numpy as np
import pytest

import uldb2_dp as D
import uldb2_model as M

STEP = D.CAP_STEP


def _scenarios(wr, pr, corr, nw, npb):
    out = []
    for w in np.linspace(wr[0], wr[1], nw):
        frac = (w - wr[0]) / (wr[1] - wr[0])
        for p in np.linspace(pr[0], pr[1], npb):
            out.append((float(w), float(p * (1 - corr * 0.6 * frac) * w), int(round(w / STEP))))
    return out


def _vectorised_v(T, cap, wr, pr, corr, nw=12, npb=8):
    n_cap = int(round(cap / STEP)) + 1
    sc = _scenarios(wr, pr, corr, nw, npb)
    V = np.zeros((T + 1, n_cap))
    for t in range(T - 1, -1, -1):
        nxt, acc = V[t + 1], np.zeros(n_cap)
        for _w, price, ck in sc:
            take = nxt.copy()
            if ck < n_cap:
                shifted = np.full(n_cap, -np.inf)
                shifted[ck:] = price + nxt[: n_cap - ck]
                take = np.maximum(nxt, shifted)
            acc += take
        V[t] = acc / len(sc)
    return V


def _lp_v(T, cap, wr, pr, corr, nw, npb):
    """Bellman als LP: minimiere sum V(t,c) mit V(t,c) = mean_k z_k, z_k >= Annahme- und z_k >= Ablehnungswert; die minimale Lösung ist die Wertfunktion."""
    sp = pytest.importorskip("scipy.sparse")
    from scipy.optimize import linprog
    n_cap = int(round(cap / STEP)) + 1
    sc = _scenarios(wr, pr, corr, nw, npb)
    K = len(sc)

    def zi(t, c, k):
        return (t * n_cap + c) * K + k
    rows = []
    for t in range(T):
        for c in range(n_cap):
            for k, (_w, price, ck) in enumerate(sc):
                for target, add, allowed in ((c, 0.0, True), (c - ck, price, ck <= c)):
                    if not allowed:
                        continue
                    row = {zi(t, c, k): -1.0}
                    if t + 1 < T:
                        for j in range(K):
                            row[zi(t + 1, target, j)] = row.get(zi(t + 1, target, j), 0.0) + 1.0 / K
                    rows.append((row, -add))
    A = sp.lil_matrix((len(rows), T * n_cap * K))
    b = np.zeros(len(rows))
    for r, (row, rhs) in enumerate(rows):
        for j, v in row.items():
            A[r, j] = v
        b[r] = rhs
    res = linprog(np.full(T * n_cap * K, 1.0 / K), A_ub=A.tocsr(), b_ub=b, bounds=(None, None), method="highs")
    assert res.status == 0
    V = np.zeros((T + 1, n_cap))
    V[:T] = res.x.reshape(T, n_cap, K).mean(axis=2)
    return V


@pytest.mark.parametrize("T,cap,wr,pr,corr,nw,npb", [(2, 300.0, (100.0, 250.0), (2.0, 6.0), 0.3, 3, 2), (3, 450.0, (50.0, 400.0), (1.0, 12.0), 0.6, 4, 3),
                                                      (3, 600.0, (200.0, 500.0), (2.0, 12.0), 0.0, 3, 3), (1, 150.0, (100.0, 600.0), (2.0, 6.0), 1.0, 2, 2)])
def test_value_function_equals_the_lp_form_of_the_bellman_equation(T, cap, wr, pr, corr, nw, npb):
    V = D.dp_value_function(T, cap, wr, pr, corr, nw, npb)
    assert np.allclose(V, _lp_v(T, cap, wr, pr, corr, nw, npb), rtol=1e-6, atol=1e-6)
    assert np.allclose(V, _vectorised_v(T, cap, wr, pr, corr, nw, npb), rtol=1e-10, atol=1e-8)


def test_value_function_of_the_demo_cells_equals_a_vectorised_reimplementation():
    for T, cap, corr in ((15, 1500.0, 0.0), (25, 2500.0, 0.3), (40, 2500.0, 0.6)):
        V = D.dp_value_function(T, cap, (200.0, 2000.0), (2.0, 12.0), corr)
        assert np.allclose(V, _vectorised_v(T, cap, (200.0, 2000.0), (2.0, 12.0), corr), rtol=1e-10, atol=1e-8)


@pytest.mark.parametrize("T,nw,npb,cap,corr", [(3, 4, 3, 600.0, 0.0), (4, 3, 3, 500.0, 0.6), (2, 6, 3, 800.0, 0.2)])
def test_expected_revenue_of_the_dp_rule_over_all_grid_sequences_equals_v0(T, nw, npb, cap, corr):
    wr = (200.0, 200.0 + 50.0 * (nw - 1))                                              # Gewichte exakt auf dem 50-kg-Gitter: keine Rundung
    V = D.dp_value_function(T, cap, wr, (2.0, 12.0), corr, nw, npb)
    sc = _scenarios(wr, (2.0, 12.0), corr, nw, npb)
    total = count = 0
    for seq in itertools.product(sc, repeat=T):
        accepted = D.policy_dp([M.Request(w, p) for w, p, _ in seq], cap, V)
        total += sum(p for (_w, p, _c), a in zip(seq, accepted) if a)
        count += 1
    assert total / count == pytest.approx(V[0, int(round(cap / STEP))], rel=1e-9)


def _own_policies(reqs, cap, V):
    def run(rule):
        rem, out = cap, []
        for t, (w, p) in enumerate(reqs):
            ok = w <= rem + 1e-9 and rule(t, w, p, rem)
            out.append(ok)
            rem -= w if ok else 0.0
        return out

    def dp(t, w, p, rem):
        c = min(int(round(rem / STEP)), V.shape[1] - 1)
        return p >= V[t + 1, c] - V[t + 1, max(c - int(round(w / STEP)), 0)] - 1e-9
    return run(lambda *_: True), run(lambda t, w, p, rem: p / w >= 7.0 - 1e-9), run(dp)


def test_the_three_rules_match_an_own_reimplementation_and_never_exceed_the_capacity():
    rng = np.random.default_rng(1)
    for trial in range(150):
        T, cap, corr = int(rng.choice([1, 3, 10, 25])), float(rng.choice([50.0, 500.0, 1500.0, 2500.0])), float(rng.choice([0.0, 0.3, 0.6]))
        V = D.dp_value_function(T, cap, (200.0, 2000.0), (2.0, 12.0), corr, 4, 3)
        reqs = [(float(rng.uniform(200, 2000)), 0.0) for _ in range(T)]
        reqs = [(w, w * float(rng.uniform(2, 12))) for w, _ in reqs]
        if trial % 5 == 0:                                                             # Gleichstände: glatte Gewichte, Preis exakt auf der Schwelle
            reqs = [(float(50 * rng.integers(4, 40)), 0.0) for _ in range(T)]
            reqs = [(w, 7.0 * w) for w, _ in reqs]
        own_fcfs, own_th, own_dp = _own_policies(reqs, cap, V)
        rq = [M.Request(w, p) for w, p in reqs]
        assert M.policy_fcfs(rq, cap) == own_fcfs and M.policy_threshold(rq, cap, 7.0) == own_th and D.policy_dp(rq, cap, V) == own_dp
        for acc in (own_fcfs, own_th, own_dp):
            assert sum(w for (w, _p), a in zip(reqs, acc) if a) <= cap + 1e-6
