# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Tutorial „Eine eigene Datenquelle anbinden" als PDF
#   (DE + EN): Schritt für Schritt, jeder Schritt mit Beispiel, für
#   Entwickler:innen ohne Vorerfahrung mit dem sources-Framework. Inhalt
#   parallel zur mkdocs-Seite docs/tutorials/attach-a-source.md; die
#   Code-Blöcke sind geteilte Konstanten, damit beide Sprachfassungen
#   identischen Code zeigen.
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

_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=19,
                        leading=23, textColor=_ACCENT)
_TAGLINE = ParagraphStyle("tagline", fontName="Helvetica-Oblique",
                          fontSize=10, leading=13.5, textColor=_MUTED)
_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13.5,
                     leading=17, spaceBefore=14, spaceAfter=4,
                     textColor=_ACCENT)
_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11,
                     leading=14, spaceBefore=8, spaceAfter=2)
_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.6,
                       leading=13, spaceAfter=3)
_CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=10.8,
                       backColor=HexColor("#f4f4f4"), borderPadding=6,
                       leftIndent=4, spaceBefore=4, spaceAfter=6)
_FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, leading=10,
                       textColor=_MUTED)

# ── Geteilte Code-Blöcke (in beiden Sprachfassungen identisch) ──────────────

CODE_USE_FIRST = (
    "python -m testdata_generator --scenario portfolio --output demo --seed 42\n"
    "python -m sources providers\n\n"
    'echo {"provider": "file", "path": "demo/slo_alpha.json"} > my_sources.json\n'
    "python -m sources fetch --kind slo --config my_sources.json "
    "--output my_slo.json")

CODE_RECORD = (
    '{"service": "Order API", "slo": "availability",\n'
    ' "target_pct": 99.9, "sli_pct": 99.95,\n'
    ' "window": "30d", "source": "csv:slos.csv"}')

CODE_PROVIDER = (
    "from __future__ import annotations\n\n"
    "import csv\n"
    "from datetime import datetime\n"
    "from pathlib import Path\n\n"
    "from sources.base import KIND_SLO, SloRecord\n\n\n"
    "class MyCsvSource:\n"
    "    # (1) Name in Configs und in der providers-Liste / name in configs\n"
    "    provider_id = \"my_csv\"\n"
    "    # (2) Was diese Quelle liefern kann / what it can deliver\n"
    "    kinds = (KIND_SLO,)\n\n"
    "    # (3) Der Uebersetzer / the translator\n"
    "    def fetch(self, kind, config, log):\n"
    "        path = Path(config[\"path\"])\n"
    "        if not path.is_file():\n"
    "            raise RuntimeError(f\"my_csv: '{path}' missing.\")\n"
    "        fetched_at = datetime.now().isoformat(timespec=\"seconds\")\n"
    "        records = []\n"
    "        with path.open(encoding=\"utf-8-sig\", newline=\"\") as f:\n"
    "            for row in csv.DictReader(f):\n"
    "                records.append(SloRecord(\n"
    "                    service=row[\"service\"],\n"
    "                    slo=row[\"slo\"],\n"
    "                    target_pct=float(row[\"target_pct\"]),\n"
    "                    sli_pct=float(row[\"sli_pct\"]) if row.get(\"sli_pct\") else None,\n"
    "                    source=f\"my_csv:{path.name}\",\n"
    "                    fetched_at=fetched_at,\n"
    "                ))\n"
    "        log(f\"  my_csv: {len(records)} records\")\n"
    "        return records\n\n\n"
    "# (4) Genau dieses Objekt sucht die Auto-Discovery / discovery hook\n"
    "PROVIDER = MyCsvSource()")

CODE_CSV = ("service,slo,target_pct,sli_pct\n"
            "Order API,availability,99.9,99.95\n"
            "Checkout,availability,99.5,99.55")

CODE_FETCH_OWN = (
    '{"provider": "my_csv", "path": "team_slos.csv"}\n\n'
    "python -m sources fetch --kind slo --config csv_source.json "
    "--output my_slo.json\n"
    "python -m portfolio demo/solution_alpha.json --output report.html "
    "--browser")

