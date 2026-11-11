# Gewinn-Touren: welche Kunden fahren wir an, in welcher Reihenfolge? – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-gewinn-touren-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`). Ein Fahrer (oder wenige) hat **mehr mögliche Kunden als Zeit**: Jeder Kunde bringt eine Prämie, jede Tour hat ein
Zeitbudget, gesucht sind **Auswahl und Reihenfolge zusammen** (Team Orienteering, Prize-Collecting-Tourenplanung ohne Zeitfenster). Verglichen werden eine Verhältnis-Regel („Prämie je Zusatzzeit“), die Regel „höchste Prämie zuerst“,
eine **Lokalsuche in Stufen** (Routenzüge, Einfügen, Ersetzen), eine **eigene Suche (ILS)**, **OR-Tools** in zwei Einstellungen und das **exakte Verfahren CP-SAT**. Live läuft das auf einer Instanz; die Aussagen stützen sich auf eine
vorgerechnete Messreihe mit 30 Instanzen je Zelle (`data/gwt_results.json`).

## Warum dieses Problem

Kunden auszuwählen und anzufahren ist in Außendienst, Zustellung und Spotaufträgen Alltag, und die Auswahl hängt an der Route: Ein wertvoller, weit entfernter Kunde verdrängt zwei nahe. Die Kernfragen der Demo:
**Wo entsteht die Auswahl** (welcher Zug, welches Verfahren), **wann reicht welches Verfahren** und **wie weit ist das Optimum**? Im Portfolio gab es das Modell nach einer Stichwortsuche über die Demo-Ordner bisher nur als Hindsight-Orakel in `nahverkehr-demo` und als
ausdrücklich nicht umgesetztes Kriterium in `auftragsallianz-demo`.

## Modell

Depot in der Mitte eines 100 × 100-Gebiets, n Kunden (15, 25, 40 oder 60) gleichverteilt, K Fahrzeuge (1 bis 4) mit je einer Tour. Fahrzeit = aufgerundet 1,2 × Distanz (die Dreiecksungleichung gilt), Service 6 Minuten je Kunde.
Das **Zeitbudget je Tour** ist ein Anteil f (0,2 bis 1,0) eines Rundreise-Richtwerts über alle Kunden (Nächster Nachbar plus 2-opt, einschließlich Service), geteilt durch K. Die Messreihe enthält außerdem n = 20 sowie die Budgetanteile 0,1 und 0,7; diese Zellen sind in der App nicht einstellbar (Tab Messreihe). Prämien: **gleich** (10), **gestreut** (lognormal, Mittel 60, Streuung 0,6) oder **fern = wertvoll** (20 + 1,2 × Abstand zum Depot, mit etwas Rauschen).
Ziel: die Prämiensumme der bedienten Kunden maximieren; jeder Kunde höchstens einmal, jede Tour (Fahrt, Service, Rückkehr) höchstens so lang wie das Budget. Formeln stehen im 📐-Expander der App. Alle Instanzen sind
deterministisch (Zufalls-Seed).

## Methodik

- **Verhältnis-Greedy** (`greedy_ratio`): wiederholt den Kunden mit der größten Prämie je Zusatzzeit an der günstigsten zulässigen Stelle einfügen. **Höchste Prämie zuerst** (`greedy_prize`): nach Prämie sortieren, jeweils günstigste zulässige Stelle.
- **Lokalsuche** (`local_search`, Zugart-Schalter): *Routenzüge* (2-opt, Verschieben, Tauschen; ändern die Kundenmenge nie), *Einfügen* (freie Zeit füllen), *Ersetzen* (bedienten gegen unbedienten Kunden mit höherer Prämie tauschen).
- **Eigene Suche (ILS)** (`ils`): einige Kunden entfernen (ein Stück Tour oder zufällige), verrauscht wieder einfügen, Lokalsuche, Übernahme, wenn nicht schlechter; deterministisch bei gleichem Zufalls-Seed und gleicher Iterationszahl.
- **OR-Tools** (`solve_ortools`): Routing mit Strafe für nicht bediente Kunden; *zeitgleich* heißt, dass OR-Tools so lange läuft wie der ILS auf derselben Instanz (mindestens 5, höchstens 30 Sekunden). *Standard*: Guided Local Search, Strafe 1000 × Prämie. *Abgestimmt*: Tabu-Suche, Warmstart aus dem Verhältnis-Greedy, neun zusätzliche Operatoren,
  Strafe 3 × 60 × Prämie ÷ mittlere Prämie; die Einstellung wurde auf getrennten Instanzen (Zufalls-Seeds 1000 bis 1011) aus acht Kandidaten gewählt. Die Spalten „abgestimmt“ bei gestreuten Prämien stammen aus Läufen mit Strafe 3 × Prämie ohne Normierung (bei Mittel 60 nahezu dieselbe Skala); die Normierung kam nach dem Einbruch bei gleichen Prämien dazu, die Zellen „gleich“ und „fern“ wurden mit ihr neu gemessen.
