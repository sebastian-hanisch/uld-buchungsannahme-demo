"""uldb2_presets.py: Permalink-Parsing (Begrenzen/Einrasten), Presets, SettingSpec-Grenzen."""
import uldb2_constants as C
from uldb2_presets import SETTING_SPECS, parse_setting


def test_parse_setting_snaps_options_to_the_nearest_stage():
    spec = SETTING_SPECS["t_slider"]
    assert parse_setting(spec, "24") == 25
    assert parse_setting(spec, "1000") == 40
    assert parse_setting(spec, "-5") == 15


def test_parse_setting_clamps_the_continuous_threshold_and_keeps_it_a_float():
    spec = SETTING_SPECS["threshold_slider"]
    assert parse_setting(spec, "1.0") == C.THRESHOLD_RANGE[0]
    assert parse_setting(spec, "99") == C.THRESHOLD_RANGE[1]
    value = parse_setting(spec, "7.3")
    assert value == 7.3 and isinstance(value, float)


def test_parse_setting_clamps_seed_to_an_int():
    spec = SETTING_SPECS["seed_input"]
    assert parse_setting(spec, "-4") == C.SEED_RANGE[0]
    assert parse_setting(spec, "9999") == C.SEED_RANGE[1]
    value = parse_setting(spec, "12.6")
    assert value == 13 and isinstance(value, int)


def test_parse_setting_returns_none_for_unparseable_values():
    spec = SETTING_SPECS["seed_input"]
    assert parse_setting(spec, "not-a-number") is None
    assert parse_setting(spec, None) is None


def test_all_presets_declare_every_setting_field():
    for name, p in C.PRESETS.items():
        assert set(p) == {"t", "cap", "corr", "threshold", "seed"}, name
        assert p["t"] in C.T_OPTIONS
        assert p["cap"] in C.CAP_OPTIONS
        assert p["corr"] in C.CORR_OPTIONS
        assert C.THRESHOLD_RANGE[0] <= p["threshold"] <= C.THRESHOLD_RANGE[1]
        assert C.SEED_RANGE[0] <= p["seed"] <= C.SEED_RANGE[1]


def test_every_preset_has_help_text():
    assert set(C.PRESET_HELP) == set(C.PRESETS)
    assert all(len(text) > 15 for text in C.PRESET_HELP.values())