CODE_REST = (
    "from sources.http import bearer, get_json, token_from_env\n\n"
    "def fetch(self, kind, config, log):\n"
    "    headers = bearer(token_from_env(config, \"MY_SYSTEM_TOKEN\"))\n"
    "    data = get_json(config[\"base_url\"] + \"/api/slos\", headers, "
    "\"MySystem\")\n"
    "    return [SloRecord(service=e[\"name\"], slo=e[\"goal\"],\n"
    "                      target_pct=e[\"target\"], sli_pct=e[\"current\"],\n"
    "                      source=\"my_system\") for e in data]")

CODE_SWAP = (
    "# vorher / before:\n"
    '{"provider": "my_csv", "path": "team_slos.csv"}\n\n'
    "# nachher / after (gleicher fetch-Befehl, gleiches Register):\n"
    '{"provider": "prometheus", "base_url": "https://prom.intern",\n'
    ' "services": [{"service": "Order API", "slo": "availability",\n'
    '               "target_pct": 99.9,\n'
    '               "sli_query": "avg_over_time(up[30d])", "scale": 100}]}')

CODE_COMBINE = (
    '{"sources": [\n'
    '  {"provider": "prometheus", "base_url": "https://prom.intern",\n'
    '   "services": [ ... ]},\n'
    '  {"provider": "my_csv", "path": "team_slos.csv"}\n'
    "]}")

# ── Inhalte je Sprache: (kind, text) mit kind in h1/h2/p/li/code ────────────

_DE = [
    ("h1", "1  Das Modell in drei Begriffen"),
    ("p", "Alles im sources-Framework dreht sich um drei Dinge. "
          "<b>Record</b>: das normierte Ergebnis — der Report sieht immer "
          "nur Records, nie dein System. Für ein SLO:"),
    ("code", CODE_RECORD),
    ("p", "<b>Provider</b>: ein Übersetzer — er liest dein System (Datei, "
          "REST-API, was auch immer) und gibt Records zurück; eine "
          "Python-Datei, eine Klasse. <b>Register</b>: die JSON-Datei, die "
          "ein Abruf schreibt; die Solution-Config referenziert sie "
          "(\"slo\": \"slo.json\"), der Report rendert sie. Eine Regel hält "
          "alles vergleichbar: <b>Provider urteilen nie</b> — ob ein SLO "
          "breached ist, entscheidet eine zentrale Regel, dieselbe für jede "
          "Quelle."),
    ("h1", "2  Erst benutzen, dann bauen (5 Minuten)"),
    ("p", "Erzeuge das Demo-Portfolio, sieh dir die Provider-Liste an und "
          "mache deinen ersten Abruf mit dem file-Provider — das Ergebnis "
          "(my_slo.json) ist das Zielformat jeder Quelle:"),
    ("code", CODE_USE_FIRST),
    ("h1", "3  Deinen eigenen Provider bauen, Schritt für Schritt"),
    ("p", "Wir binden eine CSV-Datei an (Teams pflegen SLO-Werte oft in "
          "einer Tabelle) — kein Server nötig, das Muster ist für jedes "
          "System identisch. Die fertige Referenz liegt in "
          "sources/providers/csv_slo.py. <b>Schritt 1:</b> Lege EINE Datei "
          "an, sources/providers/my_csv.py:"),
    ("code", CODE_PROVIDER),
    ("p", "Vier nummerierte Ideen sind der ganze Contract: Id, Arten, ein "
          "fetch(), das übersetzt, und ein PROVIDER-Objekt. Nirgends ist "
          "ein Register zu pflegen — die Existenz der Datei ist die "
          "Registrierung. <b>Schritt 2:</b> python -m sources providers → "
          "„my_csv: slo“ erscheint. <b>Schritt 3:</b> Daten geben "
          "(team_slos.csv):"),
    ("code", CODE_CSV),
    ("p", "<b>Schritt 4 und 5:</b> Abruf-Config anlegen, fetchen, das "
          "Register in der Solution-Config eintragen (\"slo\": "
          "\"my_slo.json\") und den Report rendern — die Sektion „Service "
          "Levels & Error Budgets“ zeigt deine CSV-Zeilen, die Spalte Data "
          "source sagt my_csv:team_slos.csv:"),
    ("code", CODE_FETCH_OWN),
    ("h1", "4  Ein REST-System statt einer Datei?"),
    ("p", "Gleiches Muster, nur fetch() ändert sich — der gemeinsame "
          "Helfer übernimmt HTTP, Auth und Fehler-Mapping:"),
    ("code", CODE_REST),
    ("li", "Tokens nur aus Umgebungsvariablen (token_from_env) — nie in "
           "Configs, nie in Logs."),
    ("li", "get_json mappt Fehler: 401/403 verweist auf die womöglich "
           "fehlende API-Freigabe UND den Datei-Weg als Ausweichroute."),
    ("li", "Mit Mocks testen, nicht gegen das Live-System — "
           "Request-Recorder-Muster aus "
           "tests/sources/unit/test_rest_providers.py kopieren."),
    ("h1", "5  Eine Quelle austauschen"),
    ("p", "Austauschen heißt: die Abruf-Config ändern, sonst nichts. "
          "Register-Name, Solution-Config und Report bleiben unverändert — "
          "nur die Data-source-Spalte zeigt die neue Herkunft:"),
    ("code", CODE_SWAP),
    ("h1", "6  Zwei Quellen kombinieren"),
    ("p", "Eine Config darf eine sources-Liste tragen; die Records fließen "
          "in EIN Register, jede Zeile behält ihre Herkunft. Typisch: das "
          "meiste im Monitoring, zwei Altsysteme in einer Tabelle:"),
    ("code", CODE_COMBINE),
    ("h1", "7  Quellen im Alltag verwalten"),
    ("li", "Inventar: python -m sources providers ist die maßgebliche "
           "Liste — neue Datei erscheint automatisch."),
    ("li", "Tokens: eine Umgebungsvariable je System (PROMETHEUS_TOKEN, "
           "GITHUB_TOKEN, GITLAB_TOKEN, SONAR_TOKEN; eigene via "
           "token_env)."),
    ("li", "Konventionen: eine Datei je Quelle; Provider übersetzen, "
           "urteilen nie; nicht Gemessenes ist None, keine Schätzung."),
    ("li", "Fehler: 401/403 nennt den Freigabe-Hinweis — bis dahin "
           "dieselben Daten über file oder csv liefern."),
    ("li", "Tests: kleine Testdatei je Provider (Happy Path, eine kaputte "
           "Eingabe, lesbare Fehlermeldung)."),
    ("h1", "8  Checkliste für eine neue Quelle"),
    ("li", "Eine Datei in sources/providers/ mit provider_id, kinds, "
           "fetch(), PROVIDER — providers listet sie."),
    ("li", "fetch() liefert normierte Records; jeder Record setzt source; "
           "kein Urteil im Provider."),
    ("li", "Tokens via token_from_env; Mock-Tests grün; Rücktausch auf "
           "file/csv funktioniert (die Ausweichroute bei ausstehender "
           "Freigabe)."),
]

