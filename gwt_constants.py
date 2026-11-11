"""Konstanten: Regler-Stufen, feste Annahmen, Farben und Presets.

Die Stufen der Regler sind die in der Vorab-Messreihe gemessenen Werte (Kunden, Fahrzeuge, Budgetanteil, Praemienart); Kombinationen
jenseits der gemessenen Zellen erhalten in der App die naechstliegende gemessene Zelle (gwt_results.nearest_cell)."""

N_OPTIONS = (15, 25, 40, 60)
DEFAULT_N = 25
K_MIN, K_MAX, DEFAULT_K = 1, 4, 2
F_OPTIONS = (0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0)  # Budgetanteil: Zeitbudget je Tour = f x Rundreise ueber alle Kunden / K
DEFAULT_F = 0.5
PTYPE_OPTIONS = ("gleich", "lognormal", "fern")
PTYPE_LABELS = {"gleich": "gleich (10 je Kunde)", "lognormal": "gestreut (Mittel 60)", "fern": "fern = wertvoll"}
PTYPE_WORDS = {"gleich": "gleiche Prämien", "lognormal": "gestreute Prämien", "fern": "Prämien „fern = wertvoll“"}
DEFAULT_PTYPE = "lognormal"
ILS_OPTIONS = (300, 1000, 3000)                    # Iterationen der eigenen Suche
ILS_LABELS = {300: "300 (schnell)", 1000: "1000", 3000: "3000 (wie Messreihe)"}
DEFAULT_ILS = 300
SEED_MAX, DEFAULT_SEED = 999999, 101               # Seeds 0..29 gehoeren der Messreihe, 1000..1011 der Abstimmung

SERVICE_MIN = 6                                    # Service je Kunde in Minuten
ORTOOLS_SECONDS = 5.0                              # Zeitlimit je OR-Tools-Lauf (zwei Einstellungen)
EXACT_SECONDS = 20.0                               # Zeitlimit CP-SAT
EXACT_N_MAX = 25                                   # darueber nicht angeboten: bei 40 Kunden mit 1 bis 2 Fahrzeugen bewies CP-SAT in 30 s nichts (4 Fahrzeuge: 29 von 30), 60 Kunden nicht versucht
GAP_GREEDY_REICHT = 2.0                            # Punkte: Greedy + Lokalsuche hoechstens so weit hinter dem Besten
GAP_AUSWAHL_ENTSCHEIDET = 6.0                      # darueber entscheidet die Auswahl (gesetzt, nicht hergeleitet)

COLOR_ROUTES = ("#2F6B65", "#c77700", "#8a4fb0", "#2a6fb0")
COLOR_UNSERVED = "rgba(150,150,150,0.6)"
COLOR_DEPOT = "#c0392b"
STEP_COLORS = {"G_prize": "#9aa5b4", "G_ratio": "#c77700", "A_route": "#c77700", "B_insert": "#8a4fb0", "C_replace": "#8a4fb0",
               "E_ils_ohne": "#2a6fb0", "D_ils": "#2a6fb0"}

PRESETS = {
    "Standardfall": {"n": 25, "k": 2, "f": 0.5, "ptype": "lognormal", "ils": 300, "seed": 101},
    "Knappes Budget": {"n": 25, "k": 2, "f": 0.2, "ptype": "lognormal", "ils": 300, "seed": 101},
    "Ferne Kunden wertvoll": {"n": 25, "k": 2, "f": 0.4, "ptype": "fern", "ils": 300, "seed": 102},
    "Gleiche Prämien": {"n": 25, "k": 2, "f": 0.4, "ptype": "gleich", "ils": 300, "seed": 101},
    "Großer Fall": {"n": 60, "k": 2, "f": 0.4, "ptype": "lognormal", "ils": 300, "seed": 102},
}
PRESET_HELP = {
    "Standardfall": "25 Kunden, 2 Fahrzeuge, halbes Zeitbudget, gestreute Prämien: der Verhältnis-Greedy liegt hinter dem Besten, Lokalsuche und ILS holen auf.",
    "Knappes Budget": "Wenig Zeit, wenige Kunden: in der Messreihe liegen alle Verfahren dicht beieinander, Greedy mit Lokalsuche genügt.",
    "Ferne Kunden wertvoll": "Prämie wächst mit dem Abstand zum Depot: hier liegen Greedy und Lokalsuche in der Messreihe mit am weitesten zurück (8,4 Punkte; die übrigen Zellen höchstens 7,2).",
    "Gleiche Prämien": "Alle Kunden gleich viel wert: es zählt nur die Kundenzahl; Ersetzen bleibt wirkungslos.",
    "Großer Fall": "60 Kunden: bei 2 und 4 Fahrzeugen wächst der Rückstand von OR-Tools mit n (bei 4 Fahrzeugen erst von 40 auf 60 Kunden deutlich); die Einstellung von OR-Tools macht mehrere Punkte aus.",
}
