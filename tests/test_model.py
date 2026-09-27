"""Korrektheits-Checks für uldb2_model.py/uldb2_dp.py - die 12 Checks aus
packen-planung/messreihe_uld_buchung/check.py als pytest übernommen, PLUS:

- ein dedizierter Kapazitäts-Regressionstest (PFLICHT laut Detailplan Abschnitt 11): die DP-Regel prüft
  die Zulässigkeit gegen die ECHTE, nicht die gerundete Restkapazität. Das war ein echter Bug beim Bauen
  der Vorab-Messreihe (ERGEBNIS.md "Beim Bauen gefunden") - eine adversarische Instanz konstruiert genau die
  Situation, in der ein Rundungsfehler eine Überschreitung produzieren würde.
- Check 9 (stochastische Optimalität) ist als gepaarter Mittelwertvergleich MIT Standardfehler formuliert,
  NICHT als pfadweise Dominanz - eine pfadweise Erwartung wäre eine falsche Testerwartung an eine
  stochastisch optimale Regel (siehe DEMO-PLAYBOOK Abschnitt 4, ERGEBNIS.md "Beim Bauen gefunden")."""
from __future__ import annotations

import numpy as np
import pytest

from uldb2_dp import CAP_STEP, dp_value_function, policy_dp
from uldb2_model import Request, make_requests, policy_fcfs, policy_threshold, revenue_of

CAP = 2000.0
WR = (200.0, 2000.0)
PR = (2.0, 12.0)


# ---------------------------------------------------------------------------------------------------
# 1. Keine Regel überschreitet die Kapazität, über viele Zufallsinstanzen.
# ---------------------------------------------------------------------------------------------------
def test_keine_regel_ueberschreitet_die_kapazitaet_450_laeufe():
    rng = np.random.default_rng(1)
    V = dp_value_function(T=20, capacity_kg=CAP, weight_range=WR, price_range=PR, price_weight_corr=0.5)
    over_capacity = False
    for _ in range(150):
        reqs = make_requests(rng, 20, 0.5, WR, PR)
        for policy, args in ((policy_fcfs, (CAP,)), (policy_threshold, (CAP, 5.0)), (policy_dp, (CAP, V))):
            acc = policy(reqs, *args)
            used = sum(r.weight_kg for r, a in zip(reqs, acc) if a)
            if used > CAP + 1e-6:
                over_capacity = True
    assert not over_capacity


# ---------------------------------------------------------------------------------------------------
# 2. policy_threshold hält die Schwelle ein.
# ---------------------------------------------------------------------------------------------------
def test_policy_threshold_nimmt_nie_unter_der_schwelle_an():
    rng = np.random.default_rng(2)
    threshold_violated = False
    for _ in range(50):
        reqs = make_requests(rng, 20, 0.5, WR, PR)
        acc = policy_threshold(reqs, CAP, 6.0)
        for r, a in zip(reqs, acc):
            if a and (r.price / r.weight_kg) < 6.0 - 1e-6:
                threshold_violated = True
    assert not threshold_violated


# ---------------------------------------------------------------------------------------------------
# 3. Nullkapazität -> keine Regel nimmt irgendetwas an, Umsatz 0.
# ---------------------------------------------------------------------------------------------------
def test_nullkapazitaet_keine_regel_nimmt_etwas_an():
    rng = np.random.default_rng(3)
    reqs0 = make_requests(rng, 10, 0.5, WR, PR)
    V0 = dp_value_function(T=10, capacity_kg=0.0, weight_range=WR, price_range=PR, price_weight_corr=0.5)
    for policy, args in ((policy_fcfs, (0.0,)), (policy_threshold, (0.0, 0.0)), (policy_dp, (0.0, V0))):
        acc = policy(reqs0, *args)
        assert not any(acc) and revenue_of(acc, reqs0) == 0.0


