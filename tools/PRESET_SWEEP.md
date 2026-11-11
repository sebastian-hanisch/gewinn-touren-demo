# Preset-Abstimmung (tools/find_preset_seeds.py)

Je Preset der erste Seed ab 101, dessen Live-Instanz das Kriterium aus `gwt_stories.py` erfüllt. Die Aussage der Demo stützt sich nicht darauf (eine Instanz), sondern auf die Messreihe.

| Preset | Seed | gesuchte Seeds | Kriterium |
|---|---|---|---|
| Standardfall | 101 | 1 | Die Verhältnis-Regel liegt sichtbar hinter dem Besten; Routenzüge allein ändern die Prämie nicht. |
| Knappes Budget | 101 | 1 | Alle Verfahren liegen dicht beieinander (mindestens 95 % des Besten). |
| Ferne Kunden wertvoll | 102 | 2 | Wenn die weiten Kunden die wertvollen sind, lässt die Verhältnis-Regel am meisten liegen (höchstens 92 %). |
| Gleiche Prämien | 101 | 1 | Bei gleichen Prämien bringt Ersetzen nichts (per Konstruktion), die Suche aber mindestens so viel wie die Regel. |
| Großer Fall | 102 | 2 | Bei 60 Kunden liegt die eigene Suche mindestens 5 Punkte vor der Verhältnis-Regel. |
