"""Sucht je Preset den ersten Seed ab 101, dessen Live-Instanz das Abnahmekriterium aus gwt_stories.py erfüllt, und schreibt tools/PRESET_SWEEP.md.

    python tools/find_preset_seeds.py

Seeds 0 bis 29 gehören der Messreihe, 1000 bis 1011 der Abstimmung: gesucht wird ab 101 und nur bis 999."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import gwt_constants as C  # noqa: E402
import gwt_evaluation as E  # noqa: E402
import gwt_stories as ST  # noqa: E402


def main():
    lines = ["# Preset-Abstimmung (tools/find_preset_seeds.py)", "",
             "Je Preset der erste Seed ab 101, dessen Live-Instanz das Kriterium aus `gwt_stories.py` erfüllt. Die Aussage der Demo stützt sich nicht darauf (eine Instanz), sondern auf die Messreihe.", "",
             "| Preset | Seed | gesuchte Seeds | Kriterium |", "|---|---|---|---|"]
    for name, story in ST.STORIES.items():
        p = C.PRESETS[name]
        found = None
        for tries, seed in enumerate(range(101, 1000), 1):
            a = E.analyse(E.Settings(p["n"], p["k"], p["f"], p["ptype"], p["ils"], seed))
            if story(a):
                found = (seed, tries)
                break
        doc = " ".join((story.__doc__ or "").split())
        lines.append(f"| {name} | {found[0] if found else 'keiner'} | {found[1] if found else 'bis 999'} | {doc} |")
        print(name, found)
    (HERE / "tools" / "PRESET_SWEEP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
