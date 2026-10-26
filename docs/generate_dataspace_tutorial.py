# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt die PDF-Fassungen des Tutorials „Demo-Datenraum in einer Minute"
#   (Beta, Schnitt 4) aus den mkdocs-Seiten docs/tutorials/demo-data-room(.de).md
#   mit dem Markdown→PDF-Konverter des Tutorials „Lagebild befragen"
#   (docs/generate_ask_tutorial.py): dieselben Stile, derselbe Fuß, dieselbe
#   Bildbehandlung — ein Konverter für alle Tutorials.
#
#   Aufruf: .venv/Scripts/python.exe docs/generate_dataspace_tutorial.py
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS))

from generate_ask_tutorial import _footer, convert  # noqa: E402

PAGES = {
    "de": (DOCS / "tutorials" / "demo-data-room.de.md", DOCS / "dataspace_Tutorial_DE.pdf",
           "Demo-Datenraum in einer Minute — Tutorial", "Seite"),
    "en": (DOCS / "tutorials" / "demo-data-room.md", DOCS / "dataspace_Tutorial_EN.pdf",
           "A demo data room in one minute — tutorial", "Page"),
}


def main() -> None:
    for src, out, title, page_word in PAGES.values():
        doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=17 * mm,
                                topMargin=16 * mm, bottomMargin=18 * mm, title=title,
                                author="Robert Seebauer")
        footer = _footer(title, page_word)
        doc.build(convert(src), onFirstPage=footer, onLaterPages=footer)
        print(f"PDF erstellt: {out}")


if __name__ == "__main__":
    main()
