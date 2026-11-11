"""Instanz: Depot, Kunden mit Praemie, Fahrzeuge mit Zeitbudget; Bewertung und Zulaessigkeitspruefung.

Aus der Vorab-Messreihe (messreihe_gewinntouren/gewinntouren.py) uebernommen, Logik unveraendert; die Pruefungen der Messreihe
stehen in verkleinerter Form als tests/ im Repo."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


# ----- Instanz ----------------------------------------------------------------------------------------------------------
@dataclass
class Inst:
    n: int
    K: int
    tmax: int
    serv: int
    T: list          # (n+1) x (n+1) ganzzahlige Fahrzeiten
    prize: list      # Index 0 = Depot (0)
    xy: list
    f: float = 0.0
    ptype: str = ""
    seed: int = 0


def _ceil_t(d: float) -> int:
    return int(math.ceil(1.2 * d - 1e-9))


def tsp_length(T, nodes):
    """Rundreise ueber alle `nodes` (ohne Depot) ab Depot: Nearest Neighbour + 2-opt (nur zur Skalierung von tmax)."""
    left = set(nodes)
    tour = []
    cur = 0
    while left:
        nxt = min(left, key=lambda j: (T[cur][j], j))
        tour.append(nxt)
        left.remove(nxt)
        cur = nxt
    improved = True
    while improved:
        improved = False
        for i in range(len(tour) - 1):
            for j in range(i + 1, len(tour)):
                a = tour[i - 1] if i > 0 else 0
                b, c = tour[i], tour[j]
                d = tour[j + 1] if j + 1 < len(tour) else 0
                if T[a][c] + T[b][d] < T[a][b] + T[c][d]:
                    tour[i:j + 1] = reversed(tour[i:j + 1])
                    improved = True
    t = T[0][tour[0]] + T[tour[-1]][0] + sum(T[a][b] for a, b in zip(tour, tour[1:]))
    return t


def make_instance(n: int, K: int, seed: int, f: float, ptype: str = "lognormal", serv: int = 6) -> Inst:
    """Koordinaten und Praemien aus getrennten Stroemen: gleicher Seed => gleiche Orte in allen Praemienarten."""
    rxy = random.Random(seed * 3 + 1)
    rpr = random.Random(seed * 3 + 2)
    xy = [(50.0, 50.0)] + [(rxy.uniform(0, 100), rxy.uniform(0, 100)) for _ in range(n)]
    T = [[_ceil_t(math.dist(a, b)) if a is not b else 0 for b in xy] for a in xy]
    prize = [0]
    mu = math.log(60) - 0.6 ** 2 / 2
    for j in range(1, n + 1):
        if ptype == "gleich":
            p = 10
        elif ptype == "lognormal":
            p = max(1, int(round(rpr.lognormvariate(mu, 0.6))))
        elif ptype == "fern":
            d = math.dist(xy[0], xy[j])
            p = max(1, int(round((20 + 1.2 * d) * rpr.lognormvariate(-0.02, 0.2))))
        else:
            raise ValueError(ptype)
        prize.append(p)
    full = tsp_length(T, range(1, n + 1)) + serv * n
    tmax = max(1, int(round(f * full / K)))
    return Inst(n, K, tmax, serv, T, prize, xy, f, ptype, seed)



# ----- Bewertung (unabhaengiger Weg) ----------------------------------------------------------------------------------
def route_time(inst: Inst, r) -> int:
    if not r:
        return 0
    path = [0] + list(r) + [0]
    return sum(inst.T[a][b] for a, b in zip(path, path[1:])) + inst.serv * len(r)


def validate(inst: Inst, routes):
    """Prueft Zulaessigkeit; gibt die Praemiensumme zurueck, sonst AssertionError."""
    routes = [list(r) for r in routes if r]
    assert len(routes) <= inst.K, "zu viele Touren"
    seen = set()
    for r in routes:
        for c in r:
            assert 1 <= c <= inst.n, "ungueltiger Kunde"
            assert c not in seen, "Kunde doppelt"
            seen.add(c)
        assert route_time(inst, r) <= inst.tmax, "Tour überschreitet das Zeitbudget"
    return sum(inst.prize[c] for c in seen)


def prize_of(inst: Inst, routes) -> int:
    return sum(inst.prize[c] for r in routes for c in r)


def total_time(inst: Inst, routes) -> int:
    return sum(route_time(inst, r) for r in routes)

