"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier."""

import gwt_evaluation as ev
import gwt_scenario as S


def _cell(g_ls, ils=99.9, n=25, K=2, f=0.5, ptype="lognormal", n_inst=30):
    return {"n": n, "K": K, "f": f, "ptype": ptype, "n_inst": n_inst, "share": {"G_LS": g_ls, "ILS": ils}}


def test_regime_zone_thresholds_are_inclusive():
    assert ev.verdict_regime(_cell(98.0), True)[0] == "success"      # Lücke genau 2,0
    assert ev.verdict_regime(_cell(97.9), True)[0] == "info"         # Lücke 2,1
    assert ev.verdict_regime(_cell(94.0), True)[0] == "info"         # Lücke genau 6,0
    assert ev.verdict_regime(_cell(93.9), True)[0] == "warning"      # Lücke 6,1


def test_regime_text_names_cell_gap_and_ils_share():
    kind, text = ev.verdict_regime(_cell(96.8, ils=99.9, n=25, K=2, f=0.5), True)
    assert kind == "info"
    assert "n = 25, 2 Fahrzeuge, Budgetanteil 0,5, gestreute Prämien, 30 Instanzen" in text
    assert "**3,2 Punkte**" in text and "zwischen 2 und 6 Punkten" in text and "bei 99,9 %" in text
    assert "nächstliegende" not in text                              # exakte Zelle: kein Hinweis


def test_regime_text_for_each_zone_and_for_a_neighbour_cell():
    assert "höchstens 2 Punkte (gesetzte Schwelle)" in ev.verdict_regime(_cell(99.0), True)[1]
    assert "mehr als 6 Punkte (gesetzte Schwelle): hier lässt Greedy mit Lokalsuche viel liegen" in ev.verdict_regime(_cell(91.6, ptype="fern", f=0.4), True)[1]
    assert "Prämien „fern = wertvoll“" in ev.verdict_regime(_cell(91.6, ptype="fern", f=0.4), True)[1]
    assert "gleiche Prämien" in ev.verdict_regime(_cell(93.3, ptype="gleich"), True)[1]
    assert "nächstliegende gemessene Zelle" in ev.verdict_regime(_cell(96.8), False)[1]
    assert "Budgetanteil 0,65" in ev.verdict_regime(_cell(96.6, f=0.65), True)[1]


def _analysis(prizes=None):
    """Handanalyse: Treppe mit festen Prämien; Fahrzeit der Greedy-Stufe 330, der Routenzüge 324 (1,8 % gespart)."""
    inst = S.make_instance(15, 1, 1, 0.5, "lognormal")
    prizes = prizes or {"G_prize": 715, "G_ratio": 914, "A_route": 914, "B_insert": 930, "C_replace": 940, "E_ils_ohne": 950, "D_ils": 958}
    minutes = {"G_ratio": 330, "A_route": 324}
    steps = tuple(ev.Step(k, ev.STEP_LABELS[k], ((1, 2), (3,)), p, 3, minutes.get(k, 340), 0.1) for k, p in prizes.items())
    return ev.Analysis(inst, steps, max(prizes.values()))


def test_stairs_text_names_every_step_and_the_time_saved():
    kind, text = ev.verdict_stairs(_analysis())
    assert kind == "info"
    assert "Verhältnis-Greedy 914 Prämie mit 3 Kunden" in text and "Routenzüge allein: 914 (gleiche Kunden, Fahrzeit −1,8 %)" in text
    assert "Mit Einfügen 930, mit Ersetzen 940. ILS ohne Ersetzen 950, ILS voll 958." in text and "Eine Instanz belegt nichts" in text


def test_ortools_text_shares_are_relative_to_the_best():
    kind, text = ev.verdict_ortools(_analysis(), 900, 950)
    assert kind == "info"
    assert "OR-Tools (Standard) 900, OR-Tools (abgestimmt) 950, eigene Suche (ILS) 958" in text and "bester bekannter Wert 958" in text
    assert "93,9 %, 99,2 %, 100,0 %" in text
    assert "bester bekannter Wert 1000" in ev.verdict_ortools(_analysis(), 1000, 950)[1]   # OR-Tools kann den Besten stellen


def test_exact_verdict_states():
    a = _analysis()
    kind, text = ev.verdict_exact(a, "OPTIMAL", 958, 958.0)
    assert kind == "success" and "Optimum bewiesen: 958" in text and "erreicht 958, also das Optimum" in text
    kind, text = ev.verdict_exact(a, "OPTIMAL", 1000, 1000.0)
    assert kind == "info" and "(95,8 % des Optimums)" in text
    kind, text = ev.verdict_exact(a, "FEASIBLE", 960, 1500.0)
    assert kind == "warning" and "nicht bewiesen" in text and "960 (ILS 958)" in text and "Schranke liegt bei 1500" in text and "um 42 bis 100 % über dem Besten" in text
    assert ev.verdict_exact(a, "FEASIBLE", 960, None)[1].endswith("(ILS 958).")
    assert ev.verdict_exact(a, "UNKNOWN", None, None)[0] == "warning"