_EN = [
    ("h1", "1  The model in three terms"),
    ("p", "Everything in the sources framework revolves around three "
          "things. <b>Record</b>: the normalised result — the report only "
          "ever sees records, never your system. For an SLO:"),
    ("code", CODE_RECORD),
    ("p", "<b>Provider</b>: a translator — it reads your system (a file, a "
          "REST API, anything) and returns records; one Python file, one "
          "class. <b>Register</b>: the JSON file a fetch writes; the "
          "solution config references it (\"slo\": \"slo.json\"), the "
          "report renders it. One rule keeps everything comparable: "
          "<b>providers never judge</b> — whether an SLO is breached is "
          "decided centrally, by the same rule for every source."),
    ("h1", "2  Use it before you build it (5 minutes)"),
    ("p", "Generate the demo portfolio, list the providers, and run your "
          "first fetch with the file provider — the result (my_slo.json) "
          "is the target format of every source:"),
    ("code", CODE_USE_FIRST),
    ("h1", "3  Build your own provider, step by step"),
    ("p", "We attach a CSV file (teams often keep SLO values in a "
          "spreadsheet) — no server needed, and the pattern is identical "
          "for any system. The finished reference lives in "
          "sources/providers/csv_slo.py. <b>Step 1:</b> create ONE file, "
          "sources/providers/my_csv.py:"),
    ("code", CODE_PROVIDER),
    ("p", "Four numbered ideas are the whole contract: an id, the kinds, a "
          "fetch() that translates, and a PROVIDER object. No registry to "
          "edit anywhere — the file's existence registers it. "
          "<b>Step 2:</b> python -m sources providers → 'my_csv: slo' "
          "appears. <b>Step 3:</b> feed it data (team_slos.csv):"),
    ("code", CODE_CSV),
    ("p", "<b>Steps 4 and 5:</b> create the fetch config, fetch, reference "
          "the register in the solution config (\"slo\": \"my_slo.json\") "
          "and render the report — the 'Service Levels & Error Budgets' "
          "section shows your CSV rows, the Data source column reads "
          "my_csv:team_slos.csv:"),
    ("code", CODE_FETCH_OWN),
    ("h1", "4  A REST system instead of a file?"),
    ("p", "Same pattern, only fetch() changes — the shared helper handles "
          "HTTP, auth and error mapping:"),
    ("code", CODE_REST),
    ("li", "Tokens only from environment variables (token_from_env) — "
           "never in configs, never in logs."),
    ("li", "get_json maps errors: 401/403 points at the possibly missing "
           "API approval AND at the file path as fallback."),
    ("li", "Test with mocks, not against the live system — copy the "
           "request-recorder pattern from "
           "tests/sources/unit/test_rest_providers.py."),
    ("h1", "5  Swapping a source"),
    ("p", "Swapping means: change the fetch config, nothing else. Register "
          "name, solution config and report stay untouched — only the Data "
          "source column shows the new origin:"),
    ("code", CODE_SWAP),
    ("h1", "6  Combining two sources"),
    ("p", "A config may hold a sources list; the records merge into ONE "
          "register, each row keeping its origin. Typical: most services "
          "in monitoring, two legacy systems in a spreadsheet:"),
    ("code", CODE_COMBINE),
    ("h1", "7  Managing sources day to day"),
    ("li", "Inventory: python -m sources providers is the authoritative "
           "list — a new file appears automatically."),
    ("li", "Tokens: one environment variable per system (PROMETHEUS_TOKEN, "
           "GITHUB_TOKEN, GITLAB_TOKEN, SONAR_TOKEN; your own via "
           "token_env)."),
    ("li", "Conventions: one file per source; providers translate, never "
           "judge; unmeasured values are None, not a guess."),
    ("li", "Errors: 401/403 carries the approval hint — until it arrives, "
           "ship the same data via file or csv."),
    ("li", "Tests: a small test file per provider (happy path, one broken "
           "input, a readable error message)."),
    ("h1", "8  Checklist for a new source"),
    ("li", "One file in sources/providers/ with provider_id, kinds, "
           "fetch(), PROVIDER — providers lists it."),
    ("li", "fetch() returns normalised records; every record sets source; "
           "no judgement in the provider."),
    ("li", "Tokens via token_from_env; mock tests green; swapping back to "
           "file/csv still works (the fallback while approvals are "
           "pending)."),
]

