"""Vorgerechnete Messreihe (data/gwt_results.json): Aufbau, Zählungen, Zellen-Zuordnung und Zahlenformate."""

import json
import pathlib

import pytest

import gwt_constants as C
import gwt_results as R

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_file_has_the_documented_cells():
    cells = R.load()["cells"]
    assert len(cells) == 28 and sum(c["source"] == "main" for c in cells) == 19 and sum(c["source"] == "nk" for c in cells) == 9
    assert len({(c["n"], c["K"], c["f"], c["ptype"]) for c in cells}) == 28            # keine doppelte Zelle
    assert all(c["n_inst"] <= 30 and c["n_inst"] <= c["n_total"] for c in cells)
    assert len(R.load()["ablation"]) == 7


def test_zone_counts_and_boundaries():
    assert R.zone_counts() == {"A": 3, "B": 11, "C": 5}      # die Zählung der Kernfrage 2 und des README
    assert R.zone({"share": {"G_LS": 98.0}}) == "A" and R.zone({"share": {"G_LS": 97.99}}) == "B"
    assert R.zone({"share": {"G_LS": 94.0}}) == "B" and R.zone({"share": {"G_LS": 93.99}}) == "C"


def test_exact_cells_are_found_exactly():
    for (n, k, f, p) in ((25, 2, 0.5, "lognormal"), (25, 2, 0.4, "fern"), (25, 2, 0.4, "gleich"), (60, 2, 0.4, "lognormal"), (40, 2, 0.5, "lognormal")):
        cell, exact = R.nearest_cell(n, k, f, p)
        assert exact and (cell["n"], cell["K"], cell["f"], cell["ptype"]) == (n, k, f, p)


def test_exact_proof_cells_shape():
    ec = R.load()["exact_cells"]
    assert len(ec) == 12 and len({(c["n"], c["K"], c["f"]) for c in ec}) == 12
    assert all(c["n"] == 40 and c["ptype"] == "lognormal" and c["n_inst"] == 30 and 0 <= c["proven"] <= 30 for c in ec)
    assert {c["K"] for c in ec} == {1, 2, 3, 4} and {c["f"] for c in ec} == {0.3, 0.4, 0.5}
    assert all((c["mean_sec_proven"] is None) == (c["proven"] == 0) and c["mean_sec_proven"] is None or 0 <= c["mean_sec_proven"] <= c["max_sec_proven"] <= c["seconds_limit"] for c in ec)
    assert all(c["ils_equals_optimum"] <= c["proven"] for c in ec)


def test_exact_offered_rule():
    for n in (15, 25):                                                                     # bis EXACT_N_MAX immer
        for k in (1, 4):
            assert R.exact_offered(n, k, 0.65, "lognormal") == (True, None)
    offered = {(c["n"], c["K"], c["f"]) for c in R.exact_offered_cells()}
    assert offered == {(40, 3, 0.3), (40, 4, 0.3), (40, 4, 0.4)}                          # Beweisanteil mindestens 80 %
    for c in R.load()["exact_cells"]:
        ok, cell = R.exact_offered(c["n"], c["K"], c["f"], c["ptype"])
        assert cell is c and ok == (c["proven"] / c["n_inst"] >= C.EXACT_MIN_PROOF_SHARE)
        assert R.exact_offered(c["n"], c["K"], c["f"], "fern") == (False, None)            # nur mit gestreuten Prämien gemessen
    assert R.exact_offered(60, 4, 0.3, "lognormal") == (False, None)                       # nicht gemessen: nicht angeboten
    assert R.exact_offered(40, 4, 0.2, "lognormal") == (False, None)                       # Budgetanteil 0,2 nicht gemessen
    # genau auf der Schwelle: 24 von 30 = 80 % wird angeboten, 23 von 30 nicht
    assert 24 / 30 >= C.EXACT_MIN_PROOF_SHARE > 23 / 30


def test_neighbour_cell_never_changes_the_prize_type():
    for ptype in C.PTYPE_OPTIONS:
        for n in C.N_OPTIONS:
            for k in range(C.K_MIN, C.K_MAX + 1):
                for f in C.F_OPTIONS:
                    cell, exact = R.nearest_cell(n, k, f, ptype)
                    assert cell["ptype"] == ptype, (n, k, f, ptype)
                    assert exact == ((cell["n"], cell["K"], cell["f"]) == (n, k, f))


def test_neighbour_cell_by_hand():
    cell, exact = R.nearest_cell(25, 3, 0.5, "lognormal")      # K = 3 nur bei n = 40: aber (25, 2, 0.5) liegt näher als (40, 3, 0.4)
    assert not exact and (cell["n"], cell["K"], cell["f"]) == (25, 2, 0.5)
    cell, exact = R.nearest_cell(15, 2, 0.4, "lognormal")
    assert exact and cell["n"] == 15


def test_budget_curve_and_ablation_lookup():
    curve = R.budget_curve(25, 2, "lognormal")
    assert [c["f"] for c in curve] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.7, 0.8, 1.0]
    assert R.ablation_cell(25, 2, 0.4, "lognormal")["A_gleiche_Menge"] == 30
    with pytest.raises(KeyError):
        R.ablation_cell(99, 1, 0.1, "gleich")


def test_number_formats():
    assert R.pm([4.2056, 0.854]) == "+4,2 ± 0,9" and R.pm([-1.04, 0.2], sign=True) == "-1,0 ± 0,2" and R.pm([4.2, 0.9], sign=False) == "4,2 ± 0,9"
    assert R.num(0.65, 2) == "0,65" and R.num(3.0, 0) == "3" and R.num(2.5, 1, True) == "+2,5"


def test_results_agree_with_the_published_headline_numbers():
    """Die Zahlen, die README und App nennen: Standardzelle, Wiederholung mit abgestimmtem OR-Tools, K = 1-Optimum."""
    data = R.load()
    base = next(c for c in data["cells"] if (c["n"], c["K"], c["f"], c["ptype"]) == (25, 2, 0.5, "lognormal"))
    assert round(base["share"]["G_ratio"], 1) == 92.7 and round(base["share"]["ILS"], 1) == 99.9 and round(base["share"]["GLS"], 1) == 95.7
    assert round(base["share"]["GLS_t"], 1) == 98.5 and base["proven"] == 3
    k1 = data["k1_exact"]
    assert k1["n_inst"] == 20 and k1["below"] == {"G_ratio": 16, "G_LS": 14, "GLS": 17, "ILS": 0} and round(k1["GLS"], 1) == 87.6
    assert sum(c["tuned_over_ils"] or 0 for c in data["cells"]) == 1      # in 1 von 840 Instanzen war OR-Tools (abgestimmt, zeitgleich) besser


def test_ils_budget_measurement_is_present_for_every_size():
    budget = R.ils_budget()
    assert set(budget) == {str(n) for n in C.N_OPTIONS}
    for n in C.N_OPTIONS:
        assert set(budget[str(n)]) == {"300", "1000", "3000", "n_inst"} and budget[str(n)]["300"]["share"] >= 99.0


def test_dump_tool_and_data_file_are_consistent():
    """Das Werkzeug erzeugt genau die Schlüssel, die die App liest."""
    data = json.loads((ROOT / "data" / "gwt_results.json").read_text(encoding="utf-8"))
    assert set(data) == {"meta", "cells", "exact_cells", "ablation", "k1_exact", "ils_variants", "convergence", "tuning"}
    assert all({"n", "K", "f", "ptype", "share", "gap_std"} <= set(c) for c in data["cells"])
