"""PDF-Export (fpdf2, Standardschriften): Sonderzeichen werden bereinigt, jede Ansicht und jede Prämienart erzeugt ein gültiges PDF."""

import pytest

import gwt_constants as C
import gwt_evaluation as E
import gwt_pdf_export as P


def test_clean_replaces_known_special_characters_and_drops_emoji():
    assert P.clean("Prämie – 5 € „x“ ≤ 3 × 2 −1 🚚") == 'Prämie - 5 EUR "x" <= 3 x 2 -1 '
    assert P.clean("äöüß") == "äöüß"       # Umlaute gehören zur Standardschrift und bleiben


@pytest.mark.parametrize("ptype", C.PTYPE_OPTIONS)
def test_pdf_for_every_step_and_prize_type(ptype):
    settings = E.Settings(15, 2, 0.5, ptype, 300, 7)
    a = E.analyse(settings)
    for step in a.steps:
        data = P.build_pdf(settings, a, step.key)
        assert data[:5] == b"%PDF-" and len(data) > 1000


def test_pdf_handles_an_empty_plan():
    settings = E.Settings(15, 2, 0.2, "lognormal", 300, 5)
    a = E.analyse(settings)
    assert P.build_pdf(settings, a, "G_ratio")[:5] == b"%PDF-"
