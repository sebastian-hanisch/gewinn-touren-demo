"""Orakel-Test gewinn-touren-demo: ein ANDERER Rechenweg als der der Demo (DEMO-PLAYBOOK §12, ORACLE-PLAYBOOK §2).

* Brute Force: Held-Karp je Teilmenge (kürzeste Tour) + Partitions-DP über höchstens K zulässige Mengen: das exakte Optimum für n <= 8.
* CP-SAT (nur wenn OR-Tools im Test-venv steht) muss dasselbe Optimum beweisen; kein Verfahren der Demo darf darüber liegen.
* Greedy (Verhältnis) gegen eine unabhängige Neuimplementierung mit Brüchen (Fraction), Wörterbüchern und eigenem Einfügeweg.
* Angezeigte Kennzahlen: Halteliste (Ankunftszeiten), Anteil am Besten, Zeitnutzung, Tourlänge der Skalierung (>= optimale Rundreise).
Vorher an der Handinstanz geprüft (Optimum 13, siehe conftest.py)."""

from fractions import Fraction

import pytest

import gwt_algorithm as A
import gwt_evaluation as E
import gwt_scenario as S


def held_karp(T, n):
    """dp[(Menge, letzter Kunde)] = kürzeste Fahrzeit ab Depot über genau diese Menge (Kunden 0..n-1 entsprechen 1..n)."""
    dp = {(1 << j, j): T[0][j + 1] for j in range(n)}
    for mask in range(1, 1 << n):
        for last in range(n):
            v = dp.get((mask, last))
            if v is None:
                continue
            for nx in range(n):
                if not mask >> nx & 1:
                    key = (mask | 1 << nx, nx)
                    dp[key] = min(dp.get(key, 10 ** 9), v + T[last + 1][nx + 1])
    return dp


def brute_optimum(inst):
    n, T, s = inst.n, inst.T, inst.serv
    dp = held_karp(T, n)
    feasible, prize = {}, {}
    for mask in range(1, 1 << n):
        cnt = bin(mask).count("1")
        length = min(dp[(mask, l)] + T[l + 1][0] for l in range(n) if (mask, l) in dp) + s * cnt
        prize[mask] = sum(inst.prize[j + 1] for j in range(n) if mask >> j & 1)
        if length <= inst.tmax:
            feasible[mask] = length
    memo = {}

    def best(k, avail):
        if k == 0 or avail == 0:
            return 0
        if (k, avail) in memo:
            return memo[(k, avail)]
        res = best(k - 1, avail)
        sub = avail
        while sub:
            if sub in feasible:
                res = max(res, prize[sub] + best(k - 1, avail ^ sub))
            sub = (sub - 1) & avail
        memo[(k, avail)] = res
        return res

    return best(inst.K, (1 << n) - 1)


def greedy_reference(inst):
    tours = {v: [] for v in range(inst.K)}
    todo = set(range(1, inst.n + 1))

    def tt(r):
        path = [0, *r, 0]
        return sum(inst.T[x][y] for x, y in zip(path, path[1:])) + inst.serv * len(r)

    while True:
        best = None
        for c in sorted(todo):
            cand = None
            for v in range(inst.K):
                for p in range(len(tours[v]) + 1):
                    new = tours[v][:p] + [c] + tours[v][p:]
                    if tt(new) <= inst.tmax:
                        d = tt(new) - tt(tours[v])
                        if cand is None or d < cand[0]:
                            cand = (d, v, p)
            if cand is not None:
                ratio = Fraction(inst.prize[c], cand[0])
                if best is None or ratio > best[0]:
                    best = (ratio, c, cand)
        if best is None:
            break
        _, c, (d, v, p) = best
        tours[v].insert(p, c)
        todo.remove(c)
    return [tours[v] for v in range(inst.K)]


