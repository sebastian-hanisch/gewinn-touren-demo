"""Verdichtet die Dateien der Vorab-Messreihe (messreihe_gewinntouren/ im Portfolio-Ordner) zu data/gwt_results.json.

    python tools/dump_results.py [Pfad zu messreihe_gewinntouren]

Gelesen werden sweep_data.json (Haupt-Sweep, OR-Tools Standard), sweep_data2.json (Ablation, n x K), sweep_data3.json (Wiederholung mit
abgestimmtem OR-Tools), raw_k1exact.json (Optimum K = 1, n = 20), raw_ilsexp.json (ILS-Varianten), raw_conv.jsonl (Konvergenz), raw_tune.json
(Abstimmung). Die App liest nur die erzeugte Datei; die Messreihe selbst gehoert nicht ins Repo (siehe README, Abschnitt Reproduktion)."""
import json
import pathlib
import sys
from statistics import mean

here = pathlib.Path(__file__).resolve().parent.parent
src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent / "tourenplanung-planung" / "messreihe_gewinntouren"


def load(name):
    return json.loads((src / name).read_text(encoding="utf-8"))


D1, D2, D3 = load("sweep_data.json"), load("sweep_data2.json"), load("sweep_data3.json")
K1 = load("raw_k1exact.json")
ILSX = load("raw_ilsexp.json")
TUNE = load("raw_tune.json")
CONV = [json.loads(line) for line in (src / "raw_conv.jsonl").read_text(encoding="utf-8").splitlines()]


def parse_key(key):
    """'(25, 2, 0.5, 'lognormal')' -> (25, 2, 0.5, 'lognormal')"""
    return eval(key, {}, {})  # nur eigene, vom Dump erzeugte Schluessel


def raw_counts():
    """je Zelle: Instanzen, in denen OR-Tools (Standard bzw. abgestimmt zeitgleich) strikt besser als der ILS ist, Gleichstaende (ILS = abgestimmt) und leere Instanzen"""
    out = {}
    for name in ("raw_main_t2.jsonl", "raw_nk_t.jsonl"):
        for line in (src / name).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            c = r["cell"]
            key = (c["n"], c["K"], c["f"], c["ptype"])
            res = r["res"]
            d = out.setdefault(key, {"std_over_ils": 0, "tuned_over_ils": 0, "tied_tuned": 0, "empty": 0})
            ils, std, tun = res["ILS"]["prize"], res["GLS"]["prize"], res["GLS_teq"]["prize"]
            if max(v["prize"] for v in res.values()) == 0:
                d["empty"] += 1
            d["std_over_ils"] += std > ils
            d["tuned_over_ils"] += tun > ils
            d["tied_tuned"] += tun == ils and ils > 0
    return out


RAW = raw_counts()
cells = []
for key, d in D1.items():
    n, K, f, pt = parse_key(key)
    if not d.get("share"):
        continue
    t = D3["main"].get(f"('{pt}', {n}, {K}, {f})")
    cells.append({
        "n": n, "K": K, "f": f, "ptype": pt, "source": "main", "n_inst": d["n_nonempty"], "n_total": d["n_total"], "proven": d["proven"],
        "share": {**{m: d["share"][m] for m in ("G_prize", "G_ratio", "G_LS", "ILS", "GLS")},
                  "GLS_t": t["GLS_teq"] if t else None},
        "gap_std": d["ils_minus_gls"], "gap_tuned": t["ILS-GLS_teq"] if t else None,
        "tuned_over_ils": t["teq_ueber_ILS"] if t else None, "counts": RAW[(n, K, f, pt)],
        "bound_gap_unproven": d["bound_gap_unproven"], "n_unproven": d["n_unproven"], "served_prize_pct": d["served_prize_pct"],
        "sec": {"ILS": d["sec"]["ILS"], "GLS_t": t["sec_teq"] if t else None, "CPSAT": d["sec"].get("CPSAT")},
    })
for key, d in D2["nk"].items():
    n, K = parse_key(key)
    t = D3["nk"][f"({n}, {K})"]
    cells.append({
        "n": n, "K": K, "f": 0.5, "ptype": "lognormal", "source": "nk", "n_inst": d["n_inst"], "n_total": 30, "proven": None,
        "share": {"G_prize": None, "G_ratio": d["G_ratio"], "G_LS": d["G_LS"], "ILS": d["ILS"], "GLS": d["GLS"], "GLS_t": t["GLS_teq"]},
        "gap_std": d["ILS_minus_GLS"], "gap_tuned": t["ILS-GLS_teq"], "tuned_over_ils": t["teq_ueber_ILS"], "counts": RAW[(n, K, 0.5, "lognormal")],
        "bound_gap_unproven": None, "n_unproven": None, "served_prize_pct": None, "kunden_je_tour": d["kunden_je_tour"],
        "sec": {"ILS": t["sec_ILS"], "GLS_t": t["sec_teq"], "CPSAT": None},
    })

ablation = []
for key, d in D2["ablation"].items():
    n, K, f, pt = parse_key(key)
    ablation.append({**{k: v for k, v in d.items() if k != "n"}, "n_inst": d["n"], "n": n, "K": K, "f": f, "ptype": pt})

names = [k for k in ILSX[0] if k.startswith("V") and "|" not in k and k != "V0lang"] + ["V0lang"]
ils_variants = {}
for name in names:
    ils_variants[name] = mean(100 * r[name] / max(r[x] for x in names) for r in ILSX)

by_cell = {}
for r in CONV:
    by_cell.setdefault((r["n"], r["K"], r["f"]), []).append(r)
convergence = []
for (n, K, f), rs in sorted(by_cell.items()):
    best = [max(r["ILS3k"], r["ILS30k"], r["GLS5"], r["GLS50"]) for r in rs]
    convergence.append({"n": n, "K": K, "f": f, "n_inst": len(rs),
                        **{m: mean(100 * r[m] / b for r, b in zip(rs, best)) for m in ("ILS3k", "ILS30k", "GLS5", "GLS50")},
                        "ils30k_besser": sum(r["ILS30k"] > r["ILS3k"] for r in rs)})

cands = [k for k in TUNE[0] if k.startswith("T")]
tuning = [{"name": k, "mean_share_of_ils": mean(100 * r[k] / r["ILS"] for r in TUNE), "n_inst": len(TUNE)} for k in cands]

k1 = {"n_inst": len(K1), **{m: mean(100 * o[m] / o["opt"] for o in K1) for m in ("G_ratio", "G_LS", "GLS", "ILS")},
      "below": {m: sum(o[m] < o["opt"] for o in K1) for m in ("G_ratio", "G_LS", "GLS", "ILS")}}

out = {"meta": {"n_instances_sweeps": 840, "source": "messreihe_gewinntouren (2026-11-11)", "seeds": "0-29", "tuning_seeds": "1000-1011"},
       "cells": cells, "ablation": ablation, "k1_exact": k1, "ils_variants": ils_variants, "convergence": convergence, "tuning": tuning}
(here / "data" / "gwt_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print("geschrieben:", len(cells), "Zellen,", len(ablation), "Ablationszellen")
