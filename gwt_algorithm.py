"""Kern: Konstruktion (Verhaeltnis-Greedy, Praemie zuerst), Lokalsuche mit Zugart-Schaltern und Iterated Local Search.

Aus der Vorab-Messreihe (messreihe_gewinntouren/gewinntouren.py) uebernommen, Logik unveraendert."""
from __future__ import annotations

import random

from gwt_scenario import Inst, prize_of, route_time, total_time


# ----- Einfuegen ---------------------------------------------------------------------------------------------------------
def _cheapest_insertion(inst, routes, rts, c):
    """Guenstigste zulaessige Einfuegeposition von c: (delta, route, pos) oder None."""
    T, s, tmax = inst.T, inst.serv, inst.tmax
    best = None
    for ri, r in enumerate(routes):
        if not r:
            d = T[0][c] + T[c][0] + s
            if d <= tmax and (best is None or d < best[0]):
                best = (d, ri, 0)
            continue
        L = len(r)
        for p in range(L + 1):
            a = r[p - 1] if p > 0 else 0
            b = r[p] if p < L else 0
            d = T[a][c] + T[c][b] - T[a][b] + s
            if rts[ri] + d <= tmax and (best is None or d < best[0]):
                best = (d, ri, p)
    return best


def greedy_ratio(inst: Inst, noise_rng=None, forbidden=(), routes=None, noise=(0.7, 1.3)):
    """Wiederholt den Kunden mit dem groessten Verhaeltnis Praemie / Zusatzzeit einfuegen (an der guenstigsten Stelle)."""
    routes = [list(r) for r in routes] if routes is not None else [[] for _ in range(inst.K)]
    rts = [route_time(inst, r) for r in routes]
    visited = {c for r in routes for c in r}
    cand = [c for c in range(1, inst.n + 1) if c not in visited and c not in forbidden]
    while cand:
        best = None
        for c in cand:
            ins = _cheapest_insertion(inst, routes, rts, c)
            if ins is None:
                continue
            ratio = inst.prize[c] / ins[0]
            if noise_rng is not None:
                ratio *= noise_rng.uniform(*noise)
            if best is None or ratio > best[0]:
                best = (ratio, c, ins)
        if best is None:
            break
        _, c, (d, ri, p) = best
        routes[ri].insert(p, c)
        rts[ri] += d
        cand.remove(c)
    return routes


def greedy_prize(inst: Inst):
    """Hoechste Praemie zuerst, jeweils an der guenstigsten zulaessigen Stelle (einmaliger Durchgang)."""
    routes = [[] for _ in range(inst.K)]
    rts = [0] * inst.K
    for c in sorted(range(1, inst.n + 1), key=lambda j: (-inst.prize[j], j)):
        ins = _cheapest_insertion(inst, routes, rts, c)
        if ins is None:
            continue
        d, ri, p = ins
        routes[ri].insert(p, c)
        rts[ri] += d
    return routes



# ----- Lokalsuche --------------------------------------------------------------------------------------------------------
ALL_MOVES = frozenset({"two_opt", "relocate", "swap", "insert", "replace"})
ROUTE_MOVES = frozenset({"two_opt", "relocate", "swap"})           # aendern nur die Routen, nie die Kundenmenge
ROUTE_INSERT = ROUTE_MOVES | {"insert"}                            # dazu: freie Zeit fuellen
# Ersetzen (bedienten gegen unbedienten Kunden tauschen) ist der Auswahlzug im engeren Sinn.


