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
    "strategic_themes": {
        "de": {
            "title": "Strategic Themes & Roadmap",
            "tagline": "Feature B7 (VSC-2) · Strategie bekommt ein Zuhause, "
                       "die Solution-Ebene ihre integrierte Roadmap.",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Zwei SAFe-Lücken aus dem Workshop: Strategic Themes "
                      "haben kein strukturiertes Zuhause, und es fehlt eine "
                      "Large-Solution-Roadmap mit Initiative-Swimlanes. "
                      "Jetzt: Themes mit Epic-Verknüpfung und eine "
                      "Roadmap-Matrix über Trains — Zeithorizont nah "
                      "granular, fern grob (P1 · P2 · Y1 · Y2 · Y3)."),
                ("h", "So benutzt du es"),
                ("code", "// themes.json, in der Config: \"themes\": \"themes.json\"\n"
                         "{\"themes\": [{\"id\": \"T-1\", \"title\": \"Digital ordering\"}],\n"
                         " \"epics\": [\n"
                         "   {\"id\": \"EP-1\", \"title\": \"Portal\", \"train\": \"ART A\",\n"
                         "    \"horizon\": \"P1\", \"theme\": \"T-1\", \"status\": \"in_progress\"},\n"
                         "   {\"id\": \"EP-9\", \"title\": \"Legacy rewrite\", \"train\": \"ART C\",\n"
                         "    \"horizon\": \"Y1\"}]}   // leeres theme = Zombie"),
                ("h", "Was der Report zeigt"),
                ("li", "Orphan-Detection in beide Richtungen: Theme ohne "
                       "Epics = „declared & forgotten“ (rot, portfolioweit "
                       "beurteilt); Epic ohne Theme = Zombie-Initiative"),
                ("li", "Tippfehler-Schutz: eine falsche Theme-Referenz ist "
                       "ein Validierungsfehler, kein stiller Zombie"),
                ("li", "Roadmap-Matrix Trains × Horizonte, Zombies rot; "
                       "Zombie-Liste darunter"),
                ("li", "Konferenzmappe: die Sicht ist Input 4 des "
                       "VSC-Pre-Reads"),
                ("li", "D2-Anschluss: Epics fließen in Snapshots — das "
                       "Delta-Briefing dokumentiert „updated roadmaps“ je "
                       "Konferenz (P2 → P1, Theme verloren → „zombie“)"),
                ("h", "Leitplanken"),
                ("p", "Horizonte sind bewusst grob in der Ferne — keine "
                      "Scheingenauigkeit über Jahre. Das Werkzeug urteilt "
                      "nur strukturell (verwaist/zombie); ob eine "
                      "Initiative strategisch richtig ist, bleibt "
                      "menschliches Urteil in der Konferenz."),
            ],
        },
        "en": {
            "title": "Strategic Themes & Roadmap",
            "tagline": "Feature B7 (VSC-2) · Strategy gets a home, the "
                       "solution level its integrated roadmap.",
            "sections": [
                ("h", "What is it?"),
                ("p", "Two SAFe gaps from the workshop: strategic themes "
                      "have no structured home, and there is no "
                      "large-solution roadmap with initiative swimlanes. "
                      "Now: themes with epic links and a roadmap matrix "
                      "across trains — near-term granular, far-term coarse "
                      "(P1 · P2 · Y1 · Y2 · Y3)."),
                ("h", "How to use it"),
                ("code", "// themes.json, in the config: \"themes\": \"themes.json\"\n"
                         "{\"themes\": [{\"id\": \"T-1\", \"title\": \"Digital ordering\"}],\n"
                         " \"epics\": [\n"
                         "   {\"id\": \"EP-1\", \"title\": \"Portal\", \"train\": \"ART A\",\n"
                         "    \"horizon\": \"P1\", \"theme\": \"T-1\", \"status\": \"in_progress\"},\n"
                         "   {\"id\": \"EP-9\", \"title\": \"Legacy rewrite\", \"train\": \"ART C\",\n"
                         "    \"horizon\": \"Y1\"}]}   // empty theme = zombie"),
                ("h", "What the report shows"),
                ("li", "Orphan detection in both directions: a theme with "
                       "no epics = 'declared & forgotten' (red, judged "
                       "portfolio-wide); an epic without a theme = zombie "
                       "initiative"),
                ("li", "Typo protection: a wrong theme reference is a "
                       "validation error, not a silent zombie"),
                ("li", "Roadmap matrix trains × horizons, zombies red; "
                       "zombie list below"),
                ("li", "Conference pre-read: the view is input 4 of the "
                       "VSC bundle"),
                ("li", "D2 hook: epics flow into snapshots — the delta "
                       "briefing documents 'updated roadmaps' per "
                       "conference (P2 → P1, theme lost → 'zombie')"),
                ("h", "Guardrails"),
                ("p", "Horizons stay deliberately coarse in the distance — "
                      "no fake precision across years. The tool judges "
                      "structure only (orphaned/zombie); whether an "
                      "initiative is strategically right remains a human "
                      "judgement in the conference."),
            ],
        },
    },
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
                      "Briefing. Die optionale KI-Narration (D2 Teil 2, "
                      "eigener Onepager) ist bewusst getrennt: Das LLM "
                      "textet, es rechnet nie; das Markdown des Briefings "
                      "ist ihr Eingabe-Contract. Owner sind Teams, "
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
                      "briefing. The optional AI narration (D2 part 2, own "
                      "one-pager) is deliberately separate: the LLM writes, "
                      "it never calculates; the briefing's Markdown is its "
                      "input contract. Owners are teams, not persons."),
            ],
        },
    },
    "art_profiles": {
        "de": {
            "title": "ART-Profile im Demo-Portfolio",
            "tagline": "Jeder Demo-ART bekommt die Regler der "
                       "Einzel-ART-Erzeugung — Ø-CT, Streuung, Fehler-Muster",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Das Demo-Portfolio erzeugte seine sechs ARTs bisher "
                      "mit festen Profilen. Jetzt lässt sich je ART alles "
                      "übersteuern, was auch die Einzel-ART-Erzeugung kann: "
                      "Anzahl Issues, durchschnittliche Cycle Time und ihre "
                      "Standardabweichung, Fertig- und To-Do-Quote, "
                      "Backflow-Wahrscheinlichkeit, die Fluss-/Fehler-Muster "
                      "(triangle, flat_triangle, cluster, batch) samt Stärke "
                      "(0–100) und die PI-Dauer. So entsteht z. B. ein "
                      "Portfolio, in dem ein ART im PI-Endspurt-Muster "
                      "liefert und ein anderer mit hoher Streuung kämpft."),
                ("h", "So benutzt du es"),
                ("code", "python -m testdata_generator --scenario portfolio "
                         "--output demo/ \\\n"
                         "    --scale m --art-profiles profile.json\n\n"
                         '# profile.json:\n'
                         '{"Alpha-1": {"mean_cycle_days": 30, '
                         '"std_cycle_days": 12,\n'
                         '             "pattern": "cluster", '
                         '"pattern_strength": 80}}'),
                ("p", "Oder per GUI: Im Demo-Bereich öffnet "
                      "„ART-Profile…“ die Tabelle aller sechs ARTs, "
                      "vorbefüllt mit den Standardwerten — leere Felder "
                      "bleiben Standard, Prüfung beim OK, „Zurücksetzen“ "
                      "stellt die Vorgaben wieder her."),
                ("h", "Die Regeln"),
                ("li", "Overrides gelten in BEIDEN Delta-Ständen; der "
                       "Durchsatz-Story zuliebe bekommt prev 88 % der "
                       "(übersteuerten) Issue-Zahl"),
                ("li", "Nicht Übersteuertes behält seinen Story-Wert — die "
                       "eingebauten Geschichten (Alpha-3-Ausreißer, "
                       "Beta-3 schwach) ändern sich nur, wenn du ihre "
                       "Vorgaben änderst"),
                ("li", "Musterstärke nutzerseitig 0–100 wie überall; "
                       "unbekannte ARTs, Felder, Muster und Werte werden "
                       "mit klarer Meldung abgewiesen"),
                ("li", "Belegung speicherbar: Skala + ART-Profile wandern "
                       "mit ins Projekt-Template (Menü Templates) und "
                       "werden beim Laden wiederhergestellt"),
                ("h", "Leitplanken"),
                ("p", "Seed-Reproduzierbarkeit bleibt: gleicher Seed plus "
                      "gleiche Profile ergeben identische Daten. Die "
                      "Register-Skalen (s/m/l) und die ART-Profile sind "
                      "unabhängige Regler desselben Szenarios."),
            ],
        },
        "en": {
            "title": "ART Profiles in the Demo Portfolio",
            "tagline": "Every demo ART gets the single-ART knobs — mean CT, "
                       "spread, flow/failure patterns",
            "sections": [
                ("h", "What is it?"),
                ("p", "The demo portfolio used to generate its six ARTs "
                      "from fixed profiles. Now everything the single-ART "
                      "generation offers can be overridden per ART: issue "
                      "count, mean cycle time and its standard deviation, "
                      "completion and to-do rate, backflow probability, the "
                      "flow/failure patterns (triangle, flat_triangle, "
                      "cluster, batch) with strength (0–100) and the PI "
                      "duration. That yields, say, a portfolio where one "
                      "ART delivers in an end-of-PI batch pattern while "
                      "another struggles with high variance."),
                ("h", "How to use it"),
                ("code", "python -m testdata_generator --scenario portfolio "
                         "--output demo/ \\\n"
                         "    --scale m --art-profiles profile.json\n\n"
                         '# profile.json:\n'
                         '{"Alpha-1": {"mean_cycle_days": 30, '
                         '"std_cycle_days": 12,\n'
                         '             "pattern": "cluster", '
                         '"pattern_strength": 80}}'),
                ("p", "Or via the GUI: in the demo section, 'ART "
                      "Profiles…' opens the table of all six ARTs, "
                      "prefilled with the defaults — empty fields stay "
                      "default, validation happens at OK, 'Reset' restores "
                      "the defaults."),
                ("h", "The rules"),
                ("li", "Overrides apply in BOTH delta stands; for the "
                       "throughput story, prev gets 88 % of the "
                       "(overridden) issue count"),
                ("li", "Everything not overridden keeps its story value — "
                       "the built-in narratives (Alpha-3 outlier, weak "
                       "Beta-3) only change when you change their "
                       "defaults"),
                ("li", "Pattern strength is user-facing 0–100 as "
                       "everywhere; unknown ARTs, fields, patterns and "
                       "out-of-range values are rejected with clear "
                       "errors"),
                ("li", "Setup is storable: scale + ART profiles travel with "
                       "the project template (Templates menu) and are "
                       "restored on load"),
                ("h", "Guardrails"),
                ("p", "Seed reproducibility stays: same seed plus same "
                      "profiles yields identical data. Register scales "
                      "(s/m/l) and ART profiles are independent knobs of "
                      "the same scenario."),
            ],
        },
    },
    "portfolio_datenraum": {
        "de": {
            "title": "Portfolio-Datenraum",
            "tagline": "Ein Ordner = ein Portfolio · relative Pfade, "
                       "verschiebbar als Ganzes · Konvention statt Suchen",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Bisher verwiesen Portfolio-Configs mit absoluten "
                      "Pfaden auf verstreute Dateien — der Ordner überstand "
                      "kein Verschieben. Der Datenraum ist eine "
                      "Ordner-Konvention: portfolio.json oben, je Solution "
                      "ein Unterordner mit solution.json, arts/ "
                      "(IssueTimes/CFD/Transitions) und registers/ (die "
                      "neun Register unter Standardnamen), dazu snapshots/, "
                      "raw/ und workflows/. Relative Pfade in einer Config "
                      "lösen sich relativ zur Config-Datei auf — der Ordner "
                      "lässt sich als Ganzes verschieben, kopieren, zippen "
                      "und weitergeben."),
                ("h", "So benutzt du es"),
                ("code", "python -m testdata_generator --scenario portfolio "
                         "--output demo/ --seed 42\n"
                         "# demo/ irgendwohin verschieben — und dann:\n"
                         "python -m portfolio demo/portfolio.json --output "
                         "report.html\n"
                         "python -m portfolio --delta "
                         "demo/snapshots/snapshot_prev.json "
                         "demo/snapshots/snapshot_now.json"),
                ("p", "Das Demo-Szenario erzeugt die Struktur fertig; für "
                      "eigene Portfolios genügt es, Config und Daten in "
                      "einen gemeinsamen Ordner zu legen. In der GUI "
                      "verwaltet der Dialog „Datenquellen …“ die neun "
                      "Register-Pfade mit Status je Feld; „Aus Datenraum "
                      "übernehmen …“ füllt sie per Konvention, und beim "
                      "Speichern werden Pfade im Config-Ordner automatisch "
                      "relativiert."),
                ("h", "Die Regeln"),
                ("li", "Generierte Vielfalt: Die Register des Demo-Szenarios "
                       "bestehen aus festen Story-Ankern plus seed-"
                       "generierter Grundmenge — Skalen s/m/l (CLI --scale, "
                       "GUI-Auswahl; Default m), Anker auf jeder Skala "
                       "identisch"),
                ("li", "Relative Pfade: relativ zur Config-Datei — die "
                       "Regel gilt überall (Member, Templates, alle neun "
                       "Register)"),
                ("li", "Absolute Pfade: bleiben unverändert — "
                       "Bestands-Configs funktionieren weiter"),
                ("li", "Altfall CWD-relativ: funktioniert per Fallback, mit "
                       "Hinweis im Log"),
                ("li", "Standardnamen in registers/ sind Konvention, keine "
                       "Auto-Discovery — ein leeres Config-Feld bleibt "
                       "„kein Register“"),
                ("h", "Leitplanken"),
                ("p", "Die Configs bleiben die einzige Wahrheit; die "
                      "Konvention macht sie nur kurz und portabel. Kein "
                      "Schema-Bump, keine stille Verhaltensänderung. Ein "
                      "Verschiebe-Test in der Suite beweist die "
                      "Portabilität bei jedem Build."),
            ],
        },
        "en": {
            "title": "Portfolio Data Folder",
            "tagline": "One folder = one portfolio · relative paths, "
                       "movable as a whole · convention over hunting",
            "sections": [
                ("h", "What is it?"),
                ("p", "Portfolio configs used to point at scattered files "
                      "with absolute paths — the folder did not survive a "
                      "move. The data folder is a folder convention: "
                      "portfolio.json on top, one subfolder per solution "
                      "with solution.json, arts/ (IssueTimes/CFD/"
                      "Transitions) and registers/ (the nine registers "
                      "under standard names), plus snapshots/, raw/ and "
                      "workflows/. Relative paths in a config resolve "
                      "against the config file's folder — the folder moves, "
                      "copies, zips and travels as a whole."),
                ("h", "How to use it"),
                ("code", "python -m testdata_generator --scenario portfolio "
                         "--output demo/ --seed 42\n"
                         "# move demo/ anywhere — then:\n"
                         "python -m portfolio demo/portfolio.json --output "
                         "report.html\n"
                         "python -m portfolio --delta "
                         "demo/snapshots/snapshot_prev.json "
                         "demo/snapshots/snapshot_now.json"),
                ("p", "The demo scenario produces the structure ready-made; "
                      "for your own portfolios just put config and data "
                      "into one shared folder. In the GUI, the 'Data "
                      "sources …' dialog manages the nine register paths "
                      "with a per-field status; 'Take from data folder …' "
                      "fills them by convention, and on save, paths inside "
                      "the config folder are relativised automatically."),
                ("h", "The rules"),
                ("li", "Generated variety: the demo scenario's registers "
                       "are fixed story anchors plus a seed-generated base "
                       "population — scales s/m/l (CLI --scale, GUI picker; "
                       "default m), anchors identical at every scale"),
                ("li", "Relative paths: relative to the config file — one "
                       "rule everywhere (members, templates, all nine "
                       "registers)"),
                ("li", "Absolute paths: unchanged — existing configs keep "
                       "working"),
                ("li", "Legacy CWD-relative: still works via fallback, with "
                       "a log hint"),
                ("li", "Standard names in registers/ are a convention, not "
                       "auto-discovery — an empty config field still means "
                       "'no register'"),
                ("h", "Guardrails"),
                ("p", "The configs stay the single source of truth; the "
                      "convention only keeps them short and portable. No "
                      "schema bump, no silent behaviour change. A "
                      "move-the-folder test in the suite proves portability "
                      "on every build."),
            ],
        },
    },
    "red_team": {
        "de": {
            "title": "Red-Team-Assistent",
            "tagline": "Feature D5 · Premortem-Fragen aus dem "
                       "Decision-Log — nur Rohmaterial, nie Urteile",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Gute Stäbe greifen ihre eigenen Entscheidungen und "
                      "Annahmen an, bevor die Realität es tut — aber "
                      "Red-Team-Kapazität ist knapp. D5 erzeugt aus dem "
                      "Decision-/Assumption-Log (B4) Premortem- und "
                      "Angriffs-Fragen als Rohmaterial für eine menschlich "
                      "moderierte Session: Für Entscheidungen die "
                      "Rückschau aus der Zukunft („woran ist das in sechs "
                      "Monaten gescheitert?“), für Annahmen der direkte "
                      "Angriff („was müsste wahr sein, damit sie kippt — "
                      "und woran merkt man das früh?“)."),
                ("h", "So benutzt du es"),
                ("code", "python -m portfolio meine_solution.json "
                         "--red-team fragen.md\n"
                         "# je Log-Eintrag 1–3 Fragen, gruppiert nach ID,\n"
                         "# mit Art.-50-Banner + llm_audit.jsonl "
                         "(d5_red_team)"),
                ("p", "Provider wie überall: lokal ollama (Default), "
                      "extern claude, mock für die modellfreie Demo. "
                      "Voraussetzung ist ein referenziertes "
                      "Decision-Log (Config-Feld decisions) — fehlt es, "
                      "sagt die Fehlermeldung genau das."),
                ("h", "Der Fragen-Wächter"),
                ("p", "Die KI-Denkschrift ordnet D5 dem URTEIL zu — und "
                      "verlangt: nur Rohmaterial, kein Empfehlungs-Button. "
                      "Das ist hier maschinell erzwungen: Jede „- “-Zeile "
                      "der Ausgabe muss als Frage enden, sonst wird der "
                      "gesamte Entwurf verworfen — zusätzlich zu "
                      "Zahlen-Wächter, Kennzeichnung und Audit. Das "
                      "Werkzeug KANN keine Empfehlungen ausliefern."),
                ("h", "Leitplanken"),
                ("p", "Fragen nennen Teams und Einträge, nie Personen; "
                      "Zahlen und IDs stammen wörtlich aus dem Log. Die "
                      "Moderation, Auswahl und Beantwortung bleibt "
                      "vollständig beim Menschen."),
            ],
        },
        "en": {
            "title": "Red-Team Assistant",
            "tagline": "Feature D5 · Premortem questions from the "
                       "decision log — raw material only, never "
                       "judgements",
            "sections": [
                ("h", "What is it?"),
                ("p", "Good staffs attack their own decisions and "
                      "assumptions before reality does — but red-team "
                      "capacity is scarce. D5 turns the decision/"
                      "assumption log (B4) into premortem and attack "
                      "questions as raw material for a humanly moderated "
                      "session: for decisions the look back from the "
                      "future ('what made this fail six months from "
                      "now?'), for assumptions the direct attack ('what "
                      "would have to be true for it to flip — and how "
                      "would one notice early?')."),
                ("h", "How to use it"),
                ("code", "python -m portfolio my_solution.json "
                         "--red-team questions.md\n"
                         "# 1–3 questions per log entry, grouped by ID,\n"
                         "# with the Art. 50 banner + llm_audit.jsonl "
                         "(d5_red_team)"),
                ("p", "Provider as everywhere: local ollama (default), "
                      "external claude, mock for the model-free demo. "
                      "Prerequisite is a referenced decision log (config "
                      "field decisions) — if it is missing, the error "
                      "says exactly that."),
                ("h", "The questions guard"),
                ("p", "The KI-Denkschrift maps D5 to JUDGEMENT — and "
                      "demands: raw material only, no recommendation "
                      "button. That is machine-enforced here: every "
                      "'- ' line of the output must end as a question, "
                      "otherwise the whole draft is discarded — on top "
                      "of the numbers guard, labeling and audit. The "
                      "tool CANNOT deliver recommendations."),
                ("h", "Guardrails"),
                ("p", "Questions name teams and entries, never persons; "
                      "numbers and IDs come verbatim from the log. "
                      "Moderation, selection and answering stay entirely "
                      "with the humans."),
            ],
        },
    },
    "llm_translate": {
        "de": {
            "title": "Mehrsprachige Ausleitung",
            "tagline": "Feature D6 · Briefings und Entwürfe in allen fünf "
                       "Haussprachen — gewächtert, gekennzeichnet, "
                       "auditiert",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Internationale Solutions brauchen dieselbe Lage in "
                      "mehreren Sprachen. D6 leitet Lagebild-Texte nach "
                      "de/en/ro/pt/fr aus — über dasselbe llm-Framework "
                      "wie Narration und Executive Summary. Die "
                      "Zahlen-Invariante ist dabei die perfekte "
                      "Übersetzungs-Wache: Jede Zahl der Übersetzung muss "
                      "wörtlich in der Vorlage stehen, sonst wird sie "
                      "verworfen. Eigennamen (Teams, ARTs, Services) "
                      "bleiben unübersetzt; das Art.-50-Banner steht in "
                      "der Zielsprache."),
                ("h", "So benutzt du es"),
                ("code", "# Der Redaktions-Workflow: erst freigeben, dann "
                         "ausleiten\n"
                         "python -m llm translate delta.narration.md "
                         "--to en ro pt fr\n\n"
                         "# Direkt am Lauf: Entwurf bzw. Briefing "
                         "mitliefern\n"
                         "python -m portfolio --delta prev.json now.json "
                         "--narrate \\\n"
                         "    --translate en ro --output delta.html"),
                ("p", "Am Report-Lauf entsteht je Zielsprache "
                      "&lt;output&gt;.exec_summary.&lt;lang&gt;.md, am "
                      "Delta-Lauf .narration.&lt;lang&gt;.md — ohne "
                      "Narration wird das deterministische Briefing "
                      "selbst übersetzt (.&lt;lang&gt;.md)."),
                ("h", "Die Regeln"),
                ("li", "Vollständig übersetzen, nichts hinzufügen oder "
                       "weglassen; gleiche Absatzstruktur"),
                ("li", "Zahlen, Daten und IDs (BR-2, EP-A9 …) wörtlich — "
                       "maschinell erzwungen"),
                ("li", "Banner in der Zielsprache, Audit-Zweck "
                       "d6_translation, Provider frei wählbar (ollama "
                       "lokal Default)"),
                ("h", "Leitplanken"),
                ("p", "Jede Übersetzung ist ein Entwurf für menschliche "
                      "Redaktion — empfohlen ist der Weg „erst redigieren "
                      "und freigeben, dann ausleiten“, damit alle "
                      "Sprachfassungen vom freigegebenen Wortlaut "
                      "abstammen (gelebte Praxis der Manuals)."),
            ],
        },
        "en": {
            "title": "Multilingual Delivery",
            "tagline": "Feature D6 · Briefings and drafts in all five "
                       "house languages — guarded, labeled, audited",
            "sections": [
                ("h", "What is it?"),
                ("p", "International solutions need the same picture in "
                      "several languages. D6 delivers situational texts "
                      "in de/en/ro/pt/fr — through the same llm framework "
                      "as narration and executive summary. The numbers "
                      "invariant is the perfect translation guard: every "
                      "number in the translation must occur verbatim in "
                      "the source, or it is discarded. Proper names "
                      "(teams, ARTs, services) stay untranslated; the "
                      "Art. 50 banner is written in the target language."),
                ("h", "How to use it"),
                ("code", "# The editorial workflow: approve first, then "
                         "fan out\n"
                         "python -m llm translate delta.narration.md "
                         "--to en ro pt fr\n\n"
                         "# Inline with a run: deliver draft or briefing "
                         "alongside\n"
                         "python -m portfolio --delta prev.json now.json "
                         "--narrate \\\n"
                         "    --translate en ro --output delta.html"),
                ("p", "A report run yields "
                      "&lt;output&gt;.exec_summary.&lt;lang&gt;.md per "
                      "target language, a delta run "
                      ".narration.&lt;lang&gt;.md — without narration the "
                      "deterministic briefing itself is translated "
                      "(.&lt;lang&gt;.md)."),
                ("h", "The rules"),
                ("li", "Translate fully, add or drop nothing; keep the "
                       "paragraph structure"),
                ("li", "Numbers, dates and IDs (BR-2, EP-A9 …) verbatim — "
                       "machine-enforced"),
                ("li", "Banner in the target language, audit purpose "
                       "d6_translation, provider freely chosen (ollama "
                       "local by default)"),
                ("h", "Guardrails"),
                ("p", "Every translation is a draft for human editing — "
                      "the recommended path is 'edit and approve first, "
                      "then fan out', so every language version descends "
                      "from the approved wording (the manuals' lived "
                      "practice)."),
            ],
        },
    },
    "exec_summary": {
        "de": {
            "title": "LLM-Executive-Summary",
            "tagline": "Feature D1 · Das Sprachmodell formuliert die "
                       "Management-Zusammenfassung des Reports — Zahlen "
                       "kommen nur aus dem Datenpfad",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Der Report zeigt die Management-Summary als "
                      "Tabelle; die Executive Summary macht daraus 6–9 "
                      "Sätze Management-Prosa: Gesamtlage, auffällige "
                      "Einheiten, Datenvertrauen, Governance-Kopfzahlen. "
                      "Formuliert vom austauschbaren llm-Framework (ollama "
                      "lokal, claude extern, mock für Demos) — die Eingabe "
                      "ist ausschließlich der deterministische "
                      "Kennzahlen-Contract, den derselbe Datenpfad erzeugt "
                      "wie Report und Snapshots."),
                ("h", "So benutzt du es"),
                ("code", "python -m portfolio meine_solution.json "
                         "--output report.html --narrate\n"
                         "# Abschnitt „Executive Summary (Entwurf)“ unter "
                         "der Summary-Tabelle\n"
                         "# + report.html.exec_summary.md zum Redigieren\n"
                         "# + llm_audit.jsonl (Zweck d1_exec_summary)"),
                ("p", "In der GUI gilt die vorhandene Checkbox "
                      "„KI-Narration (Entwurf)“ jetzt auch für „Report "
                      "erzeugen …“. Schlägt die KI fehl, wird der Report "
                      "ohne Entwurf geschrieben — saubere Degradation."),
                ("h", "Die Wächter (unverändert)"),
                ("li", "Zahlen-Wächter: jede Zahl wörtlich im Contract, "
                       "sonst wird der Text verworfen"),
                ("li", "Art.-50-Banner: Modell, Deployment-Klasse, "
                       "Prompt-Version — behauptet nie eine Freigabe"),
                ("li", "Betreiber-Nachweis: llm_audit.jsonl mit "
                       "SHA-256-Hashes, nie Volltexte"),
                ("h", "Leitplanken"),
                ("p", "Der Contract nennt Einheiten und Registerzählungen "
                      "— Owner-/Personenfelder tauchen strukturell nicht "
                      "auf (per Test erzwungen). Ohne --narrate bleibt der "
                      "Report byte-identisch; PDF-Läufe erhalten einen "
                      "Hinweis statt eines Entwurfs."),
            ],
        },
        "en": {
            "title": "LLM Executive Summary",
            "tagline": "Feature D1 · The language model phrases the "
                       "report's management summary — numbers come only "
                       "from the data path",
            "sections": [
                ("h", "What is it?"),
                ("p", "The report shows the management summary as a "
                      "table; the executive summary turns it into 6–9 "
                      "sentences of management prose: overall picture, "
                      "standout units, data confidence, governance head "
                      "counts. Phrased by the exchangeable llm framework "
                      "(ollama local, claude external, mock for demos) — "
                      "the input is exclusively the deterministic metrics "
                      "contract produced by the same data path as report "
                      "and snapshots."),
                ("h", "How to use it"),
                ("code", "python -m portfolio my_solution.json "
                         "--output report.html --narrate\n"
                         "# section 'Executive Summary (Entwurf)' below "
                         "the summary table\n"
                         "# + report.html.exec_summary.md for editing\n"
                         "# + llm_audit.jsonl (purpose d1_exec_summary)"),
                ("p", "In the GUI, the existing 'AI narration (draft)' "
                      "checkbox now also covers 'Generate report …'. If "
                      "the AI fails, the report is written without the "
                      "draft — clean degradation."),
                ("h", "The guards (unchanged)"),
                ("li", "Numbers guard: every number verbatim in the "
                       "contract, otherwise the text is discarded"),
                ("li", "Art. 50 banner: model, deployment class, prompt "
                       "version — never claims approval"),
                ("li", "Operator evidence: llm_audit.jsonl with SHA-256 "
                       "hashes, never full texts"),
                ("h", "Guardrails"),
                ("p", "The contract names units and register counts — "
                      "owner/person fields structurally never appear "
                      "(enforced by tests). Without --narrate the report "
                      "stays byte-identical; PDF runs get a hint instead "
                      "of a draft."),
            ],
        },
    },
    "llm_narration": {
        "de": {
            "title": "KI-Narration",
            "tagline": "Feature D2 Teil 2 · Ein Sprachmodell entwirft die "
                       "Lage-Erzählung — lokal zuerst, gekennzeichnet immer",
            "sections": [
                ("h", "Worum geht es?"),
                ("p", "Das Delta-Briefing liefert die Fakten; die Narration "
                      "macht daraus den Entwurf von 5–8 Sätzen für die "
                      "Value-Stream-Konferenz: Was hat sich geändert, was "
                      "verdient Aufmerksamkeit — Verschlechterungen zuerst. "
                      "Formuliert von einem austauschbaren Sprachmodell, "
                      "standardmäßig lokal (Ollama, mistral-nemo): Daten "
                      "verlassen den Rechner nie, kein Konto, keine "
                      "API-Freigabe. Alternativ claude (Anthropic-API) oder "
                      "mock (Attrappe ohne Modell für Demo und Tests)."),
                ("h", "So benutzt du es"),
                ("code", "python -m portfolio --delta vorher.json heute.json "
                         "--narrate --output delta.html\n"
                         "python -m llm providers   # Inventar\n"
                         "python -m llm test        # Verkabelungs-Check "
                         "nach der Ollama-Installation"),
                ("p", "Oder per GUI: Checkbox „KI-Narration (Entwurf)“ plus "
                      "Provider-Auswahl neben „Delta-Briefing …“; im "
                      "Testdaten-Generator läuft dieselbe Strecke am "
                      "Demo-Portfolio mit wählbarem Provider — Default mock "
                      "(ohne jede Installation), umschaltbar auf "
                      "ollama/claude. Ollama einrichten: separate Anleitung "
                      "ollama_Installationsanleitung_DE.pdf (Doku-Site → "
                      "Tutorials)."),
                ("h", "Drei Wächter, fest verdrahtet"),
                ("li", "Zahlen-Wächter: Jede Zahl muss wörtlich im Briefing "
                       "stehen, sonst wird der Text verworfen — „das LLM "
                       "textet, es rechnet nicht“"),
                ("li", "Kennzeichnung (Art. 50 KI-VO): Jeder Entwurf trägt "
                       "sichtbar Modell, Deployment-Klasse und "
                       "Prompt-Version — freigeben kann nur der Mensch, der "
                       "redigiert"),
                ("li", "Betreiber-Nachweis: llm_audit.jsonl protokolliert "
                       "jede Anfrage mit SHA-256-Hashes — nie Volltexte, "
                       "nie Schlüssel"),
                ("h", "Leitplanken"),
                ("p", "Ohne --narrate bleibt das Briefing exakt wie bisher — "
                      "die KI ist Zusatz, nie Voraussetzung. Das Modell "
                      "sieht ausschließlich das Delta-Markdown (Teams, nie "
                      "Personen); ein Provider ist EINE Datei in "
                      "llm/providers/ — austauschbar wie die Datenquellen. "
                      "API-Schlüssel nur aus Umgebungsvariablen."),
            ],
        },
        "en": {
            "title": "AI Narration",
            "tagline": "Feature D2 part 2 · A language model drafts the "
                       "situational narrative — local first, always labeled",
            "sections": [
                ("h", "What is it?"),
                ("p", "The delta briefing delivers the facts; the narration "
                      "turns them into a 5–8 sentence draft for the "
                      "Value-Stream Conference: what changed, what deserves "
                      "attention — worsenings first. Phrased by an "
                      "exchangeable language model, local by default "
                      "(Ollama, mistral-nemo): data never leaves the "
                      "machine, no account, no API approval. Alternatives: "
                      "claude (Anthropic API) or mock (a stand-in without "
                      "any model, for demos and tests)."),
                ("h", "How to use it"),
                ("code", "python -m portfolio --delta before.json today.json "
                         "--narrate --output delta.html\n"
                         "python -m llm providers   # inventory\n"
                         "python -m llm test        # wiring check after "
                         "installing Ollama"),
                ("p", "Or via the GUI: tick 'AI narration (draft)' and pick "
                      "the provider next to 'Delta briefing …'; the "
                      "test-data generator runs the same flow on the demo "
                      "portfolio with a selectable provider — default mock "
                      "(no installation at all), switchable to "
                      "ollama/claude. Setting up Ollama: separate guide "
                      "ollama_Installationsanleitung_EN.pdf (docs site → "
                      "Tutorials)."),
                ("h", "Three guards, wired in"),
                ("li", "Numbers guard: every number must occur verbatim in "
                       "the briefing, otherwise the text is discarded — "
                       "'the LLM writes, it does not calculate'"),
                ("li", "AI label (Art. 50 EU AI Act): every draft visibly "
                       "carries model, deployment class and prompt version "
                       "— only the editing human can approve"),
                ("li", "Operator evidence: llm_audit.jsonl logs every "
                       "request with SHA-256 hashes — never full texts, "
                       "never keys"),
                ("h", "Guardrails"),
                ("p", "Without --narrate the briefing stays exactly as "
                      "before — AI is an add-on, never a prerequisite. The "
                      "model sees only the delta Markdown (teams, never "
                      "persons); a provider is ONE file in llm/providers/ — "
                      "exchangeable like the data sources. API keys only "
                      "from environment variables."),
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