- **CP-SAT** (`solve_cpsat`): Mehrfach-Kreis mit Selbstschleife für „nicht bedient“, ein Worker, Warmstart aus der eigenen Suche, liefert Status und Schranke; in der App nur bis 25 Kunden angeboten.
- **Bester bekannter Wert** = Maximum aller Verfahren auf der Instanz (bei bewiesenem Optimum das Optimum). **Anteil am Besten** = Prämie ÷ bester Wert; „Punkte“ sind Prozentpunkte dieses Anteils.

## Befunde (gemessen, keine Behauptungen)

Die Zahlen stammen aus der Vorab-Messreihe (meist Zufalls-Seeds 0 bis 29, 30 Instanzen je Zelle, Mittel über die Instanzen; ± ist der Standardfehler) und stehen in `data/gwt_results.json`; abweichende Instanzzahlen, Seeds und Quellen (`data/gwt_ils_budget.json`) stehen in der jeweiligen Zeile. `tests/test_claims.py` prüft die Zahlen dieses Abschnitts gegen die Ergebnisdatei (Zähl- und Instanzangaben eingeschlossen), nicht gegen die Rohdaten der Messreihe.

| Frage | Befund |
|---|---|
| Wie weit liegen die Verfahren auseinander? (25 Kunden, 2 Fahrzeuge, Budgetanteil 0,5, gestreute Prämien) | Anteil am besten bekannten Wert: höchste Prämie zuerst 87,4 %, Verhältnis-Greedy 92,7 %, plus Lokalsuche 96,8 %, OR-Tools (Standard) 95,7 %, OR-Tools (abgestimmt, zeitgleich) 98,5 %, eigene Suche (ILS) 99,9 % |
| Gibt es einen Kipppunkt über dem Budget? (25 Kunden, 2 Fahrzeuge, gestreut, Budgetanteil 0,3 bis 1,0, 7 Zellen) | Oberhalb von Budgetanteil 0,3 nein: der Rückstand des Verhältnis-Greedy liegt in diesen 7 Zellen zwischen 5,2 und 8,1 Punkten; bei Budgetanteil 0,2 sind es 2,9 Punkte, bei 0,1 sind alle Instanzen trivial (der Anstieg liegt davor, zwischen 0,2 und 0,4) |
| Wo entsteht die Auswahl? (25 Kunden, 2 Fahrzeuge, Budgetanteil 0,4, gestreut) | Routenzüge allein ändern die Kundenmenge in 30 von 30 Instanzen nicht (über alle 7 Ablationszellen, das sind 25 Kunden mit Budgetanteil 0,4 und 0,7 in drei Prämienarten sowie 40 Kunden: 210 von 210) und sparen 1,9 % Fahrzeit; Einfügen +1,0 ± 0,6 Punkte, Ersetzen weitere +2,1 ± 0,8 (je gegenüber der Vorstufe; Routenzüge ändern die Prämie nicht); im ILS bringt Ersetzen +0,1 ± 0,1 Punkte gegenüber dem ILS ohne Ersetzen, Einfügen im Lokalsuchschritt +2,4 ± 0,6 gegenüber dem ILS nur mit Routenzügen |
| Wann reicht Greedy mit Lokalsuche? (19 Zellen des Haupt-Sweeps) | In 3 Zellen höchstens 2 Punkte hinter dem Besten, in 11 Zellen zwischen 2 und 6 Punkten, in 5 Zellen mehr als 6 Punkte (Schwellen gesetzt, nicht hergeleitet); die 5 Zellen: „fern = wertvoll“ (2), gleiche Prämien (2), 60 Kunden; die 3 Zellen mit höchstens 2 Punkten sind knappe Budgets, darunter die triviale Zelle mit Budgetanteil 0,1; die 19 Zellen sind ausgewählte Szenarien, kein Querschnitt |
| Wie weit liegt OR-Tools hinter dem ILS? (Budgetanteil 0,5, gestreut, 2 Fahrzeuge, n = 20 / 40 / 60) | abgestimmt und zeitgleich +2,3 ± 0,7 / +3,7 ± 0,7 / +6,5 ± 0,9 Punkte; mit der Standard-Einstellung bei 1 Fahrzeug, gestreuten Prämien und 40 bis 60 Kunden +13,4 bis +14,8 Punkte (3 Zellen: 40 Kunden bei Budgetanteil 0,4 und 0,5, 60 Kunden bei 0,5) |
| Hängt das an der Prämienart? (25 Kunden, 2 Fahrzeuge, Budgetanteil 0,4) | „fern = wertvoll“: ILS − OR-Tools +6,7 ± 1,1 (Standard) bzw. +4,8 ± 0,8 (abgestimmt); gleiche Prämien: +0,3 ± 0,3 (Standard) bzw. +3,9 ± 1,2 (abgestimmt, schlechter als Standard); bei Budgetanteil 0,7: +2,0 (Standard) bzw. +3,4 (abgestimmt) |
| Wie oft schlägt OR-Tools (abgestimmt, zeitgleich) den ILS? (840 Instanzen der Sweeps) | in 1 von 840 Instanzen strikt besser (mit der Standard-Einstellung in 4 von 840); gleichauf mit dem ILS in 337 von 831 nicht leeren Instanzen (9 Instanzen sind leer, das heißt: kein Kunde erreichbar) |
| Wie weit liegt der ILS vom Optimum? (1 Fahrzeug, 20 Kunden, Budgetanteil 0,5, 20 Instanzen, exaktes Optimum) | ILS 100,0 % des Optimums (unter dem Optimum in 0 von 20), Verhältnis-Greedy 92,9 % (16 von 20), plus Lokalsuche 94,8 % (14 von 20), OR-Tools (Standard) 87,6 % (17 von 20) |
| Wie weit beweist CP-SAT? (25 Kunden, 2 Fahrzeuge, gestreut, 30 s, ein Worker) | Optimum bewiesen in 30 / 30 / 23 / 3 / 0 / 0 / 0 / 5 von 30 Instanzen bei Budgetanteil 0,2 / 0,3 / 0,4 / 0,5 / 0,65 / 0,7 / 0,8 / 1,0 (8 Zellen); Schranke bei Budgetanteil 0,5 im Mittel 80 % über dem besten bekannten Wert der nicht bewiesenen Instanzen |
| Lässt sich der ILS verbessern? (7 Varianten, 5 s, getrennte Instanzen) | keine der 7 Varianten ist im Mittel besser: der jetzige ILS liegt bei 99,92 % des Besten, die beste Variante bei 99,68 %, ein zehnmal längerer Lauf des jetzigen ILS (kein Variantenkandidat) bei 99,97 %; ILS mit 30000 statt 3000 Iterationen findet in 5 von 30 Instanzen mehr (n = 40 und 60) |
| Wirkt die Abstimmung von OR-Tools? (8 Kandidaten, 5 Zellen mit je 12 Instanzen = 60 Instanzen, Zufalls-Seeds 1000 bis 1011) | gewählt wurde die Einstellung mit 96,48 % des ILS gegen 94,52 % für die Standard-Einstellung (gewählt und bewertet auf denselben Instanzen; die Wirkung zeigt der Vergleich der Spalten in der Messreihe: abgestimmter Rückstand kleiner in 21 von 28 Zellen, größer in 6, gleich in 1) |
| Wie gut ist der ILS bei kleinem Rechenbudget? (2 Fahrzeuge, Budgetanteil 0,5, gestreut, je 10 Instanzen) | bei 300 Iterationen im Mittel über 10 Instanzen mindestens 99,4 % des besten der drei Läufe mit 300, 1000 und 3000 Iterationen (n = 15, 25, 40, 60; bei n = 60 die schlechteste Instanz 95,1 %), Rechenzeit bei n = 60 im Mittel 2,7 s statt 27,4 s bei 3000 Iterationen |

