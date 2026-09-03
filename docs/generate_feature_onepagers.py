# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Feature-Onepager-Generator: Für jedes umgesetzte Feature entsteht ein
#   einseitiges PDF (DE + EN), das die neue Funktion kurz vorstellt und
#   erklärt — zum Weitergeben bei Vorstellungen, ohne das ganze Manual.
#   Je Feature ein Eintrag in ONEPAGERS (slug + Sprachfassungen); das Skript
#   schreibt docs/onepager/<slug>.onepager.<de|en>.pdf. Neue Features werden
#   hier ergänzt und das Skript erneut ausgeführt (Regel seit 03.09.2026).
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

_ACCENT = HexColor("#2b5b84")
_MUTED = HexColor("#555555")

_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20,
                        leading=24, textColor=_ACCENT)
_TAGLINE = ParagraphStyle("tagline", fontName="Helvetica-Oblique",
                          fontSize=10.5, leading=14, textColor=_MUTED)
_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12,
                    leading=15, spaceBefore=10, spaceAfter=3,
                    textColor=_ACCENT)
_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.8,
                       leading=13.2)
_CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.6, leading=11.5,
                       backColor=HexColor("#f4f4f4"), borderPadding=6,
                       leftIndent=4, spaceBefore=4, spaceAfter=4)
_FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, leading=10,
                       textColor=_MUTED)

#: Onepager je Feature: slug -> {lang -> {title, tagline, sections, footer_note}}
#: sections: Liste aus ("h", Text) | ("p", Text) | ("code", Text) | ("li", Text)
ONEPAGERS: dict[str, dict[str, dict]] = {
    "delta_briefing": {
        "de": {
            "title": "Delta-Briefing",
            "tagline": "Feature D2 (deterministischer Kern) · Was hat sich "
                       "seit dem letzten Stand geändert — und wo kippt etwas?",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Ein Bericht zeigt einen Zustand; ein Lagedienst zeigt "
                      "die Veränderung. Das Delta-Briefing vergleicht zwei "
                      "eingefrorene Report-Stände (Snapshots) desselben "
                      "Solution- oder Portfolio-Lagebilds und beantwortet die "
                      "Führungsfrage „Was hat sich geändert?“ — ohne dass "
                      "jemand zwei Reports nebeneinanderlegen muss."),
                ("h", "So benutzt du es"),
                ("code", "python -m portfolio portfolio.json --snapshot heute.json\n"
                         "python -m portfolio --delta vorher.json heute.json --output delta.html\n"
                         "# Demo: im Szenario liegen snapshot_prev/now.json schon bereit"),
                ("p", "Oder per GUI: Im Solutions-&-Portfolios-Fenster "
                      "„Snapshot speichern …“ und „Delta-Briefing …“; im "
                      "Testdaten-Generator öffnet „Delta-Briefing öffnen“ "
                      "das Demo-Briefing mit einem Klick."),
                ("p", "--snapshot friert Kennzahlen, Quell-Konfidenz und alle "
                      "fünf Governance-Register als kleines JSON ein "
                      "(--as-of setzt das Beobachtungsdatum). --delta braucht "
                      "keine Config; Ausgabe als HTML-Seite, Markdown-Datei "
                      "(--output *.md) oder Text auf der Konsole."),
                ("h", "Was das Briefing zeigt"),
                ("li", "Kennzahl-Deltas je Einheit und gesamt — auf "
                       "Anzeigegenauigkeit, unsichtbare Änderungen entfallen"),
                ("li", "Durchsatz im Zeitraum („+59 Items in 14 Tagen“)"),
                ("li", "Konfidenz-Wechsel je Datenquelle (z. B. medium → low)"),
                ("li", "Je Register: Neues, Entfallenes, Statusübergänge — "
                       "Verschlechterungen zuerst und rot"),
                ("li", "Frisch Überfälliges: nur echte Kipp-Punkte seit dem "
                       "letzten Stand, kein Dauer-Alarm"),
                ("li", "„Keine Änderungen“ wird ausdrücklich gesagt — "
                       "Stille ist Information"),
                ("h", "Leitplanken"),
                ("p", "Alles deterministisch — gleiche Snapshots, gleiches "
                      "Briefing. Die optionale KI-Narration (D2 Teil 2) ist "
                      "bewusst getrennt und noch nicht gebaut: Das LLM wird "
                      "texten, nie rechnen; das Markdown des Briefings ist "
                      "ihr künftiger Eingabe-Contract. Owner sind Teams, "
                      "keine Personen."),
            ],
        },
        "en": {
            "title": "Delta Briefing",
            "tagline": "Feature D2 (deterministic core) · What changed since "
                       "the last state — and where is something tipping?",
            "sections": [
                ("h", "What is it?"),
                ("p", "A report shows a state; a situation service shows the "
                      "change. The delta briefing compares two frozen report "
                      "states (snapshots) of the same solution or portfolio "
                      "picture and answers the leadership question 'what "
                      "changed?' — without anyone laying two reports side "
                      "by side."),
                ("h", "How to use it"),
                ("code", "python -m portfolio portfolio.json --snapshot today.json\n"
                         "python -m portfolio --delta before.json today.json --output delta.html\n"
                         "# Demo: the scenario ships snapshot_prev/now.json ready to use"),
                ("p", "Or via the GUI: the Solutions & Portfolios window "
                      "carries 'Save snapshot …' and 'Delta briefing …'; in "
                      "the test-data generator, 'Open Delta Briefing' opens "
                      "the demo briefing with one click."),
                ("p", "--snapshot freezes metrics, source confidence and all "
                      "five governance registers into a small JSON (--as-of "
                      "pins the observation date). --delta needs no config; "
                      "output as an HTML page, a Markdown file (--output "
                      "*.md), or text on the console."),
                ("h", "What the briefing shows"),
                ("li", "Metric deltas per unit and in total — at display "
                       "precision, invisible changes are dropped"),
                ("li", "Throughput in the period ('+59 items in 14 days')"),
                ("li", "Confidence transitions per data source (e.g. "
                       "medium → low)"),
                ("li", "Per register: new, removed, status transitions — "
                       "worsenings first and in red"),
                ("li", "Newly overdue items: only genuine flips since the "
                       "last state, no standing alarm"),
                ("li", "'No changes' is stated explicitly — silence is "
                       "information"),
                ("h", "Guardrails"),
                ("p", "Everything deterministic — same snapshots, same "
                      "briefing. The optional AI narration (D2 part 2) is "
                      "deliberately separate and not built yet: the LLM will "
                      "write, never calculate; the briefing's Markdown is its "
                      "future input contract. Owners are teams, not persons."),
            ],
        },
    },
}