def local_search(inst: Inst, routes, moves=ALL_MOVES):
    """Lexikographisch (Praemie hoch, Gesamtzeit niedrig). Zuege: 2-opt, Verschieben, Tauschen, Einfuegen, Ersetzen."""
    T, s, tmax, P = inst.T, inst.serv, inst.tmax, inst.prize
    routes = [list(r) for r in routes]
    rts = [route_time(inst, r) for r in routes]
    K = len(routes)

    def two_opt():
        for ri, r in enumerate(routes):
            L = len(r)
            for i in range(L - 1):
                for j in range(i + 1, L):
                    a = r[i - 1] if i > 0 else 0
                    b, c = r[i], r[j]
                    d = r[j + 1] if j + 1 < L else 0
                    delta = T[a][c] + T[b][d] - T[a][b] - T[c][d]
                    if delta < 0:
                        r[i:j + 1] = reversed(r[i:j + 1])
                        rts[ri] += delta
                        return True
        return False

    def relocate():
        for A in range(K):
            ra = routes[A]
            for i, c in enumerate(ra):
                a = ra[i - 1] if i > 0 else 0
                b = ra[i + 1] if i + 1 < len(ra) else 0
                rem = T[a][c] + T[c][b] - T[a][b] + s
                if len(ra) == 1:
                    rem = T[0][c] + T[c][0] + s
                ra2 = ra[:i] + ra[i + 1:]
                for B in range(K):
                    rb = ra2 if B == A else routes[B]
                    for p in range(len(rb) + 1):
                        if B == A and p == i:
                            continue
                        x = rb[p - 1] if p > 0 else 0
                        y = rb[p] if p < len(rb) else 0
                        add = T[x][c] + T[c][y] - T[x][y] + s
                        if add >= rem:
                            continue
                        if B != A and rts[B] + add > tmax:
                            continue
                        if B == A:
                            ra[:] = ra2[:p] + [c] + ra2[p:]
                            rts[A] += add - rem
                        else:
                            ra[:] = ra2
                            routes[B].insert(p, c)
                            rts[A] -= rem
                            rts[B] += add
                        return True
        return False

    def swap():
        for A in range(K):
            for B in range(A + 1, K):
                ra, rb = routes[A], routes[B]
                for i, u in enumerate(ra):
                    a = ra[i - 1] if i > 0 else 0
                    b = ra[i + 1] if i + 1 < len(ra) else 0
                    for j, v in enumerate(rb):
                        x = rb[j - 1] if j > 0 else 0
                        y = rb[j + 1] if j + 1 < len(rb) else 0
                        dA = T[a][v] + T[v][b] - T[a][u] - T[u][b]
                        dB = T[x][u] + T[u][y] - T[x][v] - T[v][y]
                        if dA + dB < 0 and rts[A] + dA <= tmax and rts[B] + dB <= tmax:
                            ra[i], rb[j] = v, u
                            rts[A] += dA
                            rts[B] += dB
                            return True
        return False

    def insert_unvisited():
        vis = {c for r in routes for c in r}
        best = None
        for c in range(1, inst.n + 1):
            if c in vis:
                continue
            ins = _cheapest_insertion(inst, routes, rts, c)
            if ins is None:
                continue
            ratio = P[c] / ins[0]
            if best is None or ratio > best[0]:
                best = (ratio, c, ins)
        if best is None:
            return False
        _, c, (d, ri, p) = best
        routes[ri].insert(p, c)
        rts[ri] += d
        return True

    def replace():
        vis = {c for r in routes for c in r}
        unv = [c for c in range(1, inst.n + 1) if c not in vis]
        best = None
        for A in range(K):
            ra = routes[A]
            for i, v in enumerate(ra):
                cands = [u for u in unv if P[u] > P[v]]
                if not cands:
                    continue
                rem_routes = routes[:A] + [ra[:i] + ra[i + 1:]] + routes[A + 1:]
                rem_rts = rts[:]
                rem_rts[A] = route_time(inst, rem_routes[A])
                for u in cands:
                    ins = _cheapest_insertion(inst, rem_routes, rem_rts, u)
                    if ins is None:
                        continue
                    gain = (P[u] - P[v], -(rem_rts[A] - rts[A] + ins[0]))
                    if best is None or gain > best[0]:
                        best = (gain, A, i, u, ins)
        if best is None:
            return False
        _, A, i, u, (d, ri, p) = best
        del routes[A][i]
        rts[A] = route_time(inst, routes[A])
        routes[ri].insert(p, u)
        rts[ri] = route_time(inst, routes[ri])
        return True

    while True:
        if (("two_opt" in moves and two_opt()) or ("relocate" in moves and relocate())
                or ("swap" in moves and swap())):
            continue
        if "insert" in moves and insert_unvisited():
            continue
        if "replace" in moves and replace():
            continue
        break
    return routes



# ----- ILS ---------------------------------------------------------------------------------------------------------------
def key_of(inst, routes):
    return (prize_of(inst, routes), -total_time(inst, routes))


def ils(inst: Inst, start, iters: int, seed: int = 0, moves=ALL_MOVES):
    """Iterated Local Search: Entfernen (zufaellig oder Segment) + verrauschtes Greedy-Einfuegen + Lokalsuche."""
    rng = random.Random(seed)
    cur = local_search(inst, start, moves)
    cur_key = key_of(inst, cur)
    best, best_key = [list(r) for r in cur], cur_key
    stale = 0
    for it in range(iters):
        cand = [list(r) for r in cur]
        vis = [(ri, i) for ri, r in enumerate(cand) for i in range(len(r))]
        if not vis:
            break
        m = rng.randint(2, max(2, min(6, len(vis) // 3 + 1)))
        removed = set()
        if rng.random() < 0.5:
            ri = rng.choice([x for x in range(len(cand)) if cand[x]])
            r = cand[ri]
            L = min(len(r), m)
            st = rng.randint(0, len(r) - L)
            removed.update(r[st:st + L])
            del r[st:st + L]
        else:
            for ri, i in rng.sample(vis, min(m, len(vis))):
                removed.add(cand[ri][i])
            for ri in range(len(cand)):
                cand[ri] = [c for c in cand[ri] if c not in removed]
        cand = greedy_ratio(inst, noise_rng=rng, forbidden=removed, routes=cand)
        cand = local_search(inst, cand, moves)
        k = key_of(inst, cand)
        if k >= cur_key:
            cur, cur_key = cand, k
        if k > best_key:
            best, best_key = [list(r) for r in cand], k
            stale = 0
        else:
            stale += 1
        if stale >= 60:
            cur, cur_key, stale = [list(r) for r in best], best_key, 0
    return best
