"""Gewinn-Touren: welche Kunden fahren wir an, in welcher Reihenfolge? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Team Orienteering (Prize-Collecting-Tourenplanung): mehr Kunden als Zeit, Auswahl und Reihenfolge zusammen. Live auf einer Instanz:
Greedy, Lokalsuche in Stufen und eine eigene Suche (ILS); OR-Tools und das exakte Verfahren auf Knopfdruck. Die Aussagen stuetzen sich auf
die vorgerechnete Messreihe (data/gwt_results.json). Aufbau und Regeln: DEMO-PLAYBOOK.md (§2).

Lauffaehig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import gwt_constants as C
import gwt_evaluation as E
import gwt_results as R
import gwt_scenario as S
import gwt_solvers as V
import gwt_visualization as VIZ
from gwt_layout import dunkles_design, kopf_css
from gwt_pdf_export import build_pdf
from gwt_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    options,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)

st.set_page_config(page_title="Gewinn-Touren – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return E.analyse(settings)


@st.cache_data(show_spinner=False)
def _ortools(settings):
    """Beide OR-Tools-Einstellungen (je ORTOOLS_SECONDS) auf derselben Instanz."""
    inst = S.make_instance(settings.n, settings.k, settings.seed, settings.f, settings.ptype, C.SERVICE_MIN)
    std = V.solve_ortools(inst, C.ORTOOLS_SECONDS, tuned=False)
    tuned = V.solve_ortools(inst, C.ORTOOLS_SECONDS, tuned=True)
    return {"std": S.validate(inst, std), "tuned": S.validate(inst, tuned)}


@st.cache_data(show_spinner=False)
def _exact(settings):
    """CP-SAT mit Warmstart aus der eigenen Suche (wie in der Messreihe); liefert Status, Praemie und Schranke."""
    a = _analysis(settings)
    hint = [list(r) for r in E.step_of(a, "D_ils").routes]
    res = V.solve_cpsat(a.inst, C.EXACT_SECONDS, 1, hint=hint, seed=settings.seed)
    return {"status": res["status"], "obj": res["obj"], "bound": res["bound"], "sec": res["sec"]}


def _gap_std(ptype):
    """ILS minus OR-Tools (Standard) in Punkten, 25 Kunden, 2 Fahrzeuge, Budgetanteil 0,4, je Prämienart (gemessene Zelle)."""
    return R.nearest_cell(25, 2, 0.4, ptype)[0]["gap_std"][0]


def _fmt_f(value):
    return f"{value:g}".replace(".", ",")


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in gwt_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🚚 Gewinn-Touren: welche Kunden fahren wir an, in welcher Reihenfolge?")
st.markdown(
    """
Ein Fahrer hat **mehr mögliche Kunden als Zeit**: Jeder Kunde bringt eine **Prämie**, jede Tour hat ein **Zeitbudget**, gesucht sind **Auswahl und Reihenfolge zusammen**
(Team Orienteering). Die Demo zeigt live auf **einer Instanz**, wo die Auswahl entsteht, und vergleicht Greedy, Lokalsuche, eine eigene Suche (ILS), **OR-Tools** und ein **exaktes Verfahren**;
die Aussagen stützen sich auf eine vorgerechnete Messreihe mit 30 Instanzen je Zelle.

