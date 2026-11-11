"""Live-Analyse einer Instanz (Verfahrenstreppe), Kennzahlen und Verdikte als reine Funktionen: verdict_*(...) -> (Art, Text)."""

import time
from dataclasses import dataclass

import gwt_algorithm as A
import gwt_constants as C
import gwt_results as R
import gwt_scenario as S


@dataclass(frozen=True)
class Settings:
    n: int = C.DEFAULT_N
    k: int = C.DEFAULT_K
    f: float = C.DEFAULT_F
    ptype: str = C.DEFAULT_PTYPE
    ils: int = C.DEFAULT_ILS
    seed: int = C.DEFAULT_SEED


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    routes: tuple      # Tuple von Tuples (hashbar fuer den Cache)
    prize: int
    served: int
    minutes: int       # Gesamtfahrzeit aller Touren
    seconds: float     # Rechenzeit dieses Schritts auf diesem Rechner


@dataclass(frozen=True)
class Analysis:
    inst: S.Inst
    steps: tuple
    best: int          # beste Praemie der Treppe


STEP_LABELS = {
    "G_prize": "Höchste Prämie zuerst",
    "G_ratio": "Verhältnis-Greedy",
    "A_route": "+ Routenzüge",
    "B_insert": "+ Einfügen",
    "C_replace": "+ Ersetzen",
    "E_ils_ohne": "ILS ohne Ersetzen",
    "D_ils": "ILS voll",
}


def _freeze(routes):
    return tuple(tuple(r) for r in routes)


def _step(inst, key, fn):
    t0 = time.perf_counter()
    routes = fn()
    dt = time.perf_counter() - t0
    return Step(key, STEP_LABELS[key], _freeze(routes), S.validate(inst, routes), sum(len(r) for r in routes), S.total_time(inst, routes), dt)


def analyse(settings: Settings) -> Analysis:
    """Die Treppe der Verfahren auf einer Instanz: alles live, deterministisch bei gleichem Seed und gleicher Iterationszahl."""
    inst = S.make_instance(settings.n, settings.k, settings.seed, settings.f, settings.ptype, C.SERVICE_MIN)
    steps = []
    g_ratio = A.greedy_ratio(inst)
    steps.append(_step(inst, "G_prize", lambda: A.greedy_prize(inst)))
    steps.append(_step(inst, "G_ratio", lambda: g_ratio))
    steps.append(_step(inst, "A_route", lambda: A.local_search(inst, g_ratio, A.ROUTE_MOVES)))
    steps.append(_step(inst, "B_insert", lambda: A.local_search(inst, g_ratio, A.ROUTE_INSERT)))
    steps.append(_step(inst, "C_replace", lambda: A.local_search(inst, g_ratio, A.ALL_MOVES)))
    steps.append(_step(inst, "E_ils_ohne", lambda: A.ils(inst, g_ratio, settings.ils, settings.seed, A.ROUTE_INSERT)))
    steps.append(_step(inst, "D_ils", lambda: A.ils(inst, g_ratio, settings.ils, settings.seed)))
    return Analysis(inst, tuple(steps), max(s.prize for s in steps))


def step_of(a: Analysis, key: str) -> Step:
    return next(s for s in a.steps if s.key == key)


def share(prize: int, best: int) -> float:
    """Anteil am besten bekannten Wert in Prozent; ohne erreichbaren Kunden (bester Wert 0) gibt es nichts zu vergleichen."""
    return 100.0 if best <= 0 else 100.0 * prize / best


def best_known(a: Analysis, *extra_prizes: int) -> int:
    return max([a.best, *extra_prizes])


def time_saved_percent(a: Analysis) -> float:
    """Fahrzeit, die die reinen Routenzuege gegenueber dem Greedy sparen (Prozent der Greedy-Fahrzeit)."""
    g, r = step_of(a, "G_ratio"), step_of(a, "A_route")
    return 0.0 if g.minutes <= 0 else 100.0 * (g.minutes - r.minutes) / g.minutes