def _tiny(seed):
    return S.make_instance(7, 1 + seed % 3, 100 + seed, [0.25, 0.5, 0.8][seed % 3], ["gleich", "lognormal", "fern"][(seed // 3) % 3])


def test_oracle_on_the_hand_instance(hand):
    assert brute_optimum(hand) == 13


def test_no_method_exceeds_the_brute_force_optimum():
    for seed in range(16):
        inst = _tiny(seed)
        opt = brute_optimum(inst)
        r0 = A.greedy_ratio(inst)
        for routes in (r0, A.greedy_prize(inst), A.local_search(inst, r0), A.ils(inst, r0, 150, seed)):
            assert S.validate(inst, routes) <= opt, seed


def test_cpsat_proves_the_brute_force_optimum():
    pytest.importorskip("ortools")
    import gwt_solvers as V
    for seed in range(8):
        inst = _tiny(seed)
        res = V.solve_cpsat(inst, 30, 1)
        assert res["status"] == "OPTIMAL" and res["obj"] == brute_optimum(inst), seed
        assert S.validate(inst, res["routes"]) == res["obj"]


def test_cpsat_with_hint_never_returns_less_than_the_hint():
    pytest.importorskip("ortools")
    import gwt_solvers as V
    inst = S.make_instance(15, 2, 4, 0.4, "lognormal")
    hint = A.ils(inst, A.greedy_ratio(inst), 100, 4)
    res = V.solve_cpsat(inst, 10, 1, hint=hint)
    assert res["obj"] is not None and res["obj"] >= S.prize_of(inst, hint)


def test_ortools_plans_are_valid_in_both_settings():
    pytest.importorskip("ortools")
    import gwt_solvers as V
    inst = S.make_instance(15, 2, 4, 0.5, "lognormal")
    for tuned in (False, True):
        assert S.validate(inst, V.solve_ortools(inst, 1.0, tuned=tuned)) >= 0


def test_penalty_scale_is_independent_of_the_prize_unit():
    """Die abgestimmte Strafe ist 3 x 60 x Prämie / mittlere Prämie: im Mittel 180 je Kunde, egal ob die Prämien um 10 oder um 60 liegen."""
    for ptype in ("gleich", "lognormal", "fern"):
        inst = S.make_instance(25, 2, 3, 0.4, ptype)
        mean = sum(inst.prize[1:]) / inst.n
        pens = [round(inst.prize[j] * 3 * 60 / mean) for j in range(1, inst.n + 1)]
        assert abs(sum(pens) / inst.n - 180) < 1.0, ptype


def test_greedy_matches_an_independent_reimplementation():
    for seed in range(20):
        inst = S.make_instance(12, 1 + seed % 3, 400 + seed, [0.25, 0.5, 0.8][seed % 3], ["gleich", "lognormal", "fern"][(seed // 3) % 3])
        assert A.greedy_ratio(inst) == greedy_reference(inst), seed


def test_schedule_matches_route_time():
    for seed in range(10):
        inst = S.make_instance(25, 2, 500 + seed, 0.5, "lognormal")
        for route in A.local_search(inst, A.greedy_ratio(inst)):
            if not route:
                continue
            sched = E.schedule(inst, route)
            last, arrival, _ = sched[-1]
            assert arrival + inst.serv + inst.T[last][0] == S.route_time(inst, route)
            assert [c for c, _, _ in sched] == route and all(p == inst.prize[c] for c, _, p in sched)


def test_displayed_figures_by_hand():
    a = E.analyse(E.Settings(15, 1, 0.5, "lognormal", 300, 1))
    assert E.share(50, 100) == 50.0 and E.share(0, 0) == 100.0
    greedy = E.step_of(a, "G_ratio")
    assert E.budget_use_percent(a, greedy) == pytest.approx(100.0 * greedy.minutes / (a.inst.K * a.inst.tmax))
    assert E.minus_percent(1.94) == "−1,9 %" and E.minus_percent(0.0) == "±0,0 %"


def test_budget_scale_is_at_least_the_optimal_tour():
    """tmax skaliert mit der Nearest-Neighbour-plus-2-opt-Rundreise: sie darf nie kürzer sein als die optimale Rundreise (Held-Karp)."""
    for seed in range(8):
        inst = S.make_instance(8, 1, 600 + seed, 1.0, "gleich")
        n, T = inst.n, inst.T
        dp = held_karp(T, n)
        optimum = min(dp[((1 << n) - 1, l)] + T[l + 1][0] for l in range(n))
        tour = S.tsp_length(T, range(1, n + 1))
        assert tour >= optimum
        assert inst.tmax == round(1.0 * (tour + inst.serv * n) / 1)
