"""Jede Zahl des README (Abschnitt Befunde) und der App-Texte wird hier aus data/gwt_results.json nachgerechnet (DEMO-PLAYBOOK §4, §11a).

Der Test baut die erwarteten Zeichenketten aus der Ergebnisdatei und verlangt sie wörtlich im README: ändert sich die Datei oder der Text,
bricht der Test, bevor eine falsche Zahl veröffentlicht wird."""

import math
import pathlib

import gwt_constants as C
import gwt_results as R

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
DATA = R.load()


def cell(n, k, f, ptype):
    return next(c for c in DATA["cells"] if (c["n"], c["K"], c["f"], c["ptype"]) == (n, k, f, ptype))


def has(text):
    assert text in README, text


def test_leiter_der_verfahren_auf_der_basis():
    c = cell(25, 2, 0.5, "lognormal")
    s = c["share"]
    has(f"höchste Prämie zuerst {R.num(s['G_prize'])} %")
    has(f"Verhältnis-Greedy {R.num(s['G_ratio'])} %")
    has(f"plus Lokalsuche {R.num(s['G_LS'])} %")
    has(f"OR-Tools (Standard) {R.num(s['GLS'])} %")
    has(f"OR-Tools (abgestimmt, zeitgleich) {R.num(s['GLS_t'])} %")
    has(f"eigene Suche (ILS) {R.num(s['ILS'])} %")
    assert c["n_inst"] == 30


def test_kein_kipppunkt_ueber_dem_budget():
    cells = [c for c in R.budget_curve(25, 2, "lognormal") if c["f"] >= 0.3]
    gaps = [100 - c["share"]["G_ratio"] for c in cells]
    assert len(cells) == 7 and all(c["n_inst"] == 30 for c in cells)
    has(f"zwischen {R.num(min(gaps))} und {R.num(max(gaps))} Punkten")


def test_ablation_der_zugarten():
    ab = R.ablation_cell(25, 2, 0.4, "lognormal")
    assert ab["A_gleiche_Menge"] == 30 and ab["n_inst"] == 30
    assert sum(a["A_gleiche_Menge"] for a in DATA["ablation"]) == 210 and all(a["n_inst"] == 30 for a in DATA["ablation"])
    has("in 30 von 30 Instanzen nicht (über alle 7 Ablationszellen, das sind 25 Kunden mit Budgetanteil 0,4 und 0,7 in drei Prämienarten sowie 40 Kunden: 210 von 210)")
    has(f"sparen {R.num(ab['A_Zeit_gespart_%'])} % Fahrzeit")
    has(f"Einfügen {R.pm(ab['B_minus_G_pkt'])} Punkte, Ersetzen weitere {R.pm(ab['C_minus_B_pkt'])}")
    has(f"im ILS bringt Ersetzen {R.pm(ab['D_minus_E_pkt'])} Punkte gegenüber dem ILS ohne Ersetzen, Einfügen im Lokalsuchschritt {R.pm(ab['D_minus_F_pkt'])} gegenüber dem ILS nur mit Routenzügen")


def test_zonen_der_19_haupt_sweep_zellen():
    counts = R.zone_counts()
    assert counts == {"A": 3, "B": 11, "C": 5} and sum(c["source"] == "main" for c in DATA["cells"]) == 19
    has("In 3 Zellen höchstens 2 Punkte hinter dem Besten, in 11 Zellen zwischen 2 und 6 Punkten, in 5 Zellen mehr als 6 Punkte")
    zone_c = [c for c in DATA["cells"] if c["source"] == "main" and R.zone(c) == "C"]
    assert sorted(c["ptype"] for c in zone_c) == ["fern", "fern", "gleich", "gleich", "lognormal"] and [c["n"] for c in zone_c if c["ptype"] == "lognormal"] == [60]
    has("die 5 Zellen: „fern = wertvoll“ (2), gleiche Prämien (2), 60 Kunden")


def test_rueckstand_von_ortools_nach_groesse_und_einstellung():
    row = [cell(n, 2, 0.5, "lognormal")["gap_tuned"] for n in (20, 40, 60)]
    has(" / ".join(R.pm(p) for p in row) + " Punkte")
    worst = max((c for c in DATA["cells"]), key=lambda c: c["gap_std"][0])
    assert (worst["n"], worst["K"]) == (40, 1)
    k1 = [c for c in DATA["cells"] if c["K"] == 1 and c["n"] in (40, 60)]
    assert len(k1) == 3
    has(f"bei 1 Fahrzeug, gestreuten Prämien und 40 bis 60 Kunden {R.num(min(c['gap_std'][0] for c in k1), 1, True)} bis {R.num(max(c['gap_std'][0] for c in k1), 1, True)} Punkte (3 Zellen: 40 Kunden bei Budgetanteil 0,4 und 0,5, 60 Kunden bei 0,5)")


