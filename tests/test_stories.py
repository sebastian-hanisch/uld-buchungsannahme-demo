"""uldb2_stories.py: alle fünf Presets bestehen ihre Abnahmekriterien gegen die Messreihe."""
import uldb2_results as R
import uldb2_stories as S

D = R.load_results()


def test_all_five_presets_pass_their_acceptance_criteria():
    results = S.check_all(D)
    assert set(results) == {"Standard", "Viel Restzeit", "Wenig Restzeit", "Zu niedrige Schwelle",
                             "Weniger Auslastung, mehr Umsatz"}
    for name, (ok, msg) in results.items():
        assert ok, f"{name}: {msg}"


def test_check_functions_return_explanatory_text():
    for name, (ok, msg) in S.check_all(D).items():
        assert isinstance(msg, str) and len(msg) > 10, name
