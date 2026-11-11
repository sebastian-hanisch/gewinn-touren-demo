"""Abnahmekriterien der Presets: was die angezeigte Instanz jedes Presets qualitativ zeigen muss.

Die Aussage der Demo stützt sich auf die Messreihe (30 Instanzen je Zelle); ein Preset zeigt nur eine Instanz, die zur Geschichte passt.
Die Kriterien sind deshalb bewusst grob (Schwellen in Prozent des besten Verfahrens der Instanz) und prüfen die Instanz, nicht die Messreihe.
Suche der Seeds: tools/find_preset_seeds.py (Seeds ab 101, nie 0 bis 29 der Messreihe und nie 1000 bis 1011 der Abstimmung)."""

import gwt_evaluation as E


def _shares(a):
    return {s.key: E.share(s.prize, a.best) for s in a.steps}


def story_standard(a):
    """Die Verhältnis-Regel liegt sichtbar hinter dem Besten; Routenzüge allein ändern die Prämie nicht."""
    sh = _shares(a)
    return sh["G_ratio"] <= 96.0 and E.step_of(a, "A_route").prize == E.step_of(a, "G_ratio").prize and sh["D_ils"] >= 99.0


def story_knapp(a):
    """Alle Verfahren liegen dicht beieinander (mindestens 95 % des Besten)."""
    sh = _shares(a)
    return min(sh.values()) >= 95.0 and E.step_of(a, "D_ils").prize == a.best


def story_fern(a):
    """Wenn die weiten Kunden die wertvollen sind, lässt die Verhältnis-Regel am meisten liegen (höchstens 92 %)."""
    sh = _shares(a)
    return sh["G_ratio"] <= 92.0 and sh["D_ils"] >= 99.0


def story_gleich(a):
    """Bei gleichen Prämien bringt Ersetzen nichts (per Konstruktion), die Suche aber mindestens so viel wie die Regel."""
    return E.step_of(a, "C_replace").prize == E.step_of(a, "B_insert").prize and E.step_of(a, "D_ils").prize >= E.step_of(a, "G_ratio").prize


def story_gross(a):
    """Bei 60 Kunden liegt die eigene Suche mindestens 5 Punkte vor der Verhältnis-Regel."""
    sh = _shares(a)
    return sh["D_ils"] - sh["G_ratio"] >= 5.0


STORIES = {
    "Standardfall": story_standard,
    "Knappes Budget": story_knapp,
    "Ferne Kunden wertvoll": story_fern,
    "Gleiche Prämien": story_gleich,
    "Großer Fall": story_gross,
}