Gleich darunter erklärt **💬 In einfachen Worten** das Thema ohne Formeln. Weiter unten: die **Kernfragen** und die Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich**, **Wie funktioniert diese Demo?** und **📐 Mathematische Formulierung**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/gewinn-touren-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Ein Fahrer hat mehr mögliche Kunden als Zeit. Jeder Kunde bringt einen **Wert**, und jede Tour hat ein **Zeitbudget**. Es geht also um zwei Fragen zugleich: **welche Kunden** werden angefahren und **in welcher Reihenfolge**. Die Demo vergleicht eine einfache Regel, eine Verbesserung per Tausch, eine eigene Suche, den Löser OR-Tools und ein Verfahren, das den besten Plan beweist. Sie zeigt auf einer Beispielinstanz, **wo die Auswahl entsteht**, und in einer vorgerechneten Messreihe, **wann welches Verfahren reicht**. Eine einzelne Instanz belegt nichts, die Messreihe zählt.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/gewinn-touren-erklaert.html)
        """
    )
# erklaerseite:einfach:end

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Instanz**")
    n = st.select_slider("Kunden", options=options("n_slider"), key="n_slider", help="Wie viele Kunden zur Wahl stehen (die gemessenen Größen).")
    k = st.slider("Fahrzeuge", *bounds("k_slider"), key="k_slider", help="Jedes Fahrzeug fährt eine Tour. Bei gleichem Budgetanteil sinkt das Zeitbudget je Tour mit der Fahrzeugzahl.")
    f = st.select_slider(
        "Zeitbudget je Tour", options=options("f_slider"), key="f_slider", format_func=_fmt_f,
        help="Anteil eines Rundreise-Richtwerts über alle Kunden (Nächster Nachbar plus 2-opt, einschließlich Service), geteilt durch die Zahl der Fahrzeuge. 1 heißt: etwa so viel Zeit, wie alle Kunden zusammen brauchen (ohne Gewähr, dass dann alle bedient werden).")
    ptype = st.radio("Prämien", options("ptype_radio"), key="ptype_radio", format_func=lambda p: C.PTYPE_LABELS[p],
                     help="Gleich: jeder Kunde 10. Gestreut: lognormal, Mittel 60. Fern: je weiter vom Depot, desto mehr.")
    st.markdown("**Rechnen**")
    ils = st.select_slider("Rechenbudget eigene Suche", options=options("ils_slider"), key="ils_slider", format_func=lambda v: C.ILS_LABELS[v],
                           help="Iterationen der eigenen Suche (ILS). Die Messreihe nutzt 3000; bei 300 liegt sie in der Messung (2 Fahrzeuge, Budgetanteil 0,5, 10 Instanzen je Größe) im Mittel bei mindestens 99,4 % des besten der drei Läufe (bei 60 Kunden die schlechteste Instanz bei 95,1 %), braucht aber weniger Zeit.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)

sync_query_params({"n_slider": int(n), "k_slider": int(k), "f_slider": float(f), "ptype_radio": ptype, "ils_slider": int(ils), "seed_input": int(seed)})

settings = E.Settings(int(n), int(k), float(f), ptype, int(ils), int(seed))
with st.spinner(f"Rechne die Verfahren auf einer Instanz mit {settings.n} Kunden ..."):
    a = _analysis(settings)

or_state = st.session_state.get("ortools_done") == settings
or_res = _ortools(settings) if or_state else None
extra = [] if or_res is None else [or_res["std"], or_res["tuned"]]
best = E.best_known(a, *extra)
best_step = max(a.steps, key=lambda s: (s.prize, -s.minutes))
g_ratio = E.step_of(a, "G_ratio")

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🚚 Eine Instanz: Auswahl und Reihenfolge")
st.info("Das ist **eine Instanz**. Sie zeigt, wie die Verfahren arbeiten; die Aussagen darüber, wann welches Verfahren reicht, stützen sich auf die Messreihe weiter unten (30 Instanzen je Zelle).")

r1c1, r1c2 = st.columns(2)
r1c1.metric("Prämie des besten Verfahrens", f"{best}", delta=f"{best - g_ratio.prize:+d} gegenüber Verhältnis-Greedy", delta_color="off")
r1c2.metric("Verhältnis-Greedy, Anteil am Besten", f"{R.num(E.share(g_ratio.prize, best))} %", delta=f"{g_ratio.prize} von {best} Prämie", delta_color="off")
r2c1, r2c2 = st.columns(2)
if or_res is None:
    r2c1.metric("OR-Tools (abgestimmt), Anteil am Besten", "–", delta="noch nicht gerechnet (Tab OR-Tools)", delta_color="off")
else:
    r2c1.metric("OR-Tools (abgestimmt), Anteil am Besten", f"{R.num(E.share(or_res['tuned'], best))} %", delta=f"{or_res['tuned']} von {best} Prämie", delta_color="off")
r2c2.metric("Bediente Kunden (bestes Verfahren)", f"{best_step.served} von {settings.n}",
            delta=f"Zeitbudget zu {R.num(E.budget_use_percent(a, best_step))} % genutzt", delta_color="off")

labels = {s.key: s.label for s in a.steps}
view_key = st.selectbox("Plan anzeigen für", list(labels), index=list(labels).index("D_ils"), format_func=lambda key: labels[key], key="view_select",
                        help="Reine Anzeigewahl: ändert nichts an der Rechnung.")
view = E.step_of(a, view_key)
st.plotly_chart(VIZ.build_map(a.inst, view.routes), width="stretch", key="map_chart")
st.caption(f"{view.label}: Prämie {view.prize}, {view.served} Kunden, Fahrzeit {view.minutes} von {settings.k * a.inst.tmax} Minuten (Budget je Tour {a.inst.tmax}). "
           "Punktgröße = Prämie, grau = nicht bedient, Stern = Depot.")
st.download_button("📄 Tourenplan als PDF", data=build_pdf(settings, a, view_key), file_name="gewinn-touren.pdf", mime="application/pdf", key="pdf_download")

st.markdown("---")

# --- Kernfrage 1: Wo entsteht die Auswahl? ----------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 1: Wo entsteht die Auswahl?")
kind, text = E.verdict_stairs(a)
getattr(st, kind)(text)
st.plotly_chart(VIZ.build_stairs(a.steps), width="stretch", key="stairs_chart")
ab = R.ablation_cell(25, 2, 0.4, "lognormal")
st.markdown(
    f"**Vorgerechnet (n = 25, 2 Fahrzeuge, Budgetanteil 0,4, gestreute Prämien, 30 Instanzen):** Routenzüge allein ändern die Kundenmenge in "
    f"{ab['A_gleiche_Menge']} von 30 Instanzen nicht und sparen im Mittel {R.num(ab['A_Zeit_gespart_%'])} % Fahrzeit. Einfügen bringt {R.pm(ab['B_minus_G_pkt'])} Punkte, Ersetzen weitere "
    f"{R.pm(ab['C_minus_B_pkt'])}. Im ILS bringt Ersetzen nur {R.pm(ab['D_minus_E_pkt'])} Punkte, das Einfügen im Lokalsuchschritt {R.pm(ab['D_minus_F_pkt'])}: "
    f"in dieser Zelle ändert vor allem das Entfernen und verrauschte Neueinfügen die Auswahl (ILS nur mit Routenzügen: {R.num(ab['F_ILS_nur_Route'])} % statt {R.num(ab['G'])} % beim Greedy). (Punkte = Prozentpunkte vom besten bekannten Wert; Mittel ± Standardfehler.)"
)
st.plotly_chart(VIZ.build_ablation(ab), width="stretch", key="ablation_chart")
st.caption("Balken: Anteil am besten bekannten Wert (Mittel über 30 Instanzen). Bei gleichen Prämien ist Ersetzen per Konstruktion wirkungslos (der Zug verlangt eine höhere Prämie).")

st.markdown("---")

# --- Kernfrage 2: Wann reicht welches Verfahren? ---------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 2: Wann reicht welches Verfahren?")
cell, exact = R.nearest_cell(settings.n, settings.k, settings.f, settings.ptype)
kind, text = E.verdict_regime(cell, exact)
getattr(st, kind)(text)
curve = R.budget_curve(cell["n"], cell["K"], cell["ptype"])
if len(curve) < 2:
    curve = R.budget_curve(25, 2, cell["ptype"])
    st.caption("Für diese Zelle gibt es keine Kurve über das Budget; gezeigt wird die Kurve für 25 Kunden und 2 Fahrzeuge.")
st.plotly_chart(VIZ.build_budget_curve(curve, settings.f if exact else None), width="stretch", key="budget_chart")
st.caption(f"Anteil am besten bekannten Wert über dem Budgetanteil: n = {curve[0]['n']}, {curve[0]['K']} Fahrzeuge, {C.PTYPE_WORDS[curve[0]['ptype']]}; je Zelle {curve[0]['n_inst']} Instanzen. "
           "OR-Tools abgestimmt: auf getrennten Instanzen gewählte Einstellung, zeitgleich zur eigenen Suche (mindestens 5 s).")
counts = R.zone_counts()
st.markdown(f"**Zählung:** In den {sum(counts.values())} gemessenen Zellen des Haupt-Sweeps liegt Greedy plus Lokalsuche in {counts['A']} Zellen höchstens {R.num(C.GAP_GREEDY_REICHT, 0)} Punkte hinter dem Besten, "
            f"in {counts['B']} zwischen {R.num(C.GAP_GREEDY_REICHT, 0)} und {R.num(C.GAP_AUSWAHL_ENTSCHEIDET, 0)} Punkten und in {counts['C']} mehr als {R.num(C.GAP_AUSWAHL_ENTSCHEIDET, 0)} Punkte "
            "(Schwellen gesetzt, nicht hergeleitet; die 3 Zellen mit höchstens 2 Punkten sind knappe Budgets, darunter die triviale Zelle mit Budgetanteil 0,1).")

st.markdown("---")

# --- Kernfrage 3: Wie weit ist das Optimum? ---------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 3: Wie weit ist das Optimum?")
k1 = R.load()["k1_exact"]
st.markdown(
    f"**Ein Fahrzeug, 20 Kunden, Budgetanteil 0,5 ({k1['n_inst']} Instanzen, exaktes Optimum per Teilmengen-Rechnung):** die eigene Suche (ILS) erreicht {R.num(k1['ILS'])} % des Optimums "
    f"(unter dem Optimum in {k1['below']['ILS']} von {k1['n_inst']}), Verhältnis-Greedy {R.num(k1['G_ratio'])} %, mit Lokalsuche {R.num(k1['G_LS'])} %, "
    f"OR-Tools in der Standard-Einstellung {R.num(k1['GLS'])} % (unter dem Optimum in {k1['below']['GLS']} von {k1['n_inst']})."
)
rows = [{"Budgetanteil": c["f"], "Optimum bewiesen (von 30)": c["proven"], "Schranke über dem Besten, nicht bewiesene Instanzen (%)": c["bound_gap_unproven"]}
        for c in R.budget_curve(25, 2, "lognormal")]
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={"Budgetanteil": st.column_config.NumberColumn(format="%.2f"),
                            "Schranke über dem Besten, nicht bewiesene Instanzen (%)": st.column_config.NumberColumn(format="%.0f")})
st.caption("CP-SAT, 30 s, ein Worker, Warmstart aus dem besseren von ILS und OR-Tools. Wo das Optimum nicht bewiesen ist, liegt die Schranke bei Budgetanteil 0,4 bis 0,65 um 42 bis 100 % über dem Besten und sagt über die Güte der Heuristiken wenig; erst bei Budgetanteil 1,0 liegt sie nur 4 % darüber; "
           "„bester bekannter Wert“ ist dort das Maximum der Verfahren, meist die eigene Suche.")

st.markdown("---")

# --- Methodenvergleich ---------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_plan, tab_methods, tab_moves, tab_or, tab_exact, tab_series = st.tabs(
        ["🗺️ Tourenplan", "📊 Verfahren", "🧩 Zugarten", "🧰 OR-Tools", "🧮 Exakt (CP-SAT)", "📈 Messreihe"])
    with tab_plan:
        st.markdown(f"Halteliste für **{view.label}** (Ankunft in Minuten nach Start, Service {C.SERVICE_MIN} min je Kunde).")
        for ri, route in enumerate(view.routes):
            if not route:
                st.caption(f"Tour {ri + 1}: leer")
                continue
            sched = E.schedule(a.inst, route)
            df = pd.DataFrame([{"Halt": i + 1, "Kunde": c_, "Ankunft (min)": t, "Prämie": p} for i, (c_, t, p) in enumerate(sched)])
            st.caption(f"Tour {ri + 1}: {S.route_time(a.inst, route)} von {a.inst.tmax} Minuten, Prämie {sum(p for _, _, p in sched)}")
            st.dataframe(df, hide_index=True, width="stretch")
    with tab_methods:
        rows = [{"Verfahren": s.label, "Prämie": s.prize, "Anteil am Besten (%)": E.share(s.prize, best), "Kunden": s.served, "Fahrzeit (min)": s.minutes,
                 "Zeitnutzung (%)": E.budget_use_percent(a, s), "Rechenzeit (s)": s.seconds} for s in a.steps]
        if or_res is not None:
            rows += [{"Verfahren": "OR-Tools (Standard)", "Prämie": or_res["std"], "Anteil am Besten (%)": E.share(or_res["std"], best)},
                     {"Verfahren": "OR-Tools (abgestimmt)", "Prämie": or_res["tuned"], "Anteil am Besten (%)": E.share(or_res["tuned"], best)}]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={"Anteil am Besten (%)": st.column_config.NumberColumn(format="%.1f"), "Zeitnutzung (%)": st.column_config.NumberColumn(format="%.1f"),
                                    "Rechenzeit (s)": st.column_config.NumberColumn(format="%.2f")})
        st.caption("Die Rechenzeit gilt für diesen Rechner und diese Sitzung. „Anteil am Besten“ bezieht sich auf das Maximum aller hier gerechneten Verfahren.")
    with tab_moves:
        st.markdown(
            "Die **Lokalsuche** kennt fünf Zugarten. **Routenzüge** (2-opt, Verschieben, Tauschen) ändern nur Reihenfolge und Zuordnung zu den Touren, nie die Menge der bedienten Kunden; "
            "**Einfügen** füllt freie Zeit mit einem weiteren Kunden; **Ersetzen** tauscht einen bedienten gegen einen unbedienten Kunden mit höherer Prämie. "
            "Der **ILS** entfernt zusätzlich einige Kunden (ein Stück Tour oder zufällige), fügt sie verrauscht wieder ein und startet die Lokalsuche neu."
        )
        st.plotly_chart(VIZ.build_ablation(ab), width="stretch", key="ablation_chart_tab")
        st.caption("Dieselben vorgerechneten Zahlen wie oben. Weitere Zellen: siehe Tab Messreihe.")
    with tab_or:
        st.markdown(
            f"Zwei Einstellungen von OR-Tools (Routing mit Disjunktionsstrafen), je {R.num(C.ORTOOLS_SECONDS, 0)} s: **Standard** (Guided Local Search, Strafe 1000 × Prämie) und **abgestimmt** "
            "(Tabu-Suche, Warmstart aus dem Verhältnis-Greedy, neun zusätzliche Operatoren, Strafe normiert auf die mittlere Prämie). Die abgestimmte Einstellung wurde auf getrennten Instanzen gewählt; "
            "sie überträgt sich nicht auf gleiche Prämien."
        )
        if st.button(f"OR-Tools rechnen (2 × {R.num(C.ORTOOLS_SECONDS, 0)} s)", key="ortools_start"):
            st.session_state["ortools_done"] = settings
            st.rerun()
        if st.session_state.get("ortools_done") == settings:
            with st.spinner("OR-Tools rechnet ..."):
                try:
                    res = _ortools(settings)
                except ImportError:
                    res = None
                    st.warning("OR-Tools ist in dieser Umgebung nicht installiert.")
            if res is not None:
                kind, text = E.verdict_ortools(a, res["std"], res["tuned"])
                getattr(st, kind)(text)
    with tab_exact:
        # Der Tab ist selbstständig: eigener Button, Spinner und Ergebnis, gegen das aktuelle Szenario geprüft (DEMO-PLAYBOOK §2).
        if settings.n > C.EXACT_N_MAX:
            st.info(f"Bei n = {settings.n} Kunden wird das exakte Verfahren nicht angeboten: In der Messreihe beweist CP-SAT bei 25 Kunden ab Budgetanteil 0,5 kaum noch ein Optimum, "
                    "bei 40 Kunden und Budgetanteil 0,4 mit 1 bis 2 Fahrzeugen keines (mit 4 Fahrzeugen 29 von 30); bei 60 Kunden wurde es nicht versucht (siehe Kernfrage 3 und Tab Messreihe).")
        else:
            st.markdown(f"CP-SAT (Kreise mit Selbstschleife für „nicht bedient“, ein Worker, höchstens {R.num(C.EXACT_SECONDS, 0)} s, Warmstart aus der eigenen Suche).")
            if st.button("Optimum berechnen", key="exact_start"):
                st.session_state["exact_done"] = settings
                st.rerun()
            if st.session_state.get("exact_done") == settings:
                with st.spinner("CP-SAT rechnet ..."):
                    try:
                        res = _exact(settings)
                    except ImportError:
                        res = None
                        st.warning("OR-Tools ist in dieser Umgebung nicht installiert.")
                if res is not None:
                    kind, text = E.verdict_exact(a, res["status"], res["obj"], res["bound"])
                    getattr(st, kind)(text)
                    st.caption(f"Rechenzeit {res['sec']:.1f} s, Status {res['status']}.")
    with tab_series:
        st.markdown("Alle gemessenen Zellen (Seeds 0 bis 29, je Zelle bis zu 30 Instanzen, Mittel über die Instanzen). „Punkte“ sind Prozentpunkte vom besten bekannten Wert.")
        rows = []
        for c_ in sorted(R.load()["cells"], key=lambda c_: (c_["ptype"], c_["n"], c_["K"], c_["f"])):
            rows.append({"Prämien": C.PTYPE_WORDS[c_["ptype"]], "n": c_["n"], "Fahrzeuge": c_["K"], "Budgetanteil": c_["f"], "Instanzen": c_["n_inst"],
                         "Greedy (%)": c_["share"]["G_ratio"], "+ Lokalsuche (%)": c_["share"]["G_LS"], "ILS (%)": c_["share"]["ILS"],
                         "OR-Tools Standard (%)": c_["share"]["GLS"], "OR-Tools abgestimmt (%)": c_["share"]["GLS_t"],
                         "ILS − OR-Tools Standard (Punkte)": c_["gap_std"][0], "ILS − OR-Tools abgestimmt (Punkte)": None if c_["gap_tuned"] is None else c_["gap_tuned"][0]})
        pct = {col: st.column_config.NumberColumn(format="%.1f") for col in ("Greedy (%)", "+ Lokalsuche (%)", "ILS (%)", "OR-Tools Standard (%)", "OR-Tools abgestimmt (%)",
                                                                           "ILS − OR-Tools Standard (Punkte)", "ILS − OR-Tools abgestimmt (Punkte)")}
        pct["Budgetanteil"] = st.column_config.NumberColumn(format="%.2f")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config=pct)
        nk_cells = [c_ for c_ in R.load()["cells"] if c_["source"] == "nk"]
        st.plotly_chart(VIZ.build_nk_gap(nk_cells), width="stretch", key="nk_chart")
        st.caption("Rückstand von OR-Tools zum ILS über n, je Fahrzeugzahl (Budgetanteil 0,5, gestreute Prämien, 30 Instanzen je Punkt). Durchgezogen: abgestimmt und zeitgleich; gestrichelt: Standard-Einstellung.")
        conv = R.load()["convergence"]
        st.markdown("**Konvergenz** (Anteil am Besten der Instanz, je 10 Instanzen): " + "; ".join(
            f"n = {c_['n']}, {c_['K']} Fahrzeuge, Budgetanteil {R.num(c_['f'])}: ILS 3000 {R.num(c_['ILS3k'])} %, ILS 30000 {R.num(c_['ILS30k'])} %, OR-Tools 5 s {R.num(c_['GLS5'])} %, 50 s {R.num(c_['GLS50'])} %"
            for c_ in conv) + ".")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Die Aufgabe.** Ein Depot, {settings.n} Kunden, {settings.k} Fahrzeug(e). Jede Tour darf höchstens {a.inst.tmax} Minuten dauern (Fahrt, {C.SERVICE_MIN} Minuten Service je Kunde, Rückkehr). Jeder Kunde bringt eine Prämie,
jeder wird höchstens einmal bedient. Gesucht ist die Auswahl und Reihenfolge mit der größten Prämiensumme. Das Zeitbudget ist ein Anteil einer Rundreise über alle Kunden, geteilt durch die Fahrzeugzahl; die Fahrzeit ist
aufgerundet 1,2 × Distanz (Dreiecksungleichung gilt).

**Die Verfahren.**
- *Höchste Prämie zuerst:* Kunden nach Prämie sortieren und jeweils an der günstigsten zulässigen Stelle einfügen.
- *Verhältnis-Greedy:* wiederholt den Kunden mit der größten Prämie je Zusatzzeit einfügen.
- *Lokalsuche:* Routenzüge, Einfügen, Ersetzen (siehe Tab Zugarten).
- *Eigene Suche (ILS):* Kunden entfernen, verrauscht neu einfügen, Lokalsuche; deterministisch bei gleichem Seed und gleicher Iterationszahl.
- *OR-Tools:* Routing mit Strafe für nicht bediente Kunden, in zwei Einstellungen.
- *CP-SAT:* exakt, mit Schranke; nur bis {C.EXACT_N_MAX} Kunden angeboten.

**„Bester bekannter Wert“** ist das Maximum aller Verfahren auf der Instanz (bei bewiesenem Optimum das Optimum). Die eigene Suche stellt dabei meist das Maximum: Ihr Anteil ist daher per Konstruktion nahe 100 %.
Wo kein Optimum bewiesen ist, kann das wahre Optimum höher liegen.

**Was die Live-Zahlen bedeuten.** Sie gelten für diese eine Instanz. Die Aussagen der Kernfragen 2 und 3 stammen aus einer vorgerechneten Messreihe (Seeds 0 bis 29, je Zelle bis zu 30 Instanzen);
die eingestellte Kombination ist nur dann gemessen, wenn es dazu eine Zelle gibt, sonst steht die nächstliegende.

**🚧 Wo die Annahmen enden**

| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| Keine Zeitfenster | Mit Zeitfenstern (TOPTW) wird auch die Reihenfolge zur Zulässigkeitsfrage; die Messreihe sagt dazu nichts | Ausbau |
| Orte gleichverteilt, keine Cluster | Bei Clustern kann sich der Abstand der Verfahren ändern | nicht gemessen |
| Prämien frei gewählt (gleich, gestreut, fern) | Die Prämienart verändert den Abstand der Verfahren (ILS minus OR-Tools Standard bei Budgetanteil 0,4: {R.num(_gap_std('gleich'), 1, True)} gleich, {R.num(_gap_std('lognormal'), 1, True)} gestreut, {R.num(_gap_std('fern'), 1, True)} fern); ein Regler für das Verhältnis Prämie zu Fahrzeit wurde nicht gemessen | Regler „Prämien“ |
| Bester bekannter Wert statt Optimum | Anteile des ILS sind nahe 100 %; bei 40 Kunden und 1 bis 2 Fahrzeugen gelang kein Beweis (Budgetanteil 0,4), bei 60 Kunden wurde er nicht versucht | Kernfrage 3 |
| OR-Tools in zwei Einstellungen | Aussagen über OR-Tools gelten für diese Einstellungen, nicht für das Verfahren; die abgestimmte Einstellung überträgt sich nicht auf gleiche Prämien | Tab OR-Tools |
| Rechenzeiten | Auf anderen Rechnern anders; OR-Tools und CP-SAT sind zeitlimitiert und nicht bitgleich reproduzierbar | Tab Verfahren |
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/gewinn-touren-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind ein Depot, $n$ Kunden mit Prämie $p_i$, Fahrzeiten $t_{ij}$, ein Service $s$ je Kunde und $K$ Fahrzeuge mit Zeitbudget $T$ je Tour. Gesucht ist, welche Kunden bedient werden und in welcher Reihenfolge, sodass die Prämiensumme möglichst groß ist.

| Symbol | Bedeutung |
|---|---|
| $p_i$ | Prämie von Kunde $i$ |
| $t_{ij}$ | Fahrzeit von $i$ nach $j$ (Depot = 0) |
| $s$ | Service je Kunde |
| $T$ | Zeitbudget je Tour |
| $y_i$ | 1, wenn Kunde $i$ bedient wird |
| $x_{ijk}$ | 1, wenn Fahrzeug $k$ von $i$ direkt nach $j$ fährt |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/gewinn-touren-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        """
$$\\max \\sum_{i} p_i \\, y_i$$