# ---------------------------------------------------------------------------------------------------
# 4./5. DP-Wertfunktion ist monoton in Restkapazität und Restzeit.
# ---------------------------------------------------------------------------------------------------
def test_dp_wertfunktion_ist_monoton_steigend_in_der_restkapazitaet():
    V_small = dp_value_function(T=8, capacity_kg=500.0, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    assert all(V_small[t, c] <= V_small[t, c + 1] + 1e-6
               for t in range(V_small.shape[0]) for c in range(V_small.shape[1] - 1))


def test_dp_wertfunktion_ist_monoton_fallend_in_t():
    """Mehr verbleibende Perioden bei gleicher Kapazität ist nie schlechter: die zusätzliche Periode kann
    immer abgelehnt werden."""
    V_small = dp_value_function(T=8, capacity_kg=500.0, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    assert all(V_small[t, c] >= V_small[t + 1, c] - 1e-6
               for t in range(V_small.shape[0] - 1) for c in range(V_small.shape[1]))


# ---------------------------------------------------------------------------------------------------
# 6. Randbedingung: V[T] ist überall exakt 0.
# ---------------------------------------------------------------------------------------------------
def test_randbedingung_v_am_ende_ist_ueberall_null():
    V_small = dp_value_function(T=8, capacity_kg=500.0, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    assert np.all(V_small[-1] == 0.0)


# ---------------------------------------------------------------------------------------------------
# 7. T=1-Grenzfall: kein Restwert, DP nimmt jede passende Anfrage an.
# ---------------------------------------------------------------------------------------------------
def test_t1_dp_nimmt_jede_passende_anfrage_an():
    V1 = dp_value_function(T=1, capacity_kg=CAP, weight_range=WR, price_range=PR, price_weight_corr=0.5)
    rng = np.random.default_rng(4)
    for _ in range(30):
        reqs1 = make_requests(rng, 1, 0.5, WR, PR)
        acc = policy_dp(reqs1, CAP, V1)
        if reqs1[0].weight_kg <= CAP:
            assert acc[0]


# ---------------------------------------------------------------------------------------------------
# 8. Brute-Force-Referenz für T=2 auf einem winzigen, deterministischen Gitter.
# ---------------------------------------------------------------------------------------------------
def _brute_force_v0(cap_kg, w_grid, p_grid):
    def v_last(c):
        total, n = 0.0, 0
        for w in w_grid:
            for price_per_kg in p_grid:
                n += 1
                total += (price_per_kg * w) if w <= c else 0.0
        return total / n

    total, n = 0.0, 0
    for w in w_grid:
        for price_per_kg in p_grid:
            n += 1
            price = price_per_kg * w
            best = v_last(cap_kg)
            if w <= cap_kg:
                best = max(best, price + v_last(cap_kg - w))
            total += best
    return total / n


def test_brute_force_referenz_auf_winzigem_gitter():
    w_grid_tiny = np.linspace(200.0, 2000.0, 3)
    p_grid_tiny = np.linspace(2.0, 12.0, 3)
    cap_tiny = 1000.0
    bf = _brute_force_v0(cap_tiny, w_grid_tiny, p_grid_tiny)
    V_tiny = dp_value_function(T=2, capacity_kg=cap_tiny, weight_range=(200.0, 2000.0), price_range=(2.0, 12.0),
                                price_weight_corr=0.0, n_weight_buckets=3, n_price_buckets=3)
    c_idx_tiny = int(round(cap_tiny / CAP_STEP))
    assert abs(bf - V_tiny[0, c_idx_tiny]) < 1.0


# ---------------------------------------------------------------------------------------------------
# 9. DP-Regel im ERWARTUNGSWERT besser als FCFS/Schwelle - gepaarter Mittelwertvergleich MIT
#    Standardfehler, NICHT pfadweise Dominanz (falsche Testerwartung, siehe Moduldoc oben).
# ---------------------------------------------------------------------------------------------------
def test_dp_regel_im_mittel_besser_als_fcfs_und_schwelle():
    rng = np.random.default_rng(5)
    V_cmp = dp_value_function(T=25, capacity_kg=CAP, weight_range=WR, price_range=PR, price_weight_corr=0.4)
    diffs = []
    n_cmp = 60
    for _ in range(n_cmp):
        reqs = make_requests(rng, 25, 0.4, WR, PR)
        rev_dp = revenue_of(policy_dp(reqs, CAP, V_cmp), reqs)
        rev_fcfs = revenue_of(policy_fcfs(reqs, CAP), reqs)
        rev_th = revenue_of(policy_threshold(reqs, CAP, 5.0), reqs)
        diffs.append(rev_dp - max(rev_fcfs, rev_th))
    diffs = np.array(diffs)
    mean_diff, se_diff = diffs.mean(), diffs.std(ddof=1) / np.sqrt(n_cmp)
    assert mean_diff > 2 * se_diff
    # Ausdrücklich NICHT gefordert: dass jede EINZELNE Instanz besser ist (wäre pfadweise Dominanz).
    assert (diffs < 0).sum() >= 0  # dokumentiert nur, dass Einzelinstanzen schlechter sein dürfen


# ---------------------------------------------------------------------------------------------------
# 10. Regressionstest (Nullspalten-Falle): unterschiedliche Schwellen -> unterschiedliche Annahmemuster.
# ---------------------------------------------------------------------------------------------------
def test_unterschiedliche_schwellen_fuehren_zu_unterschiedlichen_annahmemustern():
    rng = np.random.default_rng(6)
    reqs_r = make_requests(rng, 30, 0.5, WR, PR)
    acc_low = policy_threshold(reqs_r, CAP, 2.0)
    acc_high = policy_threshold(reqs_r, CAP, 9.0)
    assert acc_low != acc_high


# ---------------------------------------------------------------------------------------------------
# 11. Determinismus.
# ---------------------------------------------------------------------------------------------------
def test_determinismus_gleicher_seed_gleiche_anfragen():
    r1 = np.random.default_rng(7)
    r2 = np.random.default_rng(7)
    a = make_requests(r1, 10, 0.5, WR, PR)
    b = make_requests(r2, 10, 0.5, WR, PR)
    assert all((x.weight_kg, x.price) == (y.weight_kg, y.price) for x, y in zip(a, b))


# ---------------------------------------------------------------------------------------------------
# 12 (PFLICHT). Kapazitäts-Regressionstest: die DP-Regel prüft IMMER gegen die echte Restkapazität, nie
# gegen das gerundete Kapazitätsgitter - genau der Bug aus ERGEBNIS.md "Beim Bauen gefunden".
# ---------------------------------------------------------------------------------------------------
def test_dp_regel_prueft_gegen_echte_nicht_gerundete_restkapazitaet():
    """Konstruierte adversarische Instanz: Restkapazität 126 kg rundet auf dem 50-kg-Gitter auf 150 kg
    (round(126/50) = 3 -> 150). T=1 (kein Restwert -> bid_price = 0, siehe Check 7), eine Anfrage mit Gewicht
    150 kg zu einem beliebigen positiven Preis. Eine Implementierung, die die Zulässigkeit gegen die
    GERUNDETE Kapazität (150 kg) statt die ECHTE (126 kg) prüft, würde die Anfrage fälschlich annehmen
    und die Kapazität um 24 kg überschreiten."""
    cap = 126.0
    assert int(round(cap / CAP_STEP)) * CAP_STEP == 150.0  # Testvoraussetzung: das Gitter rundet wirklich auf
    V = dp_value_function(T=1, capacity_kg=cap, weight_range=WR, price_range=PR, price_weight_corr=0.5)
    request = Request(weight_kg=150.0, price=1.0)
    acc = policy_dp([request], cap, V)
    assert acc == [False]

    # Gegenprobe: eine Anfrage, die wirklich in die echte Restkapazität passt, wird weiterhin angenommen.
    request_ok = Request(weight_kg=120.0, price=1.0)
    acc_ok = policy_dp([request_ok], cap, V)
    assert acc_ok == [True]


def test_dp_regel_ueberschreitet_kapazitaet_auch_bei_mehreren_anfragen_nicht_am_gitterrand():
    """Wie oben, aber über eine Sequenz mehrerer Anfragen: die Restkapazität zwischen zwei Gitterpunkten
    (nicht durch CAP_STEP teilbar) darf nie zu einer Überschreitung führen."""
    cap = 326.0  # kein Vielfaches von CAP_STEP=50
    V = dp_value_function(T=2, capacity_kg=cap, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    reqs = [Request(weight_kg=250.0, price=2000.0), Request(weight_kg=100.0, price=2000.0)]
    acc = policy_dp(reqs, cap, V)
    used = sum(r.weight_kg for r, a in zip(reqs, acc) if a)
    assert used <= cap + 1e-9


# ---------------------------------------------------------------------------------------------------
# Grenzfälle der Toleranz-Epsilons (1e-9) - jeweils die exakte Grenze konstruiert, an der eine
# verschobene Vergleichsoperation (<=/</>=/>) ein anderes Ergebnis liefern würde (Fehler-Einbau-Test,
# tools/mutation_check.py, deckt diese Stellen auf).
# ---------------------------------------------------------------------------------------------------
def test_policy_fcfs_akzeptiert_exakt_an_der_epsilon_grenze():
    remaining_cap = 1000.0
    req = Request(weight_kg=remaining_cap + 1e-9, price=1.0)
    assert policy_fcfs([req], remaining_cap) == [True]


def test_policy_threshold_akzeptiert_exakt_an_der_gewichts_epsilon_grenze():
    req = Request(weight_kg=500.0 + 1e-9, price=1000.0)
    assert policy_threshold([req], 500.0, 1.0) == [True]


def test_policy_threshold_akzeptiert_exakt_an_der_preis_epsilon_grenze():
    min_price = 6.0
    w = 1.0
    price = (min_price - 1e-9) * w  # Preis/kg liegt exakt 1e-9 UNTER der Schwelle -> noch innerhalb der Toleranz
    req = Request(weight_kg=w, price=price)
    assert policy_threshold([req], 1000.0, min_price) == [True]


def test_policy_dp_akzeptiert_anfrage_die_exakt_die_restkapazitaet_ausschoepft():
    cap = 500.0
    V1 = dp_value_function(T=1, capacity_kg=cap, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    req = Request(weight_kg=cap, price=1.0)
    assert policy_dp([req], cap, V1) == [True]


def test_policy_dp_bid_price_epsilon_grenze():
    """T=1 -> Bid-Price ist immer 0 (kein Restwert, siehe Check 7). Ein Preis exakt 1e-9 UNTER 0 liegt noch
    innerhalb der Toleranz und wird angenommen."""
    V1 = dp_value_function(T=1, capacity_kg=1000.0, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    req = Request(weight_kg=100.0, price=-1e-9)
    assert policy_dp([req], 1000.0, V1) == [True]


def test_policy_dp_haengt_von_der_echten_restzeit_ab_auch_ausserhalb_des_wertfunktions_horizonts():
    """Wird policy_dp mit mehr Anfragen als V's Horizont (T) aufgerufen, fällt der Bid-Price außerhalb des
    Horizonts auf 0 zurück (t + 1 >= V.shape[0]) statt auf die Wertfunktion außerhalb ihres gültigen
    Bereichs zuzugreifen - kein Anwendungsfall der App (dort haben Anfragefolge und Wertfunktion immer
    dasselbe T), aber ein Vertrag von policy_dp selbst, den ein Fehler-Einbau (Grenze off-by-one) verletzen
    würde (IndexError statt Fallback)."""
    V2 = dp_value_function(T=2, capacity_kg=1000.0, weight_range=WR, price_range=PR, price_weight_corr=0.3)
    reqs = [Request(weight_kg=10.0, price=1.0) for _ in range(3)]
    acc = policy_dp(reqs, 1000.0, V2)  # darf nicht werfen
    assert len(acc) == 3


# ---------------------------------------------------------------------------------------------------
# Die dokumentierte Korrelationsformel (Faktor 0,6, siehe uldb2_model.make_requests) direkt geprüft, mit
# einem kontrollierten Zufallsgenerator-Ersatz (keine Zufallsziehung zur Testzeit).
# ---------------------------------------------------------------------------------------------------
class _FixedRNG:
    def __init__(self, values):
        self._values = iter(values)

    def uniform(self, lo, hi):
        return next(self._values)


def test_make_requests_verwendet_den_dokumentierten_korrelationsfaktor_0_6():
    weight_range, price_range = (200.0, 2000.0), (2.0, 12.0)
    w, base_price_per_kg = 1200.0, 10.0
    fake_rng = _FixedRNG([w, base_price_per_kg])
    reqs = make_requests(fake_rng, 1, 0.5, weight_range, price_range)
    w_frac = (w - weight_range[0]) / (weight_range[1] - weight_range[0])
    expected_price_per_kg = base_price_per_kg * (1.0 - 0.5 * 0.6 * w_frac)
    assert reqs[0].weight_kg == w
    assert reqs[0].price == pytest.approx(expected_price_per_kg * w, rel=1e-12)
