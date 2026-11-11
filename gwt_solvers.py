"""OR-Tools (Routing, zwei Einstellungen) und CP-SAT (exakt, mit Schranke). Importe erst beim Aufruf: die Demo laeuft ohne OR-Tools bis auf diese Knoepfe."""
from __future__ import annotations

import time

from gwt_algorithm import greedy_ratio
from gwt_scenario import Inst


# ----- OR-Tools Routing --------------------------------------------------------------------------------------------------
EXTRA_OPS = ["use_extended_swap_active", "use_relocate_and_make_active", "use_exchange_and_make_active", "use_inactive_lns",
             "use_path_lns", "use_full_path_lns", "use_tsp_lns", "use_cross_exchange", "use_relocate_neighbors"]


def solve_ortools(inst: Inst, seconds: float = 5.0, tuned: bool = False):
    """Routing mit Disjunktionsstrafen. Standard: Guided Local Search, PATH_CHEAPEST_ARC, Strafe 1000 x Praemie.
    Abgestimmt (auf getrennten Instanzen gewaehlt): Tabu-Suche, Warmstart aus dem Verhaeltnis-Greedy, neun zusaetzliche Operatoren,
    Strafe 3 x 60 x Praemie / mittlere Praemie (unabhaengig von der Praemieneinheit)."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    from ortools.util import optional_boolean_pb2

    n, K, T, s = inst.n, inst.K, inst.T, inst.serv
    mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0)
    rt = pywrapcp.RoutingModel(mgr)
    cb = rt.RegisterTransitCallback(lambda i, j: T[mgr.IndexToNode(i)][mgr.IndexToNode(j)] + (s if mgr.IndexToNode(i) else 0))
    rt.SetArcCostEvaluatorOfAllVehicles(cb)
    rt.AddDimension(cb, 0, inst.tmax, True, "Zeit")
    mean_prize = sum(inst.prize[1:]) / max(1, n)
    for j in range(1, n + 1):
        pen = round(inst.prize[j] * 3 * 60 / mean_prize) if tuned else inst.prize[j] * 1000
        rt.AddDisjunction([mgr.NodeToIndex(j)], max(1, pen))
    sp = pywrapcp.DefaultRoutingSearchParameters()
    sp.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    sp.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH if tuned
                                    else routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    if tuned:
        for name in EXTRA_OPS:
            setattr(sp.local_search_operators, name, optional_boolean_pb2.BOOL_TRUE)
    sp.time_limit.FromMilliseconds(int(seconds * 1000))
    sol = None
    if tuned:
        rt.CloseModelWithParameters(sp)
        start = greedy_ratio(inst)
        assignment = rt.ReadAssignmentFromRoutes([[mgr.NodeToIndex(x) for x in r] for r in start], True)
        if assignment is not None:
            sol = rt.SolveFromAssignmentWithParameters(assignment, sp)
    if sol is None:
        sol = rt.SolveWithParameters(sp)
    if sol is None:
        return [[] for _ in range(K)]
    routes = []
    for v in range(K):
        idx, r = rt.Start(v), []
        while not rt.IsEnd(idx):
            if mgr.IndexToNode(idx):
                r.append(mgr.IndexToNode(idx))
            idx = sol.Value(rt.NextVar(idx))
        routes.append(r)
    return routes


# ----- CP-SAT -------------------------------------------------------------------------------------------------------------
def solve_cpsat(inst: Inst, seconds: float = 20.0, workers: int = 1, hint=None, seed: int = 0):
    from ortools.sat.python import cp_model
    n, K, T, s, tmax, P = inst.n, inst.K, inst.T, inst.serv, inst.tmax, inst.prize
    m = cp_model.CpModel()
    arcs, lit, skip = [], {}, {}
    ok = {j: T[0][j] + s + T[j][0] <= tmax for j in range(1, n + 1)}
    if not any(ok.values()):  # kein Kunde einzeln erreichbar: leere Loesung ist optimal (Modell ohne Depotbogen ist ungueltig)
        return {"status": "OPTIMAL", "obj": 0, "bound": 0.0, "routes": [], "sec": 0.0}
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                continue
            if (i and not ok[i]) or (j and not ok[j]):
                continue
            if i and j and T[0][i] + s + T[i][j] + s + T[j][0] > tmax:
                continue
            b = m.NewBoolVar(f"a{i}_{j}")
            lit[i, j] = b
            arcs.append((i, j, b))
    for j in range(1, n + 1):
        sk = m.NewBoolVar(f"s{j}")
        skip[j] = sk
        arcs.append((j, j, sk))
        if not ok[j]:
            m.Add(sk == 1)
    m.add_multiple_circuit(arcs)
    dep = [lit[0, j] for j in range(1, n + 1) if (0, j) in lit]
    if dep:  # ohne Depotbogen waere die Summe ein Python-Bool (MODEL_INVALID)
        m.Add(sum(dep) <= K)
    L = {j: m.NewIntVar(T[0][j] + s, tmax, f"L{j}") for j in range(1, n + 1) if ok[j]}
    for (i, j), b in lit.items():
        if i == 0:
            continue
        if j == 0:
            m.Add(L[i] + T[i][0] <= tmax).OnlyEnforceIf(b)
        else:
            m.Add(L[j] >= L[i] + T[i][j] + s).OnlyEnforceIf(b)
    m.Maximize(sum(P[j] * (1 - skip[j]) for j in range(1, n + 1)))
    if hint is not None:
        used = set()
        vis = set()
        for r in hint:
            if not r:
                continue
            path = [0] + list(r) + [0]
            used.update(zip(path, path[1:]))
            vis.update(r)
        for (i, j), b in lit.items():
            m.AddHint(b, 1 if (i, j) in used else 0)
        for j in range(1, n + 1):
            m.AddHint(skip[j], 0 if j in vis else 1)
    sv = cp_model.CpSolver()
    sv.parameters.max_time_in_seconds = seconds
    sv.parameters.num_search_workers = workers
    sv.parameters.random_seed = seed
    t0 = time.time()
    st = sv.Solve(m)
    dt = time.time() - t0
    name = sv.StatusName(st)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": name, "obj": None, "bound": None, "routes": None, "sec": dt}
    nxt = {i: j for (i, j), b in lit.items() if sv.Value(b) and i != 0}
    starts = [j for (i, j), b in lit.items() if i == 0 and sv.Value(b)]
    routes = []
    for st0 in starts:
        r, cur = [], st0
        while cur != 0:
            r.append(cur)
            cur = nxt[cur]
        routes.append(r)
    return {"status": name, "obj": int(round(sv.ObjectiveValue())), "bound": sv.BestObjectiveBound(),
            "routes": routes, "sec": dt}