def test_praemienart():
    fern, gleich = cell(25, 2, 0.4, "fern"), cell(25, 2, 0.4, "gleich")
    has(f"ILS − OR-Tools {R.pm(fern['gap_std'])} (Standard) bzw. {R.pm(fern['gap_tuned'])} (abgestimmt)")
    has(f"{R.pm(gleich['gap_std'])} (Standard) bzw. {R.pm(gleich['gap_tuned'])} (abgestimmt, schlechter als Standard)")
    assert gleich["gap_tuned"][0] > gleich["gap_std"][0]


def test_ortools_schlaegt_den_ils_in_einer_von_840():
    assert sum(c["n_total"] for c in DATA["cells"]) == 840 and sum(c["tuned_over_ils"] or 0 for c in DATA["cells"]) == 1
    has("in 1 von 840 Instanzen")


def test_optimum_bei_einem_fahrzeug_und_20_kunden():
    k1 = DATA["k1_exact"]
    assert k1["n_inst"] == 20
    has(f"ILS {R.num(k1['ILS'])} % des Optimums (unter dem Optimum in {k1['below']['ILS']} von 20)")
    has(f"Verhältnis-Greedy {R.num(k1['G_ratio'])} % ({k1['below']['G_ratio']} von 20)")
    has(f"plus Lokalsuche {R.num(k1['G_LS'])} % ({k1['below']['G_LS']} von 20)")
    has(f"OR-Tools (Standard) {R.num(k1['GLS'])} % ({k1['below']['GLS']} von 20)")


def test_cpsat_bewiesene_zellen_und_schranke():
    cells = {f: cell(25, 2, f, "lognormal") for f in (0.2, 0.3, 0.4, 0.5, 0.65, 0.7, 0.8, 1.0)}
    has(" / ".join(str(c["proven"]) for c in cells.values()) + " von 30 Instanzen bei Budgetanteil " + " / ".join(R.num(f, 2 if f == 0.65 else 1) for f in cells))
    has(f"Schranke bei Budgetanteil 0,5 im Mittel {R.num(cells[0.5]['bound_gap_unproven'], 0)} % über dem besten bekannten Wert")
    assert cells[0.5]["n_unproven"] == 27


def test_ils_laesst_sich_nicht_verbessern():
    v = DATA["ils_variants"]
    v0 = next(val for k, val in v.items() if k.startswith("V0 "))
    others = max(val for k, val in v.items() if not k.startswith("V0"))
    lang = v["V0lang"]
    assert others < v0 < lang
    has(f"der jetzige ILS liegt bei {R.num(v0, 2)} % des Besten, die beste Variante bei {R.num(max(val for k, val in v.items() if k not in ('V0lang',) and not k.startswith('V0 ')), 2)} %, ein zehnmal längerer Lauf des jetzigen ILS (kein Variantenkandidat) bei {R.num(lang, 2)} %")
    assert sum(c["ils30k_besser"] for c in DATA["convergence"]) == 5
    has("in 5 von 30 Instanzen mehr (n = 40 und 60)")


def test_abstimmung_auf_getrennten_instanzen():
    tuning = DATA["tuning"]
    assert len(tuning) == 8 and all(t["n_inst"] == 60 for t in tuning)
    chosen = max(tuning, key=lambda t: t["mean_share_of_ils"])
    std = next(t for t in tuning if t["name"].startswith("T0"))
    assert chosen["name"].startswith("T6")
    has(f"gewählt wurde die Einstellung mit {R.num(chosen['mean_share_of_ils'], 2)} % des ILS gegen {R.num(std['mean_share_of_ils'], 2)} % für die Standard-Einstellung")


def test_rechenbudget_des_ils():
    b = R.ils_budget()
    low = min(b[str(n)]["300"]["share"] for n in C.N_OPTIONS)
    assert math.floor(low * 10) / 10 == 99.4 and low >= 99.4
    has("bei 300 Iterationen im Mittel über 10 Instanzen mindestens 99,4 % des besten der drei Läufe")
    has(f"bei n = 60 die schlechteste Instanz {R.num(b['60']['300']['worst_share'])} %")
    assert "(bei 60 Kunden die schlechteste Instanz bei 95,1 %)" in APP and round(b["60"]["300"]["worst_share"], 1) == 95.1
    has(f"Rechenzeit bei n = 60 im Mittel {R.num(b['60']['300']['sec'])} s statt {R.num(b['60']['3000']['sec'])} s bei 3000 Iterationen")
    assert "mindestens 99,4 % des besten der drei Läufe" in APP


def test_app_texte_nennen_die_gemessenen_zahlen():
    k1 = DATA["k1_exact"]
    assert "{k1['ILS']" in APP or "R.num(k1['ILS'])" in APP
    assert k1["ILS"] == 100.0
    counts = R.zone_counts()
    assert "counts['A']" in APP and sum(counts.values()) == 19


def test_preset_help_superlativ_ist_gemessen():
    """'am weitesten zurück' (Preset Ferne Kunden wertvoll): größter Rückstand von Greedy plus Lokalsuche aller 19 Haupt-Sweep-Zellen."""
    main = [c for c in DATA["cells"] if c["source"] == "main" and c["n_inst"] > 0]
    worst = max(main, key=R.gap_greedy_ls)
    assert worst["ptype"] == "fern" and worst["f"] == 0.4
    assert "am weitesten zurück" in C.PRESET_HELP["Ferne Kunden wertvoll"]


