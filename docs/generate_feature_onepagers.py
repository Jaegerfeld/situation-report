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
    "flow_problems": {
        "de": {
            "title": "Flussproblem-Backlog",
            "tagline": "Feature B6 (VSC-1) · Der wichtigste Input der "
                       "Value-Stream-Konferenz — mit Konferenzmappe.",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Der Workshop hat es benannt: Risiken und "
                      "Flussprobleme werden geloggt, nie mitigiert — und "
                      "tauchen nächstes PI wieder auf. Der Backlog macht "
                      "dieses Muster messbar: Jedes Problem zählt, in wie "
                      "vielen Konferenzen es schon auf dem Tisch lag. "
                      "Ungelöste Probleme ab der dritten Konferenz "
                      "eskalieren sichtbar — sortiert zuerst, roter Zähler."),
                ("h", "So benutzt du es"),
                ("code", "// flow_problems.json je Solution, in der Config: \"flow_problems\": \"...\"\n"
                         "{\"problems\": [{\"id\": \"FP-1\",\n"
                         "  \"title\": \"Test-environment provisioning takes weeks\",\n"
                         "  \"status\": \"open\", \"conferences\": 3,\n"
                         "  \"value_streams\": [\"ART A\", \"ART B\"],\n"
                         "  \"resolution_commitment\": \"...\", \"follow_up_pi\": \"PI 5\"}]}\n\n"
                         "python -m portfolio portfolio.json --conference mappe.html"),
                ("h", "Was der Report zeigt"),
                ("li", "Survivor-Regel: ungelöst und ≥ 3 Konferenzen → oben "
                       "und rot — Nicht-Mitigation wird sichtbar statt "
                       "anekdotisch"),
                ("li", "Cross-VS wird abgeleitet, nie behauptet: mehr als "
                       "ein betroffener Value Stream"),
                ("li", "Commitment und Wiedervorlage-PI je Problem — "
                       "Zusagen bekommen ein Gedächtnis"),
                ("li", "Konferenzmappe: druckbarer Pre-Read mit den "
                       "Sitzungs-Inputs (Daten, Impediments samt "
                       "ROAM/Dependencies, Business Objectives)"),
                ("h", "Leitplanken"),
                ("p", "Der Konferenzen-Zähler wird von Menschen gepflegt — "
                      "das Werkzeug hat keine Historie und erfindet keine. "
                      "Owner sind Teams, keine Personen. Portfolio "
                      "aggregiert die Backlogs aller Solutions mit "
                      "Solution-Spalte."),
            ],
        },
        "en": {
            "title": "Flow-Problem Backlog",
            "tagline": "Feature B6 (VSC-1) · The Value-Stream Conference's "
                       "most important input — with a conference pre-read.",
            "sections": [
                ("h", "What is it?"),
                ("p", "The workshop named it: risks and flow problems get "
                      "logged, never mitigated — and return next PI. The "
                      "backlog makes that pattern measurable: every problem "
                      "counts in how many conferences it has been on the "
                      "table. Unresolved problems from the third conference "
                      "on escalate visibly — sorted first, red counter."),
                ("h", "How to use it"),
                ("code", "// flow_problems.json per solution, in the config: \"flow_problems\": \"...\"\n"
                         "{\"problems\": [{\"id\": \"FP-1\",\n"
                         "  \"title\": \"Test-environment provisioning takes weeks\",\n"
                         "  \"status\": \"open\", \"conferences\": 3,\n"
                         "  \"value_streams\": [\"ART A\", \"ART B\"],\n"
                         "  \"resolution_commitment\": \"...\", \"follow_up_pi\": \"PI 5\"}]}\n\n"
                         "python -m portfolio portfolio.json --conference preread.html"),
                ("h", "What the report shows"),
                ("li", "Survivor rule: unresolved and ≥ 3 conferences → on "
                       "top and red — non-mitigation becomes visible "
                       "instead of anecdotal"),
                ("li", "Cross-VS is derived, never asserted: more than one "
                       "affected value stream"),
                ("li", "Commitment and follow-up PI per problem — promises "
                       "get a memory"),
                ("li", "Conference pre-read: printable bundle of the "
                       "meeting inputs (data, impediments with "
                       "ROAM/dependencies, business objectives)"),
                ("h", "Guardrails"),
                ("p", "The conference counter is maintained by people — the "
                      "tool has no history and invents none. Owners are "
                      "teams, not persons. A portfolio aggregates all "
                      "solutions' backlogs with a Solution column."),
            ],
        },
    },
    "metric_sources": {
        "de": {
            "title": "Externe Kennzahlen-Quellen",
            "tagline": "Feature C1/C2 · SLO, DORA und Code-Qualität — aus "
                       "austauschbaren, kombinierbaren Quellen.",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Das Lagebild bekommt zwei neue Sichten: „Service "
                      "Levels & Error Budgets“ (Zuverlässigkeit gemessen "
                      "und budgetiert) und „Delivery Performance (DORA) & "
                      "Code Quality“ (wie gesund liefert das System). Die "
                      "Daten kommen aus einem steckbaren Quellen-Framework "
                      "— der Report sieht nie einen Hersteller, nur "
                      "normierte Records. Status- und Tier-Urteile fallen "
                      "zentral: Jede Quelle wird nach derselben Regel "
                      "beurteilt."),
                ("h", "So benutzt du es"),
                ("code", "python -m sources providers\n"
                         "python -m sources fetch --kind slo  --config quellen.json --output slo.json\n"
                         "python -m sources fetch --kind dora --config github.json  --output dora.json\n"
                         "# dann in der Solution-Config: \"slo\": \"slo.json\", \"dora\": \"dora.json\""),
                ("p", "Eine Config darf MEHRERE Quellen listen — die "
                      "Records landen in einem Register, jede Zeile behält "
                      "ihre Herkunft. Quellen sind jederzeit austauschbar."),
                ("h", "Mitgelieferte Provider"),
                ("li", "file / csv — universeller Weg 1: jedes System ist "
                       "per JSON- oder CSV-Export anbindbar, ganz ohne "
                       "API-Freigabe"),
                ("li", "prometheus — De-facto-Standard des Monitorings "
                       "(SLO/SLI per PromQL-Query)"),
                ("li", "github — DORA aus Deployments, PRs und "
                       "Incident-Issues abgeleitet (Näherungen dokumentiert "
                       "und konfigurierbar)"),
                ("li", "gitlab — die einzige native DORA-API am Markt "
                       "(zweite Referenz: der Austauschbarkeits-Beweis)"),
                ("li", "sonarqube — Coverage, Maintainability-Rating, "
                       "kritische Verstöße"),
                ("h", "Leitplanken"),
                ("p", "Eine neue Quelle ist EINE Datei in "
                      "sources/providers/ (~30 Zeilen) — die Auto-Discovery "
                      "findet sie. Schritt-für-Schritt mit Beispiel: "
                      "Tutorial „Eine eigene Datenquelle anbinden“ "
                      "(sources_Tutorial_DE.pdf / online unter Tutorials). "
                      "Tokens nur aus Umgebungsvariablen, nie gespeichert, "
                      "nie geloggt; 401/403 verweist auf die ggf. fehlende "
                      "Freigabe und den Datei-Weg. Nur Standardbibliothek."),
            ],
        },
        "en": {
            "title": "External Metric Sources",
            "tagline": "Feature C1/C2 · SLO, DORA and code quality — from "
                       "exchangeable, combinable sources.",
            "sections": [
                ("h", "What is it?"),
                ("p", "The situational picture gains two new views: "
                      "'Service Levels & Error Budgets' (reliability "
                      "measured and budgeted) and 'Delivery Performance "
                      "(DORA) & Code Quality' (how healthily the system "
                      "delivers). The data comes from a pluggable source "
                      "framework — the report never sees a vendor, only "
                      "normalised records. Status and tier judgements are "
                      "central: every source is judged by the same rule."),
                ("h", "How to use it"),
                ("code", "python -m sources providers\n"
                         "python -m sources fetch --kind slo  --config sources.json --output slo.json\n"
                         "python -m sources fetch --kind dora --config github.json  --output dora.json\n"
                         "# then in the solution config: \"slo\": \"slo.json\", \"dora\": \"dora.json\""),
                ("p", "A config may list SEVERAL sources — the records land "
                      "in one register, each row keeping its origin. "
                      "Sources stay exchangeable at any time."),
                ("h", "Shipped providers"),
                ("li", "file / csv — universal path 1: any system attaches "
                       "via JSON or CSV export, no API approval needed"),
                ("li", "prometheus — the de-facto monitoring standard "
                       "(SLO/SLI via PromQL query)"),
                ("li", "github — DORA derived from deployments, PRs and "
                       "incident issues (approximations documented and "
                       "configurable)"),
                ("li", "gitlab — the only native DORA API on the market "
                       "(second reference: the exchangeability proof)"),
                ("li", "sonarqube — coverage, maintainability rating, "
                       "critical violations"),
                ("h", "Guardrails"),
                ("p", "A new source is ONE file in sources/providers/ "
                      "(~30 lines) — auto-discovery picks it up. Step by "
                      "step with an example: tutorial 'Attaching your own "
                      "data source' (sources_Tutorial_EN.pdf / online under "
                      "Tutorials). Tokens only from environment variables, "
                      "never stored, never logged; 401/403 points to the "
                      "possibly missing approval and to the file path. "
                      "Standard library only."),
            ],
        },
    },
    "get_data": {
        "de": {
            "title": "Get Data",
            "tagline": "Feature C3 · Jira-Daten holen — zwei gleichwertige "
                       "Wege, ein Artefakt.",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Das Lagebild braucht Rohdaten aus Jira. get_data "
                      "bietet dafür zwei Wege, die bewusst gleichwertig "
                      "sind: den automatischen REST-Abruf — und den "
                      "manuellen Export, denn in großen Organisationen kann "
                      "die Freigabe für API-Zugriffe lange dauern. Beide "
                      "Wege münden in derselben JSON-Datei; die Pipeline "
                      "dahinter ist identisch."),
                ("h", "So benutzt du es"),
                ("code", "set JIRA_TOKEN=IhrAPIToken\n"
                         "python -m get_data fetch --url https://firma.atlassian.net ^\n"
                         "  --project ART_A --email name@firma.de --output ART_A.json\n"
                         "python -m get_data check ART_A_merged.json   # Export pruefen"),
                ("p", "Oder per GUI: python -m get_data (bzw. die "
                      "Get-Data-Karte im Launcher) — ein Fenster, beide "
                      "Wege als Umschalter: „Jira REST-Abruf“ und "
                      "„Vorhandener Export“ mit Prüfung."),
                ("h", "Was es kann"),
                ("li", "API v3 (Cursor) und v2 (Offset) mit vollständiger "
                       "Paginierung, expand=changelog immer gesetzt"),
                ("li", "Anmeldung Cloud (E-Mail + API-Token) oder "
                       "Server/DC (Bearer-PAT)"),
                ("li", "Export-Prüfung erkennt die Klassiker: fehlender "
                       "Changelog, vergessene Folgeseiten, Duplikate"),
                ("li", "Fehlermeldungen zeigen bei 401/403 auch auf die "
                       "fehlende Freigabe — und den manuellen Ausweichweg"),
                ("h", "Leitplanken"),
                ("p", "Das Token wird nie gespeichert und nie geloggt: CLI "
                      "liest es aus einer Umgebungsvariable (JIRA_TOKEN), "
                      "die GUI hält es nur im Speicher. Nur "
                      "Standardbibliothek — keine neuen Abhängigkeiten. Ein "
                      "Contract-Test garantiert: Abruf und manueller Export "
                      "derselben Daten werden identisch verarbeitet."),
            ],
        },
        "en": {
            "title": "Get Data",
            "tagline": "Feature C3 · Fetching Jira data — two equal paths, "
                       "one artifact.",
            "sections": [
                ("h", "What is it?"),
                ("p", "The situational picture needs raw data from Jira. "
                      "get_data offers two deliberately equal paths: the "
                      "automated REST fetch — and the manual export, "
                      "because in large organisations, approval for API "
                      "access can take a long time. Both paths end in the "
                      "same JSON file; the pipeline behind them is "
                      "identical."),
                ("h", "How to use it"),
                ("code", "set JIRA_TOKEN=YourAPIToken\n"
                         "python -m get_data fetch --url https://company.atlassian.net ^\n"
                         "  --project ART_A --email name@company.com --output ART_A.json\n"
                         "python -m get_data check ART_A_merged.json   # validate an export"),
                ("p", "Or via the GUI: python -m get_data (or the Get Data "
                      "card in the launcher) — one window, both paths as a "
                      "toggle: 'Jira REST fetch' and 'Existing export' "
                      "with validation."),
                ("h", "What it does"),
                ("li", "API v3 (cursor) and v2 (offset) with full "
                       "pagination, expand=changelog always set"),
                ("li", "Auth for Cloud (e-mail + API token) or Server/DC "
                       "(bearer PAT)"),
                ("li", "Export validation catches the classics: missing "
                       "changelog, forgotten follow-up pages, duplicates"),
                ("li", "Error messages point 401/403 at the missing "
                       "approval too — and at the manual fallback path"),
                ("h", "Guardrails"),
                ("p", "The token is never stored and never logged: the CLI "
                      "reads it from an environment variable (JIRA_TOKEN), "
                      "the GUI keeps it in memory only. Standard library "
                      "only — no new dependencies. A contract test "
                      "guarantees: a fetch and a manual export of the same "
                      "data are processed identically."),
            ],
        },
    },
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
