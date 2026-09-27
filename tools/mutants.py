"""Handverlesene Mutantenliste für die beiden Kernmodule (uldb2_model.py, uldb2_dp.py): jede alte Stelle
kommt im jeweiligen Modul genau einmal vor. Wie bei uld-beladeplan-demo (siehe dortiges tools/mutants.py)
sind es hier nur zwei kleine, mechanisch aus buchung.py übernommene Module - eine handverlesene Liste deckt
jede Vergleichsoperation, jede Vorzeichen-/Faktor-Stelle und jede Grenzbedingung ab, ohne die Maschinerie
eines Generators zu brauchen.

EQUIVALENT_NOTES wird nach dem ersten vollen Lauf mit der tatsächlichen Einordnung der Überlebenden gefüllt
(siehe tools/mutation_check.py)."""
EQUIVALENT_NOTES = """Stand nach dem vollen Lauf (18 handverlesene Mutanten, sowohl --jobs 4 als auch --jobs 1
reproduzierbar gleich, siehe AP 7): Lauf 1 fand 9 von 18, 8 überlebten (die meisten Epsilon-Grenzfälle der
1e-9-Toleranzen in policy_fcfs/policy_threshold/policy_dp, der 0,6-Korrelationsfaktor in make_requests und ein
Off-by-one an der Wertfunktions-Horizontgrenze in policy_dp). Alle 8 waren echte Testlücken, keine
gleichwertigen Mutanten - für jede wurde ein gezielter Grenzfall-Test in tests/test_model.py ergänzt
(Preis/Gewicht exakt an der Toleranzgrenze konstruiert, ein kontrollierter Zufallsgenerator-Ersatz für die
Korrelationsformel, eine Anfrageliste länger als der Wertfunktions-Horizont). Stabiler Lauf danach: 18 von 18
gefunden, 0 überlebt, 0 Fehler - anders als bei uld-beladeplan-demo (dort einige strukturell gleichwertige
Mutanten durch CP-SAT-Grenzfälle) sind hier alle Stellen mit vertretbarem Aufwand erreichbar, weil beide
Kernmodule reines Python/NumPy ohne Solver-Nichtdeterminismus sind."""

MUTANTS = [
    # --- uldb2_model.py: policy_fcfs ---------------------------------------------------------------------
    ("uldb2_model.py", "ok = r.weight_kg <= remaining + 1e-9\n        accepted.append(ok)\n        if ok:\n            remaining -= r.weight_kg\n    return accepted\n\n\ndef policy_threshold",
     "ok = r.weight_kg < remaining + 1e-9\n        accepted.append(ok)\n        if ok:\n            remaining -= r.weight_kg\n    return accepted\n\n\ndef policy_threshold"),
    # --- uldb2_model.py: policy_threshold -----------------------------------------------------------------
    ("uldb2_model.py", "ok = r.weight_kg <= remaining + 1e-9 and (r.price / r.weight_kg) >= min_price_per_kg - 1e-9",
     "ok = r.weight_kg <= remaining + 1e-9 and (r.price / r.weight_kg) > min_price_per_kg - 1e-9"),
    ("uldb2_model.py", "ok = r.weight_kg <= remaining + 1e-9 and (r.price / r.weight_kg) >= min_price_per_kg - 1e-9",
     "ok = r.weight_kg < remaining + 1e-9 and (r.price / r.weight_kg) >= min_price_per_kg - 1e-9"),
    # --- uldb2_model.py: make_requests (Korrelationsformel) -----------------------------------------------
    ("uldb2_model.py", "price_per_kg = base_price_per_kg * (1.0 - price_weight_corr * 0.6 * w_frac)",
     "price_per_kg = base_price_per_kg * (1.0 - price_weight_corr * 0.5 * w_frac)"),
    ("uldb2_model.py", "w_frac = (w - weight_range[0]) / (weight_range[1] - weight_range[0])",
     "w_frac = (w - weight_range[1]) / (weight_range[1] - weight_range[0])"),
    # --- uldb2_model.py: revenue_of ------------------------------------------------------------------------
    ("uldb2_model.py", "return sum(r.price for r, a in zip(requests, accepted) if a)",
     "return sum(r.price for r, a in zip(requests, accepted) if not a)"),
    # --- uldb2_dp.py: dp_value_function --------------------------------------------------------------------
    ("uldb2_dp.py", "if c_idx <= c:\n                        gain_accept = price + V[t + 1, c - c_idx]\n                        gain_reject = V[t + 1, c]\n                        best_accum += max(gain_accept, gain_reject)",
     "if c_idx < c:\n                        gain_accept = price + V[t + 1, c - c_idx]\n                        gain_reject = V[t + 1, c]\n                        best_accum += max(gain_accept, gain_reject)"),
    ("uldb2_dp.py", "best_accum += max(gain_accept, gain_reject)", "best_accum += min(gain_accept, gain_reject)"),
    ("uldb2_dp.py", "gain_accept = price + V[t + 1, c - c_idx]", "gain_accept = price - V[t + 1, c - c_idx]"),
    ("uldb2_dp.py", "V[t, c] = best_accum / n_combo", "V[t, c] = best_accum / (n_combo + 1)"),
    ("uldb2_dp.py", "c_idx = int(round(w / CAP_STEP))\n                    if c_idx <= c:",
     "c_idx = int(round(w / CAP_STEP)) + 1\n                    if c_idx <= c:"),
    # --- uldb2_dp.py: policy_dp -----------------------------------------------------------------------------
    ("uldb2_dp.py", "if r.weight_kg > remaining + 1e-9:\n            accepted.append(False)\n            continue",
     "if r.weight_kg > remaining - 1e-9:\n            accepted.append(False)\n            continue"),
    ("uldb2_dp.py", "c = min(int(round(remaining / CAP_STEP)), n_cap - 1)", "c = min(int(round(remaining / CAP_STEP)) + 1, n_cap - 1)"),
    ("uldb2_dp.py", "c_after = max(c - c_idx, 0)", "c_after = max(c - c_idx - 1, 0)"),
    ("uldb2_dp.py", "bid_price = (V[t + 1, c] - V[t + 1, c_after]) if t + 1 < V.shape[0] else 0.0",
     "bid_price = (V[t + 1, c] - V[t + 1, c_after]) if t + 1 <= V.shape[0] else 0.0"),
    ("uldb2_dp.py", "ok = r.price >= bid_price - 1e-9", "ok = r.price > bid_price - 1e-9"),
    ("uldb2_dp.py", "ok = r.price >= bid_price - 1e-9", "ok = r.price >= bid_price + 1e-9"),
    ("uldb2_dp.py", "if ok:\n            remaining -= r.weight_kg\n    return accepted",
     "if ok:\n            remaining -= r.weight_kg * 1.01\n    return accepted"),
]
