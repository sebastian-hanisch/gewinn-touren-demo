"""Laden und Auswerten der vorgerechneten Messreihe (data/gwt_results.json, erzeugt von tools/dump_results.py)."""

import json
import math
import pathlib
from functools import lru_cache

import gwt_constants as C

DATA = pathlib.Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def load():
    return json.loads((DATA / "gwt_results.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def ils_budget():
    return json.loads((DATA / "gwt_ils_budget.json").read_text(encoding="utf-8"))


def cell_distance(cell, n, k, f, ptype):
    """Abstand einer gemessenen Zelle zu den Reglerwerten; die Praemienart darf nie abweichen (Aufschlag 100)."""
    d = 0.0 if cell["ptype"] == ptype else 100.0
    d += 4.0 * abs(math.log(cell["n"] / n)) + abs(cell["K"] - k) + 5.0 * abs(cell["f"] - f)
    return d


def nearest_cell(n, k, f, ptype, cells=None):
    """Naechstliegende gemessene Zelle und ob sie genau den Reglerwerten entspricht. Bei Gleichstand gewinnt die Zelle mit mehr Instanzen."""
    cells = load()["cells"] if cells is None else cells
    best = min(cells, key=lambda c: (cell_distance(c, n, k, f, ptype), -c["n_inst"], c["n"], c["K"], c["f"]))
    exact = (best["n"], best["K"], best["f"], best["ptype"]) == (n, k, f, ptype)
    return best, exact


def exact_cell(n, k, f, ptype):
    """Gemessene Beweiszelle von CP-SAT (nur n > EXACT_N_MAX; nur genau die eingestellte Kombination, keine naechstliegende) oder None."""
    for c in load().get("exact_cells", []):
        if (c["n"], c["K"], c["f"], c["ptype"]) == (n, k, f, ptype):
            return c
    return None


def exact_offered(n, k, f, ptype):
    """(angeboten, Zelle): bis EXACT_N_MAX Kunden immer; darueber nur, wo die Messreihe in mindestens EXACT_MIN_PROOF_SHARE der Instanzen das Optimum bewies."""
    if n <= C.EXACT_N_MAX:
        return True, None
    cell = exact_cell(n, k, f, ptype)
    return (cell is not None and cell["proven"] / cell["n_inst"] >= C.EXACT_MIN_PROOF_SHARE), cell


def exact_offered_cells():
    """Die Beweiszellen, in denen der Knopf bei n > EXACT_N_MAX angeboten wird, nach (n, K, f) sortiert."""
    return sorted((c for c in load().get("exact_cells", []) if c["proven"] / c["n_inst"] >= C.EXACT_MIN_PROOF_SHARE), key=lambda c: (c["n"], c["K"], c["f"]))


def gap_greedy_ls(cell):
    """Rueckstand von Verhaeltnis-Greedy plus Lokalsuche zum besten bekannten Wert in Punkten (Anteil am Besten in %)."""
    return 100.0 - cell["share"]["G_LS"]


def zone(cell):
    """'A' Greedy reicht, 'B' Lokalsuche und ILS lohnen, 'C' die Auswahl entscheidet (Schwellen gesetzt, nicht hergeleitet)."""
    gap = gap_greedy_ls(cell)
    if gap <= C.GAP_GREEDY_REICHT:
        return "A"
    if gap <= C.GAP_AUSWAHL_ENTSCHEIDET:
        return "B"
    return "C"


def zone_counts():
    """Zahl der gemessenen Haupt-Sweep-Zellen je Zone (nur Zellen mit mindestens einer nicht leeren Instanz)."""
    out = {"A": 0, "B": 0, "C": 0}
    for c in load()["cells"]:
        if c["source"] == "main" and c["n_inst"] > 0:
            out[zone(c)] += 1
    return out


def budget_curve(n=25, k=2, ptype="lognormal"):
    """Zellen des Haupt-Sweeps fuer die Budget-Kurve, nach Budgetanteil sortiert."""
    return sorted((c for c in load()["cells"] if c["source"] == "main" and (c["n"], c["K"], c["ptype"]) == (n, k, ptype)), key=lambda c: c["f"])


def ablation_cell(n=25, k=2, f=0.4, ptype="lognormal"):
    for a in load()["ablation"]:
        if (a["n"], a["K"], a["f"], a["ptype"]) == (n, k, f, ptype):
            return a
    raise KeyError((n, k, f, ptype))


def pm(pair, digits=1, sign=True):
    """[Mittel, Standardfehler] als Text 'Mittel ± SE' mit Dezimalkomma."""
    mean, se = pair
    text = f"{mean:+.{digits}f}" if sign else f"{mean:.{digits}f}"
    return f"{text} ± {se:.{digits}f}".replace(".", ",")


def num(x, digits=1, sign=False):
    return (f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}").replace(".", ",")
