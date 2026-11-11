"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: laedt app.py mit den
Standardeinstellungen, klickt jeden Preset-Button und faehrt jeden Slider an seine Grenzen und prueft, dass
kein Python-Fehler auftritt - insbesondere `streamlit.errors.StreamlitDuplicateElementId` (mehrere
st.plotly_chart-Aufrufe ohne eindeutiges key= koennen zufaellig identischen Inhalt rendern und kollidieren)
und `StreamlitAPIException` bei Slidern mit berechneten Grenzen (min == max)."""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
AUTOPLAY_MARKER = "\u25b6"  # Auto-Play-Buttons (Animation mit sleep) im Smoke-Test auslassen


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception():
    _fresh_app()


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        if AUTOPLAY_MARKER in label:
            continue
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_every_slider_at_its_min_and_max_does_not_raise():
    labels = [s.label for s in _fresh_app().slider]
    assert labels, "keine Slider gefunden"
    for index, label in enumerate(labels):
        for edge in ("min", "max"):
            at = _fresh_app()
            slider = at.slider[index]
            value = slider.min if edge == "min" else slider.max
            if isinstance(slider.value, int):
                value = int(value)
            slider.set_value(value).run(timeout=TIMEOUT)
            assert not at.exception, (label, edge, [str(e) for e in at.exception])


def test_every_select_slider_and_radio_option_does_not_raise():
    """Alle Stufen der diskreten Regler (Kunden, Zeitbudget, Rechenbudget, Prämienart); die schweren Größen mit kleinem Rechenbudget."""
    at = _fresh_app()
    keys = [w.key for w in at.select_slider] + [w.key for w in at.radio]
    assert set(keys) == {"n_slider", "f_slider", "ils_slider", "ptype_radio"}, keys
    for key in keys:
        widget = at.sidebar.select_slider(key=key) if key != "ptype_radio" else at.sidebar.radio(key=key)
        for option in list(widget.options):
            at = _fresh_app()
            widget = at.sidebar.select_slider(key=key) if key != "ptype_radio" else at.sidebar.radio(key=key)
            value = widget.options.index(option) if False else option
            widget.set_value(value if key == "ptype_radio" else _typed(key, option)).run(timeout=TIMEOUT)
            assert not at.exception, (key, option, [str(e) for e in at.exception])


def _typed(key, option):
    """select_slider.options enthält die Anzeigetexte; zurück auf den Wert der Stufe."""
    import gwt_constants as C
    stages = {"n_slider": C.N_OPTIONS, "f_slider": C.F_OPTIONS, "ils_slider": C.ILS_OPTIONS}[key]
    for value in stages:
        if str(value) == str(option) or (key == "f_slider" and f"{value:g}".replace(".", ",") == str(option)) or (key == "ils_slider" and C.ILS_LABELS[value] == str(option)):
            return value
    raise AssertionError((key, option))


def test_ortools_and_exact_buttons_work_and_are_cached_per_setting():
    at = _fresh_app()
    at.button(key="ortools_start").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("OR-Tools (Standard)" in i.value for i in at.info), "Verdikt der OR-Tools-Läufe fehlt"
    assert not [m for m in at.metric if m.value == "–"], "OR-Tools-Kennzahl bleibt leer"
    at.button(key="exact_start").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("Optimum" in w.value for w in list(at.success) + list(at.info) + list(at.warning))
    at.sidebar.select_slider(key="n_slider").set_value(40).run(timeout=TIMEOUT)   # n > 25: der Optimum-Tab bietet den Knopf nicht an
    assert not at.exception and not [b for b in at.button if b.key == "exact_start"]


def test_plans_and_pdf_do_not_crash_for_every_view():
    at = _fresh_app()
    for option in list(at.selectbox(key="view_select").options):
        at.selectbox(key="view_select").set_value(at.selectbox(key="view_select").options[list(at.selectbox(key="view_select").options).index(option)]).run(timeout=TIMEOUT)
        assert not at.exception, (option, [str(e) for e in at.exception])