def minus_percent(saved: float) -> str:
    """Eingesparter Anteil als Text mit echtem Minuszeichen ('−1,9 %'); ohne Ersparnis '±0,0 %'."""
    return f"−{R.num(saved)} %" if saved > 0 else "±0,0 %"


def budget_use_percent(a: Analysis, step: Step) -> float:
    return 100.0 * step.minutes / (a.inst.K * a.inst.tmax) if a.inst.tmax > 0 else 0.0


# --- Verdikte (rein: die App ruft st.<Art>(Text), der Test prueft jede Zahl im Text) ------------------------------------------------------

def verdict_regime(cell, exact: bool) -> tuple[str, str]:
    """Kernfrage 'Wann reicht welches Verfahren?', aus der gemessenen Zelle (nicht aus der einen Instanz)."""
    gap = R.gap_greedy_ls(cell)
    z = R.zone(cell)
    where = (f"n = {cell['n']}, {cell['K']} Fahrzeuge, Budgetanteil {R.num(cell['f'], 2 if cell['f'] == 0.65 else 1)}, "
             f"{C.PTYPE_WORDS[cell['ptype']]}, {cell['n_inst']} Instanzen")
    note = "" if exact else " Die eingestellte Kombination ist nicht gemessen; hier steht die nächstliegende gemessene Zelle."
    base = (f"In der Messreihe ({where}) liegt Verhältnis-Greedy plus Lokalsuche im Mittel **{R.num(gap)} Punkte** hinter dem besten bekannten Wert.")
    ils = f" Die eigene Suche (ILS) liegt dort im Mittel bei {R.num(cell['share']['ILS'])} % des besten bekannten Werts."
    if z == "A":
        return "success", base + (f" Das sind höchstens {R.num(C.GAP_GREEDY_REICHT, 0)} Punkte (gesetzte Schwelle): Greedy mit Lokalsuche genügt hier "
                                  f"im Mittel.{ils}{note}")
    if z == "B":
        return "info", base + (f" Das liegt zwischen {R.num(C.GAP_GREEDY_REICHT, 0)} und {R.num(C.GAP_AUSWAHL_ENTSCHEIDET, 0)} Punkten "
                               f"(gesetzte Schwellen): Suche lohnt.{ils}{note}")
    return "warning", base + (f" Das sind mehr als {R.num(C.GAP_AUSWAHL_ENTSCHEIDET, 0)} Punkte (gesetzte Schwelle): hier lässt Greedy mit Lokalsuche viel liegen.{ils}{note}")


def verdict_stairs(a: Analysis) -> tuple[str, str]:
    """Zahlen der Treppe auf DIESER Instanz (eine Instanz, kein Beleg)."""
    g, r, b, c = (step_of(a, k) for k in ("G_ratio", "A_route", "B_insert", "C_replace"))
    e, d = step_of(a, "E_ils_ohne"), step_of(a, "D_ils")
    same = {x for rt in g.routes for x in rt} == {x for rt in r.routes for x in rt}
    return "info", (
        f"Auf dieser Instanz: Verhältnis-Greedy {g.prize} Prämie mit {g.served} Kunden. Routenzüge allein: {r.prize} "
        f"({'gleiche Kunden' if same else 'andere Kunden'}, Fahrzeit {minus_percent(time_saved_percent(a))}). "
        f"Mit Einfügen {b.prize}, mit Ersetzen {c.prize}. ILS ohne Ersetzen {e.prize}, ILS voll {d.prize}. "
        "Eine Instanz belegt nichts; die Messreihe unten zählt über 30 Instanzen je Zelle."
    )


def verdict_ortools(a: Analysis, std_prize: int, tuned_prize: int) -> tuple[str, str]:
    best = best_known(a, std_prize, tuned_prize)
    d = step_of(a, "D_ils").prize
    kind = "info"
    text = (f"OR-Tools (Standard) {std_prize}, OR-Tools (abgestimmt) {tuned_prize}, eigene Suche (ILS) {d} Prämie; bester bekannter Wert {best}. "
            f"Anteile am Besten: {R.num(share(std_prize, best))} %, {R.num(share(tuned_prize, best))} %, {R.num(share(d, best))} %. "
            "Eine Instanz, nicht die Messreihe.")
    return kind, text