## Ehrliche Grenzen

- **Keine Zeitfenster, keine Cluster:** Orte gleichverteilt, Fahrzeiten deterministisch, eine Tour je Fahrzeug; Prämien und ihr Verhältnis zur Fahrzeit frei gewählt. Mit Zeitfenstern (Team Orienteering mit Zeitfenstern) ist die Reihenfolge auch eine Zulässigkeitsfrage; dazu sagt die Messreihe nichts.
- **Der ILS ist mein eigenes Verfahren und stellt meist den „besten bekannten Wert“:** sein Anteil ist per Konstruktion nahe 100 %. Bewiesen ist das Optimum nur bei kleinen Touren (wenige Kunden je Fahrzeug oder knappes Budget); wo es nicht bewiesen ist, kann es höher liegen
  (der Konvergenzvergleich begrenzt den Fehler gegenüber einem zehnmal längeren eigenen Lauf, nicht gegenüber dem Optimum).
- **OR-Tools nur in zwei Einstellungen:** die Aussagen gelten für diese Einstellungen, nicht für das Verfahren. Die abgestimmte Einstellung überträgt sich bei 25 Kunden und 2 Fahrzeugen nicht auf gleiche Prämien (Budgetanteil 0,4: deutlich schlechter als Standard, 0,7: weniger). Der abgestimmte Rückstand ist in 21 von 28 Zellen kleiner als der Standard-Rückstand, in 6 größer (gleiche Prämien, 15 und 20 Kunden, 4 Fahrzeuge) und in 1 gleich.
  Ob weitere Einstellungen (anderes Dimensionsmodell, Mehrfachstart, mehr Threads) oder längere Läufe den Rückstand weiter senken, wurde nicht gemessen.
