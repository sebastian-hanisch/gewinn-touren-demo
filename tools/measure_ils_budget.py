"""Guete und Zeit des ILS bei 300 / 1000 / 3000 Iterationen (n = 15, 25, 40, 60; K = 2, Budgetanteil 0,5, gestreute Praemien; Seeds 0..9).
Anteil = Praemie / beste Praemie der drei Laeufe der Instanz. Schreibt data/gwt_ils_budget.json (Live-Voreinstellung der App)."""
import json
import pathlib
import sys
import time
from multiprocessing import Pool
from statistics import mean

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import gwt_algorithm as A  # noqa: E402
import gwt_scenario as S  # noqa: E402

BUDGETS = (300, 1000, 3000)


def one(args):
    n, seed = args
    inst = S.make_instance(n, 2, seed, 0.5, "lognormal")
    r0 = A.greedy_ratio(inst)
    out = {"n": n, "seed": seed}
    for it in BUDGETS:
        t0 = time.time()
        routes = A.ils(inst, r0, it, seed)
        out[it] = (S.validate(inst, routes), time.time() - t0)
    return out


if __name__ == "__main__":
    jobs = [(n, s) for n in (15, 25, 40, 60) for s in range(10)]
    with Pool(8) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    res = {}
    for n in (15, 25, 40, 60):
        rs = [r for r in rows if r["n"] == n]
        best = [max(r[it][0] for it in BUDGETS) for r in rs]
        res[str(n)] = {str(it): {"share": mean(100 * r[it][0] / b for r, b in zip(rs, best)), "sec": mean(r[it][1] for r in rs),
                                 "below_best": sum(r[it][0] < b for r, b in zip(rs, best)),
                                 "worst_share": min(100 * r[it][0] / b for r, b in zip(rs, best))} for it in BUDGETS}
        res[str(n)]["n_inst"] = len(rs)
    (HERE / "data" / "gwt_ils_budget.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for n, v in res.items():
        print(n, {k: (round(x["share"], 2), round(x["sec"], 2), x["below_best"]) for k, x in v.items() if k != "n_inst"})
