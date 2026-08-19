#!/usr/bin/env python3
"""Veroeffentlicht die aktuellen Denkschriften auf der Doku-Site.

Kopiert die in MANIFEST gelisteten PDFs (aktuelle Fassungen aus dem lokalen,
untracked gepflegten ``Quellen/``-Ordner) sowie die Mindmap-SVG nach
``docs/denkschriften/``. Von dort deployt der Deploy-Docs-Workflow sie nach
https://jaegerfeld.github.io/situation-report/denkschriften/ (Merge auf main
vorausgesetzt).

Ablauf bei einem Versionssprung einer Denkschrift:
  1. MANIFEST unten auf die neuen Dateinamen aktualisieren.
  2. ``python scripts/publish_denkschriften.py`` ausfuehren (kopiert + prueft).
  3. Landing-Pages ``docs/denkschriften/index.de.md`` / ``index.md`` anpassen
     (Version, Datum, Seitenzahl, ggf. Teasertext) - das Skript erinnert daran.
  4. Alte PDF-Fassung aus ``docs/denkschriften/pdf/`` entfernen (Skript meldet
     verwaiste Dateien), Aenderungen per PR auf main bringen.
  5. Optional ``--release``: legt ein GitHub-Release ``denkschriften/<Datum>``
     mit allen aktuellen PDFs als eingefrorenem Stand an (nutzt ``gh``).

Stdlib-only; ``--release`` ruft die GitHub CLI via subprocess auf.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUELLEN = REPO / "Quellen"
TARGET = REPO / "docs" / "denkschriften"

# Aktuelle Fassungen (bei Versionssprung hier aktualisieren; DE + EN je Schrift)
MANIFEST = [
    "Denkschrift-0_Large-Solution-Management_v1.5.pdf",
    "Memorandum-0_Large-Solution-Management_v1.5.en.pdf",
    "Was-ist-ein-Lagebild_v1.0.pdf",
    "What-is-a-Situational-Picture_v1.0.en.pdf",
    "Team-of-Teams-und-Stabsausbildung_v4.2.pdf",
    "Team-of-Teams-and-Staff-Training_v4.2.en.pdf",
    "Enterprise-Architektur-und-Solution-Lagebild_v2.2.pdf",
    "Enterprise-Architecture-and-Solution-Situational-Picture_v2.2.en.pdf",
    "Architektur-Vordenker_v1.2.pdf",
    "Architecture-Thought-Leaders_v1.2.en.pdf",
    "KI-und-Lagebild_v2.1.pdf",
    "AI-and-the-Situational-Picture_v2.1.en.pdf",
]
MINDMAP_SVG = QUELLEN / "Mindmap" / "Denkschriften-Mindmap.svg"
# Ueberblicksgrafiken (Quelle -> Online-Name). EN mit -en (bleibt im Root);
# DE zusaetzlich als .de.png -> landet im de/-Baum, damit die DE-Seite lokal verlinkt.
OVERVIEW_PNGS = {
    QUELLEN / "Denkschriften-Reihe_Ueberblick.png": "Denkschriften-Reihe_Ueberblick.png",
    QUELLEN / "Memoranda-Series_Overview.en.png": "Memoranda-Series_Overview-en.png",
}
OVERVIEW_DE_COPY = (QUELLEN / "Denkschriften-Reihe_Ueberblick.png", "Denkschriften-Reihe_Ueberblick.de.png")


def online_name(name: str) -> str:
    """Online-Dateiname: ``.en.pdf`` wird zu ``-en.pdf``.

    Das mkdocs-static-i18n-Plugin (suffix-Modus) interpretiert ``.<lang>.<ext>``
    als Sprachvariante: Es streift das Suffix und legt die Datei in den Baum der
    jeweiligen Sprache (``.de.pdf`` -> ``de/.../name.pdf``). Fuer die EN-Kopien
    ist das unerwuenscht (Root ist ohnehin EN) -> Bindestrich; fuer die DE-Kopien
    ist es genau richtig (siehe ``de_copy_name``). Kanonische Quellen-/Release-
    Namen behalten das ``.en.pdf``-Schema.
    """
    return name.replace(".en.pdf", "-en.pdf")


def is_german(name: str) -> bool:
    return not name.endswith(".en.pdf")


def de_copy_name(name: str) -> str:
    """Zweitkopie einer deutschen PDF mit ``.de.pdf``-Suffix: landet im Build
    unter ``de/denkschriften/pdf/<name>.pdf`` – so bleiben Leser der deutschen
    Seite beim Download im deutschen Sprachbaum (kein Wechsel zur EN-Seite)."""
    return name[:-4] + ".de.pdf"


def sync() -> list[Path]:
    pdf_dir = TARGET / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    missing = []
    for name in MANIFEST:
        src = QUELLEN / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, pdf_dir / online_name(name))
        copied.append(pdf_dir / online_name(name))
        if is_german(name):
            shutil.copy2(src, pdf_dir / de_copy_name(name))
            copied.append(pdf_dir / de_copy_name(name))
    if missing:
        sys.exit("FEHLER - nicht in Quellen/ gefunden (MANIFEST pruefen): "
                 + ", ".join(missing))
    if MINDMAP_SVG.exists():
        shutil.copy2(MINDMAP_SVG, TARGET / MINDMAP_SVG.name)
        copied.append(TARGET / MINDMAP_SVG.name)
    else:
        print("WARNUNG: Mindmap-SVG nicht gefunden:", MINDMAP_SVG)
    for src, online in OVERVIEW_PNGS.items():
        if src.exists():
            shutil.copy2(src, TARGET / online)
            copied.append(TARGET / online)
        else:
            print("WARNUNG: Ueberblicksgrafik nicht gefunden:", src)
    if OVERVIEW_DE_COPY[0].exists():
        shutil.copy2(OVERVIEW_DE_COPY[0], TARGET / OVERVIEW_DE_COPY[1])
        copied.append(TARGET / OVERVIEW_DE_COPY[1])

    expected = {online_name(n) for n in MANIFEST} | {de_copy_name(n) for n in MANIFEST if is_german(n)}
    orphans = [p.name for p in pdf_dir.glob("*.pdf") if p.name not in expected]
    if orphans:
        print("HINWEIS - verwaiste Alt-Fassungen in docs/denkschriften/pdf/ "
              "(manuell entfernen): " + ", ".join(orphans))
    return copied


def release(date: str) -> None:
    tag = f"denkschriften/{date}"
    files = [str(TARGET / "pdf" / name) for name in MANIFEST]
    cmd = [
        "gh", "release", "create", tag, *files,
        "--title", f"Denkschriften-Stand {date}",
        "--latest=false",
        "--notes",
        "Eingefrorener Stand der Denkschriften-Reihe (alle aktuellen Fassungen, "
        "DE + EN). Aktuelle Fassungen und Uebersicht: "
        "https://jaegerfeld.github.io/situation-report/denkschriften/",
    ]
    subprocess.run(cmd, check=True)
    print(f"Release {tag} angelegt.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", action="store_true",
                    help="zusaetzlich GitHub-Release denkschriften/<Datum> anlegen")
    ap.add_argument("--date", default=_dt.date.today().isoformat(),
                    help="Datum fuer den Release-Tag (Default: heute)")
    args = ap.parse_args()

    copied = sync()
    print(f"OK: {len(copied)} Dateien nach docs/denkschriften/ synchronisiert.")
    print("Erinnerung: Landing-Pages (index.de.md / index.md) bei "
          "Versionsspruengen anpassen; Aenderungen per PR auf main bringen.")
    if args.release:
        release(args.date)


if __name__ == "__main__":
    main()
