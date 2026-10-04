"""AppTest: Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, PDF, Texte. Deckt
DEMO-PLAYBOOK Abschnitt 5 (Browser-Verifikation reicht AppTest allein nicht, ergänzt in AP 7 mit einem
echten Browser-Durchlauf)."""
import pathlib
import re

import pytest
from streamlit.testing.v1 import AppTest

import uldb2_constants as C
import uldb2_results as R
from uldb2_presets import PRESET_STATE_KEYS, SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
DATA = R.load_results()
FOOTER = (
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html)."
)


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        if key == "seed_input":
            at.number_input(key=key).set_value(value)
        elif key == "threshold_slider":
            at.slider(key=key).set_value(value)
        else:
            at.select_slider(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def state_values(at):
    return {key: at.session_state[key] for key in SETTING_SPECS}


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]
    assert len(at.title) == 1 and at.title[0].value == "✈️ Buchungsannahme mit Gewichtslimit"
    assert any(v.value.startswith("## ✈️ Welche Buchungen werden angenommen?") for v in at.markdown)
    assert any(v.value.startswith("### 📐 Was die Messreihe über 150 Instanzen") for v in at.markdown)
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – vollständiger Methodenvergleich",
                                                "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS)
    assert len(at.sidebar.header) == 1 and len(at.sidebar.subheader) == 0


def test_preset_buttons_have_help_text():
    at = fresh()
    buttons = [b for b in at.button if b.label in C.PRESETS]
    assert all(b.help and len(b.help) > 15 for b in buttons)
    assert [b.help for b in buttons] == [C.PRESET_HELP[n] for n in C.PRESETS]


def test_no_dead_controls():
    """Nur die dokumentierten Widgets: drei select_slider (Stufenregler), ein slider (Preisschwelle,
    kontinuierlich), ein number_input (Seed) - keine Checkboxen/Toggles."""
    at = fresh()
    assert not at.sidebar.checkbox and not at.sidebar.toggle and not at.checkbox and not at.toggle
    assert len(at.sidebar.slider) == 1  # nur die Preisschwelle ist ein kontinuierlicher Regler


def test_sliders_have_the_measured_stages_and_seed_bounds():
    at = fresh()
    assert list(at.select_slider(key="t_slider").options) == [str(v) for v in C.T_OPTIONS]
    assert list(at.select_slider(key="cap_slider").options) == [str(v) for v in C.CAP_OPTIONS]
    assert list(at.select_slider(key="corr_slider").options) == [str(v) for v in C.CORR_OPTIONS]
    threshold = at.slider(key="threshold_slider")
    assert (threshold.min, threshold.max, threshold.step, threshold.value) == (
        C.THRESHOLD_RANGE[0], C.THRESHOLD_RANGE[1], C.THRESHOLD_STEP, C.THRESHOLD_DEFAULT)
    seed = at.number_input(key="seed_input")
    assert (seed.min, seed.max, seed.step, seed.value) == (C.SEED_RANGE[0], C.SEED_RANGE[1], 1, C.SEED_DEFAULT)


def test_default_state_and_permalink_written_to_the_address_bar():
    at = fresh()
    assert state_values(at) == dict(t_slider=C.T_DEFAULT, cap_slider=C.CAP_DEFAULT, corr_slider=C.CORR_DEFAULT,
                                     threshold_slider=C.THRESHOLD_DEFAULT, seed_input=C.SEED_DEFAULT)
    qp = {k: (v[0] if isinstance(v, list) else v) for k, v in dict(at.query_params).items()}
    assert qp["t"] == str(C.T_DEFAULT) and qp["seed"] == str(C.SEED_DEFAULT)


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink, Regler
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_sets_all_controls_and_runs_without_exception(name):
    at = fresh()
    click(at, name)
    p = C.PRESETS[name]
    assert state_values(at) == {PRESET_STATE_KEYS[k]: v for k, v in p.items()}
    cell = R.find_cell(DATA, p["t"], p["cap"], p["corr"])
    assert any(R.judgment_text(cell) in i.value for i in at.info)