def _build(slug: str, lang: str, spec: dict, out_dir: Path) -> Path:
    """Render one onepager PDF."""
    path = out_dir / f"{slug}.onepager.{lang}.pdf"
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=14 * mm,
        title=spec["title"], author="Robert Seebauer")
    story: list = [
        Paragraph(spec["title"], _TITLE),
        Spacer(1, 2 * mm),
        Paragraph(spec["tagline"], _TAGLINE),
        Spacer(1, 1 * mm),
        HRFlowable(width="100%", thickness=1, color=_ACCENT),
    ]
    for kind, text in spec["sections"]:
        if kind == "h":
            story.append(Paragraph(text, _H))
        elif kind == "p":
            story.append(Paragraph(text, _BODY))
        elif kind == "li":
            story.append(Paragraph(f"•  {text}", _BODY))
        elif kind == "code":
            story.append(Preformatted(text, _CODE))
    story += [
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=0.5, color=_MUTED),
        Paragraph(
            f"SituationReport {_VERSION} · BSD-3-Clause · "
            f"github.com/Jaegerfeld/situation-report · "
            f"jaegerfeld.github.io/situation-report", _FOOT),
    ]
    doc.build(story)
    return path


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "onepager"
    out_dir.mkdir(exist_ok=True)
    for slug, langs in ONEPAGERS.items():
        for lang, spec in langs.items():
            path = _build(slug, lang, spec, out_dir)
            print(f"PDF erstellt: {path}")


if __name__ == "__main__":
    main()