_META = {
    "de": ("Tutorial: Eine eigene Datenquelle anbinden",
           "Für Entwickler:innen ohne Vorerfahrung · ~30 Minuten · läuft "
           "komplett gegen das Demo-Szenario · jede Etappe mit Beispiel",
           "sources_Tutorial_DE.pdf", _DE),
    "en": ("Tutorial: Attaching your own data source",
           "For developers with no prior experience · ~30 minutes · runs "
           "entirely against the demo scenario · every step with an example",
           "sources_Tutorial_EN.pdf", _EN),
}


def _build(lang: str) -> Path:
    title, tagline, filename, content = _META[lang]
    path = Path(__file__).resolve().parent / filename
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=14 * mm,
        title=title, author="Robert Seebauer")
    story: list = [
        Paragraph(title, _TITLE),
        Spacer(1, 2 * mm),
        Paragraph(tagline, _TAGLINE),
        Spacer(1, 1 * mm),
        HRFlowable(width="100%", thickness=1, color=_ACCENT),
    ]
    for kind, text in content:
        if kind == "h1":
            story.append(Paragraph(text, _H1))
        elif kind == "h2":
            story.append(Paragraph(text, _H2))
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
            f"github.com/Jaegerfeld/situation-report · Online-Fassung: "
            f"jaegerfeld.github.io/situation-report", _FOOT),
    ]
    doc.build(story)
    return path


def main() -> None:
    for lang in _META:
        print(f"PDF erstellt: {_build(lang)}")


if __name__ == "__main__":
    main()