def test_permalink_sets_the_controls_and_snaps_to_stages():
    at = fresh(t="40", cap="1500", corr="0.6", threshold="9.5", seed="17")
    assert state_values(at) == dict(t_slider=40, cap_slider=1500.0, corr_slider=0.6, threshold_slider=9.5, seed_input=17)
    at = fresh(t="30", cap="1800", corr="0.9", threshold="99", seed="-4")
    vals = state_values(at)
    assert vals["t_slider"] in C.T_OPTIONS and vals["cap_slider"] in C.CAP_OPTIONS and vals["corr_slider"] in C.CORR_OPTIONS
    assert vals["threshold_slider"] == C.THRESHOLD_RANGE[1]  # 99 wird auf die Obergrenze begrenzt
    assert vals["seed_input"] == C.SEED_RANGE[0]  # -4 wird auf die Untergrenze begrenzt


def test_all_controls_at_min_and_max_run_without_exception():
    at = fresh()
    for key, options in (("t_slider", C.T_OPTIONS), ("cap_slider", C.CAP_OPTIONS), ("corr_slider", C.CORR_OPTIONS)):
        for v in (options[0], options[-1]):
            set_and_run(at, **{key: v})
            assert state_values(at)[key] == v
    for v in C.THRESHOLD_RANGE:
        set_and_run(at, threshold_slider=v)
        assert state_values(at)["threshold_slider"] == v
    for v in C.SEED_RANGE:
        set_and_run(at, seed_input=v)
        assert state_values(at)["seed_input"] == v


def test_new_instance_button_rolls_a_new_seed(monkeypatch):
    import uldb2_presets as P
    frozen = iter([3, 5, C.SEED_DEFAULT, 3])
    monkeypatch.setattr(P.random, "randint", lambda lo, hi: next(frozen))
    at = fresh()
    seen = {at.session_state["seed_input"]}
    for _ in range(3):
        click(at, "🎲 Neue Instanz")
        seen.add(at.session_state["seed_input"])
        assert C.SEED_RANGE[0] <= at.session_state["seed_input"] <= C.SEED_RANGE[1]
    assert seen == {C.SEED_DEFAULT, 3, 5}


# ---------------------------------------------------------------------------------------------------
# Kennzahlen, Texte
# ---------------------------------------------------------------------------------------------------
def test_main_metrics_are_present():
    at = fresh()
    assert len(at.metric) >= 4


def test_threshold_regler_changes_the_shown_acceptance_pattern():
    """Regressionstest gegen einen wirkungslosen Regler: eine sehr niedrige gegen eine sehr hohe Preisschwelle
    führen zu unterschiedlichen Umsätzen der festen Schwellenregel."""
    at_low = fresh(threshold=str(C.THRESHOLD_RANGE[0]))
    at_high = fresh(threshold=str(C.THRESHOLD_RANGE[1]))
    rev_low = next(m for m in at_low.metric if m.label == "Umsatz feste Schwelle").value
    rev_high = next(m for m in at_high.metric if m.label == "Umsatz feste Schwelle").value
    assert rev_low != rev_high


def test_pdf_download_button_is_present_and_named():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Buchungsannahme als PDF herunterladen"


def test_all_plotly_charts_render_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    assert len(charts) >= 4
    ids = [c.proto.id for c in charts]
    assert len(set(ids)) == len(ids)


def test_no_dead_file_links_in_markdown():
    at = fresh()
    for md in list(at.markdown) + list(at.caption):
        for target in re.findall(r"\]\(([^)]+)\)", md.value):
            assert target.startswith("https://"), (target, md.value[:80])


def test_real_umlauts_present():
    at = fresh()
    text = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "Rückstand" in text and "für" in text and "Preisschwelle" in text


def test_regime_dataframe_is_not_a_dead_column():
    """Nullspalten-Signal: keine Spalte der Regime-Tabelle ist überall gleich."""
    at = fresh()
    regime_frame = next(d.value for d in at.dataframe if "Rückstand FCFS" in d.value.columns)
    assert len(regime_frame) == 18
    for col in ("Rückstand FCFS", "Rückstand feste Schwelle", "Auslastung DP-Regel"):
        assert regime_frame[col].astype(str).nunique() > 1


def test_expander_texts_state_the_limits():
    at = fresh()
    how = next(m.value for m in at.markdown if "Nicht Teil dieser Demo" in m.value)
    for needle in ("FCFS", "Preisschwelle", "DP-Regel", "erfunden, nicht kalibriert", "revenue-management-demo",
                   "Overbooking"):
        assert needle in how, needle
    math = next(m.value for m in at.markdown if "Implementiert in" in m.value)
    for needle in ("uldb2_model.py", "uldb2_dp.py"):
        assert needle in math, needle
