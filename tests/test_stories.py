"""Abnahmekriterien der Presets (gwt_stories.py) an der angezeigten Instanz; Seeds liegen außerhalb der Messreihe und der Abstimmung."""

import pytest

import gwt_constants as C
import gwt_evaluation as E
import gwt_stories as ST


def test_every_preset_has_a_story():
    assert set(ST.STORIES) == set(C.PRESETS)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_the_preset_instance_shows_its_story(name):
    p = C.PRESETS[name]
    a = E.analyse(E.Settings(p["n"], p["k"], p["f"], p["ptype"], p["ils"], p["seed"]))
    assert ST.STORIES[name](a), name


def test_each_criterion_flips_at_its_threshold():
    """Künstliche Treppen: jedes Kriterium kippt einzeln an seiner Schwelle (Prämien in Prozent des Besten 1000)."""
    import gwt_scenario as S
    inst = S.make_instance(15, 1, 1, 0.5, "lognormal")

    def an(**p):
        base = {"G_prize": 700, "G_ratio": 950, "A_route": 950, "B_insert": 960, "C_replace": 970, "E_ils_ohne": 990, "D_ils": 1000}
        base.update(p)
        steps = tuple(E.Step(k, E.STEP_LABELS[k], ((1,),), v, 1, 100, 0.0) for k, v in base.items())
        return E.Analysis(inst, steps, max(base.values()))

    assert ST.story_standard(an()) and not ST.story_standard(an(G_ratio=961, A_route=961)) and not ST.story_standard(an(A_route=951))
    assert ST.story_knapp(an(G_prize=950)) and not ST.story_knapp(an(G_prize=949)) and not ST.story_knapp(an(D_ils=990, E_ils_ohne=990, C_replace=991))
    assert ST.story_fern(an(G_ratio=920)) and not ST.story_fern(an(G_ratio=921))
    assert ST.story_gleich(an(C_replace=960)) and not ST.story_gleich(an(C_replace=961)) and not ST.story_gleich(an(D_ils=940))
    assert ST.story_gross(an(G_ratio=950)) and not ST.story_gross(an(G_ratio=951))
