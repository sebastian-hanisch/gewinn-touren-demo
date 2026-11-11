"""Tourenplan als PDF (fpdf2, Standardschriften). Sonderzeichen werden vorher bereinigt: Gedankenstrich, Minuszeichen, Euro, Anführungszeichen
und Emoji stuerzen die Standardschriften sonst ab (DEMO-PLAYBOOK, fpdf2-Falle)."""

from fpdf import FPDF

import gwt_constants as C
import gwt_evaluation as E

_REPLACE = {"–": "-", "—": "-", "−": "-", "€": "EUR", "„": '"', "“": '"', "”": '"', "‚": "'", "‘": "'", "’": "'", "→": "->", "×": "x", "±": "+/-",
            "≤": "<=", "≥": ">=", "·": "-", "…": "..."}


def clean(text: str) -> str:
    """Nur Zeichen der Standardschrift (Latin-1) behalten; bekannte Sonderzeichen ersetzen, Unbekanntes (Emoji) streichen."""
    for old, new in _REPLACE.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "ignore").decode("latin-1")


def build_pdf(settings: E.Settings, a: E.Analysis, step_key: str = "D_ils") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, clean("Gewinn-Touren: Tourenplan"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, clean(
        f"{settings.n} Kunden, {settings.k} Fahrzeug(e), Zeitbudget je Tour {a.inst.tmax} min (Budgetanteil {settings.f}), "
        f"Prämien: {C.PTYPE_LABELS[settings.ptype]}, Zufalls-Seed {settings.seed}, Rechenbudget eigene Suche {settings.ils} Iterationen."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Verfahren auf dieser Instanz", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)
    widths = (70, 25, 25, 30, 35)
    for w, h in zip(widths, ("Verfahren", "Prämie", "Kunden", "Fahrzeit (min)", "Rechenzeit (s)")):
        pdf.cell(w, 6, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for s in a.steps:
        for w, v in zip(widths, (s.label, str(s.prize), str(s.served), str(s.minutes), f"{s.seconds:.2f}")):
            pdf.cell(w, 6, clean(v), border=1)
        pdf.ln()
    step = E.step_of(a, step_key)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, clean(f"Touren: {step.label} (Prämie {step.prize})"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for ri, route in enumerate(step.routes):
        if not route:
            pdf.cell(0, 5, f"Tour {ri + 1}: leer", new_x="LMARGIN", new_y="NEXT")
            continue
        used = S_time(a, route)
        pdf.multi_cell(0, 5, clean(f"Tour {ri + 1} ({used} von {a.inst.tmax} min): " + ", ".join(
            f"K{c} (an {t} min, Prämie {p})" for c, t, p in E.schedule(a.inst, route))), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, clean("Eine Instanz, kein Beleg: die Aussagen der Demo stützen sich auf die vorgerechnete Messreihe (30 Instanzen je Zelle)."),
                   new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def S_time(a: E.Analysis, route) -> int:
    import gwt_scenario as S
    return S.route_time(a.inst, route)