def verdict_exact(a: Analysis, status: str, prize: int | None, bound: float | None) -> tuple[str, str]:
    d = step_of(a, "D_ils").prize
    if status == "OPTIMAL" and prize is not None:
        gap = share(d, prize)
        if d >= prize:
            return "success", f"Optimum bewiesen: {prize} Prämie. Die eigene Suche (ILS) erreicht {d}, also das Optimum."
        return "info", f"Optimum bewiesen: {prize} Prämie. Die eigene Suche (ILS) erreicht {d} ({R.num(gap)} % des Optimums)."
    if prize is None:
        return "warning", "CP-SAT hat im Zeitlimit keine Lösung gemeldet; das sagt nichts über das Optimum."
    bound_text = "" if bound is None else f" Die Schranke liegt bei {bound:.0f}; in der Messreihe liegt sie bei Budgetanteil 0,4 bis 0,65 um 42 bis 100 % über dem Besten und sagt dann über die Güte der Heuristiken wenig."
    return "warning", f"Optimum nicht bewiesen im Zeitlimit: beste gefundene Prämie {prize} (ILS {d}).{bound_text}"


def exact_unavailable_text(s: Settings) -> str:
    """Meldung im Exakt-Tab, wenn der Knopf nicht angeboten wird (s.n > EXACT_N_MAX und keine Beweiszelle mit genug Beweisen): sagt, was gemessen ist und was fehlt."""
    cells = R.load().get("exact_cells", [])
    share_pct = f"{R.num(100 * C.EXACT_MIN_PROOF_SHARE, 0)} %"
    offered = "; ".join(f"{c['n']} Kunden, {c['K']} Fahrzeuge, Budgetanteil {R.num(c['f'])}" for c in R.exact_offered_cells())
    cell = R.exact_cell(s.n, s.k, s.f, s.ptype)
    if cell is not None:
        head = (f"Bei {s.n} Kunden, {s.k} Fahrzeugen, Budgetanteil {R.num(s.f)} und gestreuten Prämien bewies CP-SAT in der Messreihe in {cell['proven']} von {cell['n_inst']} Instanzen das Optimum "
                f"(höchstens {R.num(cell['seconds_limit'], 0)} s, ein Worker, Warmstart aus der eigenen Suche); der Knopf wird erst ab {share_pct} angeboten.")
    else:
        ns = sorted({c["n"] for c in cells})
        ks = sorted({c["K"] for c in cells})
        fs = sorted({c["f"] for c in cells})
        head = (f"Bei dieser Kombination ({s.n} Kunden, {s.k} Fahrzeuge, Budgetanteil {R.num(s.f)}, {C.PTYPE_WORDS[s.ptype]}) ist nicht gemessen, ob CP-SAT das Optimum beweist: "
                f"gemessen sind {' und '.join(str(n) for n in ns)} Kunden mit {ks[0]} bis {ks[-1]} Fahrzeugen bei Budgetanteil {' / '.join(R.num(f) for f in fs)} und gestreuten Prämien "
                "(bei 25 Kunden ab Budgetanteil 0,5 beweist CP-SAT kaum noch ein Optimum; 60 Kunden wurden nicht versucht).")
    return (f"{head} Angeboten wird der Knopf ab {C.EXACT_N_MAX + 1} Kunden nur, wo es in mindestens {share_pct} der Instanzen bewies: {offered}. "
            "Siehe Kernfrage 3 und Tab Messreihe.")


def schedule(inst: S.Inst, route) -> list[tuple[int, int, int]]:
    """Halteliste einer Tour: (Kunde, Ankunft in Minuten nach Start, Prämie). Service wird nach der Ankunft verbraucht."""
    out, t, prev = [], 0, 0
    for c in route:
        t += inst.T[prev][c]
        out.append((c, t, inst.prize[c]))
        t += inst.serv
        prev = c
    return out