$$\\sum_{k}\\sum_{j} x_{ijk} = y_i \\quad (i = 1, \\dots, n)$$

$$\\sum_{(i,j)} t_{ij}\\, x_{ijk} + s \\sum_{i=1}^{n}\\sum_{j} x_{ijk} \\le T \\quad (k = 1, \\dots, K)$$

Dazu gehören Binärbedingungen für $x$ und $y$, Flusserhaltung je Fahrzeug und Kunde (Zufluss gleich Abfluss), höchstens ein Abgang je Fahrzeug aus dem Depot mit Rückkehr dorthin und ein Teiltourverbot (keine Kreise ohne Depot). $T$ ist der Anteil $f$ eines Rundreise-Richtwerts $R$ über alle Kunden, geteilt durch $K$: $T = f \\cdot R / K$; der Service $s$ wird je angefahrenem Kunden gerechnet, nicht am Depot. In CP-SAT wird das als Mehrfach-Kreis mit einer Selbstschleife für $y_i = 0$ und kumulierter Zeit $L_j \\ge L_i + t_{ij} + s$ je gewähltem Bogen abgebildet.

**Verhältnis-Greedy.** Wähle $\\arg\\max_i \\; p_i / \\Delta_i$ mit $\\Delta_i$ = billigste zulässige Zusatzzeit beim Einfügen von $i$; wiederhole, bis nichts mehr passt.

**ILS.** Entferne $m$ Kunden, füge unbediente Kunden nach $p_i / \\Delta_i$ mit einem Rauschfaktor in $[0{,}7;\\, 1{,}3]$ wieder ein, verbessere lokal (lexikographisch: Prämie hoch, Gesamtzeit niedrig), übernimm das Ergebnis, wenn es nicht schlechter ist.

**Anteil am besten bekannten Wert** $= 100 \\cdot P / P^{\\text{best}}$ mit $P^{\\text{best}}$ = Maximum der Verfahren auf der Instanz.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html)."
)