- **Eine Live-Instanz ist kein Beleg.** Die Meldungen der App stützen sich auf die vorgerechnete Zelle; ist die eingestellte Kombination nicht gemessen, steht die nächstliegende gemessene Zelle dort und die App sagt es.
- **Rechenzeiten** stammen vom Entwicklungsrechner; OR-Tools und CP-SAT sind zeitlimitiert und nicht bitgleich reproduzierbar (die Tests prüfen nur Invarianten).
- **Die Schwellen der Meldung** (2 und 6 Punkte) sind gesetzt, nicht hergeleitet.

## Verifikation

- **Kern:** Handinstanz (Gerade, Optimum 13), Zulässigkeitsprüfer, Stufen der Lokalsuche (Routenzüge ändern die Menge nie, Stufen monoton, Lokalsuche idempotent), ILS reproduzierbar; Randfälle (kein Kunde erreichbar, genau ein Kunde, Budget genau an der Grenze, Gleichstände, ein und vier Fahrzeuge).
- **Orakel:** `tests/test_oracle_gewinn_touren.py` rechnet das Optimum auf Kleinstinstanzen mit einem anderen Weg (Held-Karp je Teilmenge plus Partitions-DP), prüft, dass kein Verfahren darüber liegt und CP-SAT dasselbe Optimum beweist,
  vergleicht den Greedy mit einer unabhängigen Neuimplementierung (Brüche) und rechnet Halteliste, Anteil am Besten und Skalierung des Budgets nach.
