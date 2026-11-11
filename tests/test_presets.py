"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink (Begrenzen, Einrasten)."""

import pytest

import gwt_constants as C
import gwt_evaluation as ev
import gwt_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_valid_stages():
    for name, p in C.PRESETS.items():
        assert p["n"] in C.N_OPTIONS and C.K_MIN <= p["k"] <= C.K_MAX and p["f"] in C.F_OPTIONS, name
        assert p["ptype"] in C.PTYPE_OPTIONS and p["ils"] in C.ILS_OPTIONS and 0 <= p["seed"] <= C.SEED_MAX, name


def test_preset_seeds_stay_outside_the_measurement_seeds():
    """Seeds 0 bis 29 gehören der Messreihe, 1000 bis 1011 der Abstimmung: ein Preset darf dort keine Aussage 'finden'."""
    for name, p in C.PRESETS.items():
        assert not (0 <= p["seed"] <= 29 or 1000 <= p["seed"] <= 1011), name


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**{k: v for k, v in C.PRESETS["Standardfall"].items()}) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_stages_are_the_measured_values():
    assert C.N_OPTIONS == (15, 25, 40, 60) and C.F_OPTIONS == (0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0) and (C.K_MIN, C.K_MAX) == (1, 4)


@pytest.mark.parametrize("key, raw, expected", [
    ("n_slider", 30, 25), ("n_slider", 100, 60), ("n_slider", 1, 15),          # Zahlen rasten auf die nächste Stufe ein
    ("f_slider", 0.55, 0.5), ("f_slider", 0.9, 0.8), ("f_slider", 5.0, 1.0),
    ("k_slider", 9, 4), ("k_slider", 0, 1), ("seed_input", -5, 0),             # Begrenzen
    ("ptype_radio", "gleich", "gleich"), ("ptype_radio", "unbekannt", None),   # unbekannter Text wird verworfen
    ("ils_slider", 700, 1000),
])
def test_permalink_values_are_clamped_or_snapped(key, raw, expected):
    spec = P.SETTING_SPECS[key]
    value = spec.caster(raw)
    assert P.clamp_value(spec, value) == expected