def test_preset_help_wachstum_mit_n_bei_2_und_4_fahrzeugen():
    for k in (2, 4):
        gaps = [cell(n, k, 0.5, "lognormal")["gap_tuned"][0] for n in (20, 40, 60)]
        assert gaps == sorted(gaps), (k, gaps)
    assert "bei 2 und 4 Fahrzeugen wächst" in C.PRESET_HELP["Großer Fall"]
    big = cell(60, 2, 0.4, "lognormal")
    assert big["share"]["GLS_t"] - big["share"]["GLS"] > 5.0      # 'macht mehrere Punkte aus'


def test_kipppunkt_zeile_nennt_die_zelle_unterhalb():
    c02 = cell(25, 2, 0.2, "lognormal")
    has(f"bei Budgetanteil 0,2 sind es {R.num(100 - c02['share']['G_ratio'])} Punkte")
    assert cell(25, 2, 0.1, "lognormal")["share"]["G_ratio"] == 100.0       # Budgetanteil 0,1: alle Instanzen trivial
    zone_a = sorted(c["f"] for c in DATA["cells"] if c["source"] == "main" and c["n_inst"] > 0 and R.zone(c) == "A")
    assert zone_a == [0.1, 0.2, 0.3]
    has("die 3 Zellen mit höchstens 2 Punkten sind knappe Budgets, darunter die triviale Zelle mit Budgetanteil 0,1")


def test_zaehlung_ortools_gegen_ils():
    cells = DATA["cells"]
    total = sum(c["n_total"] for c in cells)
    empty = sum(c["counts"]["empty"] for c in cells)
    assert (total, empty) == (840, 9)
    assert sum(c["counts"]["tuned_over_ils"] for c in cells) == 1 and sum(c["counts"]["std_over_ils"] for c in cells) == 4
    assert sum(c["counts"]["tied_tuned"] for c in cells) == 337 and total - empty == 831
    has("in 1 von 840 Instanzen strikt besser (mit der Standard-Einstellung in 4 von 840); gleichauf mit dem ILS in 337 von 831 nicht leeren Instanzen (9 Instanzen sind leer, das heißt: kein Kunde erreichbar)")


def test_abgestimmt_gegen_standard_je_zelle():
    cells = DATA["cells"]
    smaller = sum(c["gap_tuned"][0] < c["gap_std"][0] for c in cells)
    larger = sum(c["gap_tuned"][0] > c["gap_std"][0] for c in cells)
    equal = len(cells) - smaller - larger
    assert (smaller, larger, equal) == (21, 6, 1)
    has("abgestimmter Rückstand kleiner in 21 von 28 Zellen, größer in 6, gleich in 1")
    bigger = {(c["n"], c["K"], c["ptype"]) for c in cells if c["gap_tuned"][0] > c["gap_std"][0]}
    assert {(25, 2, "gleich"), (15, 2, "lognormal"), (20, 2, "lognormal"), (20, 4, "lognormal"), (40, 4, "lognormal")} == bigger
    g7 = cell(25, 2, 0.7, "gleich")
    has(f"bei Budgetanteil 0,7: {R.num(g7['gap_std'][0], 1, True)} (Standard) bzw. {R.num(g7['gap_tuned'][0], 1, True)} (abgestimmt)")


def test_beweisgrenzen_der_app_texte():
    assert cell(40, 1, 0.4, "lognormal")["proven"] == 0 and cell(40, 2, 0.4, "lognormal")["proven"] == 0
    assert cell(40, 4, 0.4, "lognormal")["proven"] == 29 and not any(c["n"] == 60 and c["proven"] for c in DATA["cells"])
    bound = {f: cell(25, 2, f, "lognormal")["bound_gap_unproven"] for f in (0.4, 0.5, 0.65, 1.0)}
    assert round(min(bound[0.4], bound[0.5], bound[0.65])) == 42 and round(max(bound[0.4], bound[0.5], bound[0.65])) == 100 and round(bound[1.0]) == 4
    for needle in ("um 42 bis 100 % über dem Besten", "nur 4 % darüber", "mit 4 Fahrzeugen 29 von 30"):
        assert needle in APP, needle


def test_praemienart_zahlen_der_app_tabelle():
    std = {p: cell(25, 2, 0.4, p)["gap_std"][0] for p in ("gleich", "lognormal", "fern")}
    assert [round(std[p], 1) for p in ("gleich", "lognormal", "fern")] == [0.3, 3.5, 6.7]


def test_ablation_zelle_der_app_ist_dieselbe_wie_im_readme():
    ab = R.ablation_cell(25, 2, 0.4, "lognormal")
    assert (round(ab["F_ILS_nur_Route"], 1), round(ab["G"], 1)) == (97.6, 91.9)
    assert "ILS nur mit Routenzügen" in APP and "ändert vor allem das Entfernen und verrauschte Neueinfügen die Auswahl" in APP
