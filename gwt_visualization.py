"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben."""

import plotly.graph_objects as go

import gwt_constants as C

LINE_STYLES = (
    ("G_prize", "Höchste Prämie zuerst", "#9aa5b4", "solid"),
    ("G_ratio", "Verhältnis-Greedy", "#c77700", "solid"),
    ("G_LS", "+ Lokalsuche", "#8a4fb0", "solid"),
    ("GLS", "OR-Tools, Standard", "#c0392b", "solid"),
    ("GLS_t", "OR-Tools, abgestimmt", "#2a8f5b", "solid"),
    ("ILS", "Eigene Suche (ILS)", "#2a6fb0", "solid"),
)


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.25), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_map(inst, routes):
    """Depot, Kunden (Größe = Prämie) und die Touren. Nicht bediente Kunden sind grau. Gleiches Seitenverhältnis der Achsen."""
    served = {c: ri for ri, r in enumerate(routes) for c in r}
    fig = go.Figure()
    for ri, r in enumerate(routes):
        if not r:
            continue
        path = [0, *r, 0]
        color = C.COLOR_ROUTES[ri % len(C.COLOR_ROUTES)]
        fig.add_trace(go.Scatter(x=[inst.xy[i][0] for i in path], y=[inst.xy[i][1] for i in path], mode="lines",
                                 line=dict(color=color, width=2), name=f"Tour {ri + 1}", hoverinfo="skip"))
    max_prize = max(inst.prize[1:]) if inst.n else 1
    for ri in range(len(routes)):
        ids = [c for c, r in served.items() if r == ri]
        if ids:
            fig.add_trace(go.Scatter(
                x=[inst.xy[c][0] for c in ids], y=[inst.xy[c][1] for c in ids], mode="markers", showlegend=False,
                marker=dict(color=C.COLOR_ROUTES[ri % len(C.COLOR_ROUTES)], size=[8 + 14 * inst.prize[c] / max_prize for c in ids]),
                text=[f"Kunde {c}: Prämie {inst.prize[c]}" for c in ids], hovertemplate="%{text}<extra></extra>"))
    rest = [c for c in range(1, inst.n + 1) if c not in served]
    if rest:
        fig.add_trace(go.Scatter(
            x=[inst.xy[c][0] for c in rest], y=[inst.xy[c][1] for c in rest], mode="markers", name="nicht bedient",
            marker=dict(color=C.COLOR_UNSERVED, size=[8 + 14 * inst.prize[c] / max_prize for c in rest]),
            text=[f"Kunde {c}: Prämie {inst.prize[c]}" for c in rest], hovertemplate="%{text}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[inst.xy[0][0]], y=[inst.xy[0][1]], mode="markers", name="Depot",
                             marker=dict(color=C.COLOR_DEPOT, size=14, symbol="star"), hovertemplate="Depot<extra></extra>"))
    fig.update_xaxes(range=[-2, 102], showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(range=[-2, 102], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1)
    return _base(fig, 440)


def build_stairs(steps):
    """Prämie je Verfahren auf der Instanz (Balken). Beschriftungen als Text, damit Plotly keine lineare Achse anlegt."""
    labels = [s.label for s in steps]
    fig = go.Figure(go.Bar(x=labels, y=[s.prize for s in steps], marker_color=[C.STEP_COLORS.get(s.key, "#888") for s in steps],
                           text=[str(s.prize) for s in steps], textposition="outside", hovertemplate="%{x}: %{y}<extra></extra>"))
    top = max(s.prize for s in steps)
    fig.update_yaxes(title_text="Prämie", range=[0, max(1, top * 1.12)])
    return _base(fig, 330)


def build_budget_curve(cells, current_f=None):
    """Anteil am besten bekannten Wert über dem Budgetanteil (gemessene Zellen eines festen n, K, Prämienart)."""
    fig = go.Figure()
    xs = [c["f"] for c in cells]
    for key, label, color, dash in LINE_STYLES:
        ys = [c["share"].get(key) for c in cells]
        if all(y is None for y in ys):
            continue
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=label, line=dict(color=color, width=2, dash=dash),
                                 hovertemplate=label + ": %{y:.1f} % (Budgetanteil %{x})<extra></extra>"))
    if current_f is not None and current_f in xs:
        fig.add_vline(x=current_f, line_dash="dot", line_color="rgba(128,128,128,0.7)")
    fig.update_xaxes(title_text="Budgetanteil (Zeitbudget je Tour)", tickvals=xs)
    fig.update_yaxes(title_text="Anteil am Besten (%)", range=[78, 101])
    return _base(fig, 380)


def build_ablation(ab):
    """Stufen der Lokalsuche (vorgerechnet, Mittel über 30 Instanzen)."""
    keys = [("G", "Verhältnis-Greedy"), ("A_route", "+ Routenzüge"), ("B_insert", "+ Einfügen"), ("C_replace", "+ Ersetzen"),
            ("F_ILS_nur_Route", "ILS nur Routenzüge"), ("E_ILS_ohne_Ersetzen", "ILS ohne Ersetzen"), ("D_ILS", "ILS voll")]
    colors = ["#c77700", "#c77700", "#8a4fb0", "#8a4fb0", "#2a6fb0", "#2a6fb0", "#2a6fb0"]
    fig = go.Figure(go.Bar(x=[k[1] for k in keys], y=[ab[k[0]] for k in keys], marker_color=colors, text=[f"{ab[k[0]]:.1f}".replace(".", ",") for k in keys],
                           textposition="outside", hovertemplate="%{x}: %{y:.1f} %<extra></extra>"))
    fig.update_yaxes(title_text="Anteil am Besten (%)", range=[85, 102])
    return _base(fig, 330)


def build_nk_gap(cells):
    """Rückstand von OR-Tools (Standard gestrichelt, abgestimmt durchgezogen) zum ILS über n, je Fahrzeugzahl; Budgetanteil 0,5, gestreute Prämien."""
    fig = go.Figure()
    ks = sorted({c["K"] for c in cells})
    for i, k in enumerate(ks):
        row = sorted((c for c in cells if c["K"] == k), key=lambda c: c["n"])
        color = C.COLOR_ROUTES[i % len(C.COLOR_ROUTES)]
        fig.add_trace(go.Scatter(x=[c["n"] for c in row], y=[c["gap_tuned"][0] for c in row], mode="lines+markers", name=f"K = {k}, abgestimmt",
                                 line=dict(color=color, width=2), hovertemplate="n = %{x}: %{y:.1f} Punkte<extra></extra>"))
        fig.add_trace(go.Scatter(x=[c["n"] for c in row], y=[c["gap_std"][0] for c in row], mode="lines+markers", name=f"K = {k}, Standard",
                                 line=dict(color=color, width=2, dash="dash"), hovertemplate="n = %{x}: %{y:.1f} Punkte<extra></extra>"))
    fig.update_xaxes(title_text="Kunden n", tickvals=sorted({c["n"] for c in cells}))
    fig.update_yaxes(title_text="ILS minus OR-Tools (Punkte)")
    return _base(fig, 380)