- **Messreihe:** der Kern ist wörtlich aus der Vorab-Messreihe übernommen (26 Prüfungen dort, darunter dasselbe Orakel auf 12 Instanzen); `tests/test_results.py` und `tests/test_claims.py` prüfen die Ergebnisdatei und jede Zahl dieses README.
- **Presets:** vollständig, Werte sind gemessene Stufen, Seeds außerhalb der Messreihe, Abnahmekriterium je Preset an der angezeigten Instanz (`tests/test_stories.py`, `tools/PRESET_SWEEP.md`).
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jede Stufe jedes Reglers, OR-Tools- und Optimum-Knopf, jede Ansicht), Layout (Schnellstart oben, fester Kopf, aktives Preset hervorgehoben) und Footer-Test.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App |
| `gwt_scenario.py` | Instanz (Depot, Kunden, Prämien, Budget), Bewertung und Zulässigkeitsprüfer |
| `gwt_algorithm.py` | Kern: Greedy, Lokalsuche mit Zugart-Schaltern, ILS |
| `gwt_solvers.py` | OR-Tools (zwei Einstellungen) und CP-SAT (Importe erst beim Aufruf) |
| `gwt_evaluation.py` | Live-Analyse (Treppe der Verfahren), Kennzahlen, Verdikte als reine Funktionen, Halteliste |
| `gwt_results.py` | Laden und Auswerten der vorgerechneten Messreihe, Zellen-Zuordnung |
| `gwt_constants.py` | Regler-Stufen, feste Annahmen, Farben, Presets |
| `gwt_presets.py` | Permalink (Begrenzen, Einrasten), Presets, Zufalls-Seed-Button |
| `gwt_stories.py` | Abnahmekriterien der Presets |
| `gwt_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `gwt_pdf_export.py` | Tourenplan als PDF (fpdf2) |
| `gwt_layout.py` | Fester Kopf (Stylesheet) |
| `data/gwt_results.json` | Aggregate der Vorab-Messreihe (28 Zellen, Ablation, Optimum, Varianten, Abstimmung) |
| `data/gwt_ils_budget.json` | Güte und Zeit des ILS bei 300 / 1000 / 3000 Iterationen |
| `tools/dump_results.py` | erzeugt `gwt_results.json` aus den Dateien der Messreihe |
| `tools/measure_ils_budget.py` | erzeugt `gwt_ils_budget.json` |
| `tools/find_preset_seeds.py`, `tools/PRESET_SWEEP.md` | Suche der Preset-Seeds und ihr Bericht |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `tests/` | Handinstanz, Randfälle, Orakel, Verdikte, Ergebnisdatei, Zahlen des README, Presets, Stories, Layout, AppTest-Smoke-Test, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Zeitfenster** (Team Orienteering mit Zeitfenstern), Wartezeiten, unsichere Fahrzeiten, mehrere Touren je Fahrzeug.
- **Online-Eingang neuer Kunden** und Annahmeentscheidungen im Tagesverlauf: das ist `nahverkehr-demo`.
- **Weitere Verfahren** (ALNS, genetische Verfahren, Schnittebenen oder Branch-and-Price für einen Beweis bei 40 Kunden und wenigen Fahrzeugen).
- **Echte Straßennetze und Kalibrierung an echten Daten.**

## Verwandte Demos mit demselben mathematischen Modell

- [`vrp-demo`](https://github.com/sebastian-hanisch/vrp-demo): Tourenplanung mit allen Kunden (nur die Reihenfolge, keine Auswahl).
- [`alns-demo`](https://github.com/sebastian-hanisch/alns-demo) und [`vrp-nachbarschaften-demo`](https://github.com/sebastian-hanisch/vrp-nachbarschaften-demo): dieselbe Verfahrensfamilie (Entfernen und Neueinfügen, Nachbarschaften), aber für Touren, die alle Stopps bedienen.
- [`fptas-rucksack-demo`](https://github.com/sebastian-hanisch/fptas-rucksack-demo): Auswahl unter einer Budgetgrenze ohne Route.
- [`nahverkehr-demo`](https://github.com/sebastian-hanisch/nahverkehr-demo): dasselbe Prize-Collecting-Modell als Hindsight-Orakel einer Online-Annahme; [`auftragsallianz-demo`](https://github.com/sebastian-hanisch/auftragsallianz-demo) nennt das Team-Orienteering-Kriterium der Auftragsauswahl als nicht umgesetzt.

## Reproduktion der Messreihe

Die Skripte der Vorab-Messreihe (Instanz, Verfahren, Sweeps, Abstimmung, Ablation, Konvergenz) liegen im Portfolio-Ordner (`tourenplanung-planung/messreihe_gewinntouren/`), nicht in diesem Repo. `tools/dump_results.py` verdichtet
deren Ausgaben zu `data/gwt_results.json`. Der Haupt-Sweep (570 Instanzen) dauerte rund 18 Minuten auf 14 Kernen, die n × K-Matrix (270 Instanzen) rund 5 Minuten, die Wiederholung mit abgestimmtem OR-Tools rund 10 Minuten.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas, OR-Tools und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Tourenplanung optimieren](https://sebastianhanisch.net/tourenplanung-optimierung.html).
