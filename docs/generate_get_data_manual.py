# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       08.05.2026
# Geändert:       08.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für get_data als PDF in Deutsch und Englisch.
#   Da get_data noch in Entwicklung ist, beschreibt das Handbuch den manuellen
#   Export echter Jira-Daten (REST API, API-Token, curl, Paginierung, Helper).
# =============================================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from version import __version__ as _VERSION

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DE = Path(__file__).parent / "get_data_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "get_data_UserManual.pdf"

_ASSETS = Path(__file__).parent / "assets"
CONTENT_WIDTH = 15.5 * cm

C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles() -> dict:
    """Build and return the paragraph style dictionary."""
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("GD_H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8, keepWithNext=1),
        h2=s("GD_H2", fontName="Helvetica-Bold", fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5, keepWithNext=1),
        h3=s("GD_H3", fontName="Helvetica-BoldOblique", fontSize=11, textColor=C_BLUE,
              spaceBefore=10, spaceAfter=4, keepWithNext=1),
        body=s("GD_Body", fontName="Helvetica", fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("GD_Bullet", fontName="Helvetica", fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3, bulletIndent=4),
        code=s("GD_Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("GD_Hint", fontName="Helvetica-Oblique", fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        caption=s("GD_Caption", fontName="Helvetica-Oblique", fontSize=8,
                  textColor=C_HINT, leading=11, alignment=TA_CENTER, spaceAfter=8),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

class _GDDoc(BaseDocTemplate):
    """BaseDocTemplate with cover and normal page templates."""

    def __init__(self, filename: str, lang: str = "de", **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        self._header_text = (
            "get_data  --  Benutzerhandbuch"
            if lang == "de"
            else "get_data  --  User Manual"
        )
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(
                id="cover",
                frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                onPage=lambda c, d, lang=lang: _build_cover(c, d, lang),
            ),
            PageTemplate(
                id="normal",
                frames=[Frame(margin, margin,
                              w - 2 * margin, h - 2 * margin - 1.2 * cm,
                              id="normal", showBoundary=0)],
                onPage=self._header_footer,
            ),
        ])

    def _header_footer(self, canvas, doc):
        """Draw header bar and page number footer."""
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2 * cm, h - 0.7 * cm, self._header_text)
        canvas.drawRightString(w - 2.2 * cm, h - 0.7 * cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont("Helvetica", 8)
        page_label = "Seite %d" if self._lang == "de" else "Page %d"
        canvas.drawCentredString(w / 2, 1.0 * cm, page_label % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2 * cm, 1.4 * cm, w - 2.2 * cm, 1.4 * cm)
        canvas.restoreState()


def _build_cover(canvas, doc, lang: str = "de"):
    """Draw the cover page with color blocks and centered text."""
    w, h = A4
    subtitle = "Benutzerhandbuch" if lang == "de" else "User Manual"
    tagline = (
        "Jira-Daten für SituationReport exportieren"
        if lang == "de"
        else "Export Jira data for SituationReport"
    )
    audience = (
        "Fuer Agile Coaches und PI Manager"
        if lang == "de"
        else "For Agile Coaches and PI Managers"
    )

    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h * 0.35, w, h * 0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawCentredString(w / 2, h * 0.62, "SituationReport")
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(w / 2, h * 0.57, "get_data")
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(w / 2, h * 0.515, subtitle)
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w / 2, h * 0.47, tagline)
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w * 0.2, h * 0.44, w * 0.8, h * 0.44)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w / 2, h * 0.12,
                             "situation-report -- github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w / 2, h * 0.09, f"{audience} -- Version {_VERSION}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Helper flowables
# ---------------------------------------------------------------------------

def H1(text, st):  return Paragraph(text, st["h1"])
def H2(text, st):  return Paragraph(text, st["h2"])
def H3(text, st):  return Paragraph(text, st["h3"])
def P(text, st):   return Paragraph(text, st["body"])
def BL(text, st):  return Paragraph("• " + text, st["bullet"])
def HI(text, st):  return Paragraph(text, st["hint"])
def CD(text, st):  return Paragraph(text, st["code"])
def PRE(text, st): return Preformatted(text, st["code"])
def SP(n=6):       return Spacer(1, n)
def HR():          return HRFlowable(width=CONTENT_WIDTH, thickness=1,
                                     color=C_ACCENT, spaceAfter=8)


def box(text: str, st: dict, bg: str = "#eaf4fb") -> Table:
    """
    Highlighted info box with a border.

    Args:
        text: Paragraph content (XML markup allowed).
        st:   Style dictionary from make_styles().
        bg:   Background colour as hex string.

    Returns:
        Table flowable styled as an info box.
    """
    t = Table([[Paragraph(text, st["body"])]], colWidths=[CONTENT_WIDTH])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(bg)),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


def tbl(headers: list, rows: list, col_widths: list | None = None) -> Table:
    """
    Standard striped table with blue header row.

    Args:
        headers:    List of column header strings.
        rows:       List of row lists (strings or Paragraphs).
        col_widths: Optional list of column widths in points.

    Returns:
        Table flowable with standard styling.
    """
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_BLUE),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("FONTNAME",       (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ("GRID",           (0, 0), (-1, -1), 0.3, C_MID),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Content — German
# ---------------------------------------------------------------------------

def content_de(st: dict) -> list:
    """
    Build the German manual story (list of ReportLab flowables).

    Args:
        st: Style dictionary from make_styles().

    Returns:
        List of Platypus flowables for the German manual.
    """
    story = []

    # ---- 1. Daten aus Jira Cloud exportieren ----
    story += [PageBreak(),
              H1("1  Daten aus Jira Cloud exportieren", st), HR(),
              box("<b>Hinweis:</b> Das Modul <b>get_data</b> ist noch in Entwicklung. "
                  "Dieses Handbuch beschreibt den manuellen Export von Jira-Daten über "
                  "die Jira REST API. Der Exportprozess ist derselbe, den get_data später "
                  "automatisiert — die exportierten JSON-Dateien sind direkt mit "
                  "<b>transform_data</b> verarbeitbar.", st, bg="#fff8e1"),
              SP(10),
              P("Dieser Abschnitt erklärt, wie Sie echte Issue-Daten aus Jira Cloud für "
                "SituationReport exportieren. Der Export liefert dieselbe JSON-Struktur "
                "wie der Testdata Generator — transform_data verarbeitet beide "
                "identisch.", st),

              H2("1.1  Was Sie benötigen", st),
              tbl(["Voraussetzung", "Details"],
                  [["Jira Cloud Zugang",
                    "Ein Konto mit Lesezugriff auf das gewünschte Projekt"],
                   ["API-Token",
                    "Persönliches Token von id.atlassian.com — einmalig erstellen"],
                   ["Projekt-Key",
                    "Kürzel des Jira-Projekts, z. B. 'ART_A' oder 'SCRUM'"],
                   ["curl oder Browser",
                    "curl für automatisierte Abfragen; Browser für einfache Tests"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(8),

              H2("1.2  API-Token erstellen", st),
              P("Das API-Token ersetzt bei API-Abfragen Ihr Passwort und wird "
                "einmalig erstellt:", st),
              tbl(["Schritt", "Aktion"],
                  [["1", "https://id.atlassian.com im Browser aufrufen (in Jira eingeloggt sein)"],
                   ["2", "Security → API tokens → Create API token"],
                   ["3", "Einen Namen eingeben, z. B. 'SituationReport', auf 'Create' klicken"],
                   ["4", "Token kopieren und sicher speichern — er wird nur einmal angezeigt!"]],
                  col_widths=[1.5 * cm, 14 * cm]),
              SP(4),
              HI("Sicherheitshinweis: Behandeln Sie den API-Token wie ein Passwort. "
                 "Speichern Sie ihn in einem Passwort-Manager und teilen Sie ihn "
                 "nicht mit anderen.", st),
              SP(6),

              H2("1.3  Die Jira REST API abfragen", st),
              P("Jira Cloud bietet zwei API-Varianten. Für neue Skripte empfiehlt sich "
                "die aktuelle v3-API; bestehende v2-Skripte funktionieren weiterhin. "
                "<font name='Courier'>expand=changelog</font> ist in <b>beiden</b> "
                "Varianten Pflicht — ohne ihn fehlen die Statusübergänge, die "
                "transform_data benötigt.", st),

              H3("Aktuelle API (v3) – empfohlen", st),
              P("Endpoint: <font name='Courier'>POST /rest/api/3/search/jql</font><br/>"
                "Parameter werden als JSON im Request-Body übergeben. "
                "Die Antwort enthält zusätzlich "
                "<font name='Courier'>isLast</font> und "
                "<font name='Courier'>nextPageToken</font> für die Paginierung "
                "(Abschnitt 1.5).", st),
              PRE("curl -X POST \\\n"
                  "  \"https://firma.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@firma.de:IhrAPIToken\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\n"
                  "       \"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json", st),
              HI("maxResults ist bei der v3-API auf 100 Issues pro Anfrage begrenzt. "
                 "Verwenden Sie nextPageToken für Projekte mit mehr als 100 Issues "
                 "(Abschnitt 1.5).", st),
              SP(6),

              H3("Ältere API (v2) – weiterhin unterstützt", st),
              P("Endpoint: <font name='Courier'>GET /rest/api/2/search</font><br/>"
                "Parameter als URL-Query-String. Unterstützt bis zu 1.000 Issues "
                "pro Anfrage und Offset-Paginierung mit "
                "<font name='Courier'>startAt</font>.", st),
              PRE("curl -u \"name@firma.de:IhrAPIToken\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              HI("Tipp: Für neue Skripte empfiehlt sich die v3-API. "
                 "Bestehende v2-Skripte müssen nicht migriert werden.", st),
              SP(6),

              H2("1.4  Welche Felder transform_data benötigt", st),
              tbl(["Jira-Feld", "Pflicht", "Verwendung"],
                  [["key", "✓",
                    "Issue-Kennung (z. B. ART_A-001)"],
                   ["fields.issuetype.name", "✓",
                    "Issue-Typ für Filterung (Feature, Bug, ...)"],
                   ["fields.created", "✓",
                    "Erstellungsdatum des Issues"],
                   ["fields.status.name", "✓",
                    "Aktueller Status"],
                   ["changelog (expand=changelog)", "✓",
                    "Statusübergänge mit Zeitstempeln — MUSS im URL-Parameter gesetzt sein"],
                   ["fields.resolution", "–",
                    "Optional — Auflösungstyp (z. B. 'Done', 'Won't Fix')"],
                   ["fields.summary", "–",
                    "Optional — Issue-Titel"]],
                  col_widths=[5.5 * cm, 1.5 * cm, 8.5 * cm]),
              SP(6),

              H2("1.5  Paginierung – mehr als 100 Issues", st),

              H3("API v3 – Cursor-basierte Paginierung (nextPageToken)", st),
              P("Die v3-API liefert maximal 100 Issues pro Anfrage. Jede Antwort enthält "
                "entweder einen <font name='Courier'>nextPageToken</font> für die nächste "
                "Seite oder <font name='Courier'>\"isLast\": true</font>, wenn alle Issues "
                "abgerufen wurden. Seiten müssen <b>sequenziell</b> abgerufen werden — "
                "das Token aus der aktuellen Antwort wird im nächsten Request eingesetzt.", st),
              PRE("# Seite 1 – ohne nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://firma.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@firma.de:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# nextPageToken aus Seite 1 auslesen:\n"
                  "#   cat ART_A_page1.json | grep nextPageToken\n"
                  "#   (oder mit jq: jq -r '.nextPageToken' ART_A_page1.json)\n\n"
                  "# Seite 2 – nextPageToken einfuegen\n"
                  "curl -X POST \\\n"
                  "  \"https://firma.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@firma.de:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"],\n"
                  "       \"nextPageToken\":\"<Token aus Seite 1>\"}' \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Wiederholen bis isLast:true in der Antwort\n\n"
                  "# Alle Seiten zusammenfuehren\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json ... \\\n"
                  "  --output ART_A_merged.json", st),
              P("Wiederholen Sie den Vorgang, bis die Antwort "
                "<font name='Courier'>\"isLast\": true</font> enthält. "
                "Der <b>Helper</b> führt alle Seiten zusammen und entfernt "
                "Duplikate automatisch.", st),
              SP(6),

              H3("API v2 – Offset-basierte Paginierung (startAt) – Legacy", st),
              P("Die v2-API unterstützt bis zu 1.000 Issues pro Anfrage. "
                "Mit <font name='Courier'>startAt</font> kann jede Seite direkt "
                "angesprungen werden. "
                "<b>Wichtig:</b> <font name='Courier'>startAt</font> ist nur mit "
                "dem v2-Endpunkt kompatibel — nicht mit dem neuen v3-Endpunkt.", st),
              PRE("# Seite 1 (Issues 1–1000)\n"
                  "curl -u \"name@firma.de:Token\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Seite 2 (Issues 1001–2000)\n"
                  "curl -u \"name@firma.de:Token\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Dateien mit dem Helper zusammenfuehren\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Erhöhen Sie <font name='Courier'>startAt</font> schrittweise um 1.000, "
                "bis das Ergebnis weniger als 1.000 Issues enthält.", st),
              SP(6),

              H2("1.6  Vom JSON-Export zur Workflow-Datei", st),
              P("Nach dem Export müssen Sie eine Workflow-Datei erstellen, die Ihre "
                "tatsächlichen Jira-Status abbildet. Das folgende Python-Skript "
                "extrahiert alle Status-Namen aus der JSON-Datei:", st),
              PRE("import json\n"
                  "data = json.loads(open('ART_A_page1.json').read())\n"
                  "statuses = set()\n"
                  "for issue in data['issues']:\n"
                  "    for h in issue['changelog']['histories']:\n"
                  "        for item in h['items']:\n"
                  "            if item['field'] == 'status':\n"
                  "                statuses.add(item['toString'])\n"
                  "print(sorted(statuses))", st),
              P("Aus den gefundenen Status-Namen erstellen Sie eine "
                "<font name='Courier'>workflow.txt</font> — ordnen Sie die Status in "
                "logischer Reihenfolge an und setzen Sie "
                "<font name='Courier'>&lt;First&gt;</font> und "
                "<font name='Courier'>&lt;Closed&gt;</font>. "
                "Das Format der Workflow-Datei ist im Benutzerhandbuch von "
                "<b>transform_data</b> beschrieben.", st)]

    # ---- 2. FAQ ----
    story += [PageBreak(),
              H1("2  Häufige Fragen (FAQ)", st), HR(),

              H2("Was passiert, wenn expand=changelog fehlt?", st),
              P("transform_data findet keine Statusübergänge und gibt für alle Issues "
                "leere Zeitwerte aus. Die Excel-Ausgaben enthalten keine nutzbaren "
                "Daten. Stellen Sie sicher, dass "
                "<font name='Courier'>expand=changelog</font> immer in der URL steht.", st),

              H2("Ich erhalte den Fehler 'Unauthorized' beim curl-Aufruf.", st),
              P("Prüfen Sie: E-Mail-Adresse und API-Token korrekt? Sind sie durch "
                "einen Doppelpunkt getrennt? Hat Ihr Konto Lesezugriff auf das Projekt? "
                "Tipp: Einen neuen API-Token generieren, falls der alte abgelaufen ist "
                "oder verloren wurde.", st),

              H2("Kann ich mehrere Jira-Projekte zusammenführen?", st),
              P("Ja — entweder über JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) für einen "
                "einzigen Export, oder mit dem Helper mehrere separate Exporte "
                "zusammenführen. Achten Sie darauf, dass die Workflows beider Projekte "
                "kompatibel sind.", st),

              H2("Wie groß kann die JSON-Datei werden?", st),
              P("Faustregel: ca. 2–5 KB pro Issue (abhängig von der Changelog-Länge). "
                "1.000 Issues entsprechen ca. 2–5 MB. Bei sehr großen Projekten "
                "(10.000+ Issues) empfiehlt sich Paginierung und der Einsatz des "
                "Helpers.", st),

              H2("Soll ich Testdaten oder echte Daten verwenden?", st),
              P("Für Demos, Schulungen und Installationstests sind synthetische Testdaten "
                "aus dem <b>Testdata Generator</b> die bessere Wahl — keine "
                "Datenschutzbedenken, reproduzierbar und kontrolliert. "
                "Für echte Flow-Analysen und Entscheidungen spiegeln echte Jira-Daten "
                "den tatsächlichen Workflow-Zustand wider.", st)]

    # ---- 3. Glossar ----
    story += [PageBreak(),
              H1("3  Glossar", st), HR(),
              tbl(["Begriff", "Erklärung"],
                  [["ART",       "Agile Release Train — ein Team aus mehreren Scrum-Teams in SAFe"],
                   ["API",       "Application Programming Interface — Programmierschnittstelle"],
                   ["API-Token", "Sicherheitsschlüssel für den Zugang zur Jira-REST-API; "
                                 "ersetzt das Passwort bei curl-Abfragen"],
                   ["Changelog", "Jira-Protokoll aller Statusänderungen eines Issues "
                                 "(expand=changelog)"],
                   ["CFD",       "Cumulative Flow Diagram — zeigt den Issuebestand je Stage "
                                 "kumuliert über die Zeit"],
                   ["Closed Stage", "Die Stage, die ein Issue als abgeschlossen markiert "
                                    "(workflow.txt: &lt;Closed&gt;)"],
                   ["Cycle Time",  "Zeit von der ersten aktiven Stage (&lt;First&gt;) bis "
                                   "zur Closed-Stage"],
                   ["First Stage", "Erste aktive Stage, ab der die Cycle Time zählt "
                                   "(workflow.txt: &lt;First&gt;)"],
                   ["Helper",    "SituationReport-Modul zum Zusammenführen mehrerer "
                                 "Jira-JSON-Dateien"],
                   ["Issue",     "Arbeitselement in Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JQL",       "Jira Query Language — Abfragesprache für Jira-Suchen, "
                                 "z. B. project=ART_A"],
                   ["JSON",      "JavaScript Object Notation — Format der Jira-API-Exporte"],
                   ["Stage",     "Ein Schritt im Workflow (entspricht einer Jira-Spalte oder "
                                 "einem Status-Namen)"],
                   ["Workflow",  "Geordnete Abfolge von Stages, die ein Issue durchläuft"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — English
# ---------------------------------------------------------------------------

def content_en(st: dict) -> list:
    """
    Build the English manual story (list of ReportLab flowables).

    Args:
        st: Style dictionary from make_styles().

    Returns:
        List of Platypus flowables for the English manual.
    """
    story = []

    # ---- 1. Exporting Data from Jira Cloud ----
    story += [PageBreak(),
              H1("1  Exporting Data from Jira Cloud", st), HR(),
              box("<b>Note:</b> The <b>get_data</b> module is still under development. "
                  "This manual describes the manual export of Jira data via the Jira REST "
                  "API. This is the same process that get_data will automate — the exported "
                  "JSON files can be processed directly by <b>transform_data</b>.", st,
                  bg="#fff8e1"),
              SP(10),
              P("This chapter explains how to export real issue data from Jira Cloud for "
                "SituationReport. The export produces the same JSON structure as the "
                "Testdata Generator — transform_data processes both identically.", st),

              H2("1.1  What you need", st),
              tbl(["Requirement", "Details"],
                  [["Jira Cloud account",
                    "An account with read access to the desired project"],
                   ["API token",
                    "Personal token from id.atlassian.com — created once"],
                   ["Project key",
                    "The Jira project shortcode, e.g. 'ART_A' or 'SCRUM'"],
                   ["curl or browser",
                    "curl for automated queries; browser for quick tests"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(8),

              H2("1.2  Creating an API token", st),
              P("The API token replaces your password for API calls and is created once:", st),
              tbl(["Step", "Action"],
                  [["1", "Open https://id.atlassian.com in your browser (while logged into Jira)"],
                   ["2", "Security → API tokens → Create API token"],
                   ["3", "Enter a label, e.g. 'SituationReport', click 'Create'"],
                   ["4", "Copy the token and store it safely — it is only shown once!"]],
                  col_widths=[1.5 * cm, 14 * cm]),
              SP(4),
              HI("Security note: Treat the API token like a password. Store it in a "
                 "password manager and do not share it.", st),
              SP(6),

              H2("1.3  Querying the Jira REST API", st),
              P("Jira Cloud offers two API variants. Use the current v3 API for new "
                "scripts; existing v2 scripts continue to work. "
                "<font name='Courier'>expand=changelog</font> is <b>required in both</b> "
                "variants — without it, status transitions are missing and transform_data "
                "cannot compute time-in-stage values.", st),

              H3("Current API (v3) – recommended", st),
              P("Endpoint: <font name='Courier'>POST /rest/api/3/search/jql</font><br/>"
                "Parameters are passed as a JSON request body. "
                "The response additionally includes "
                "<font name='Courier'>isLast</font> and "
                "<font name='Courier'>nextPageToken</font> for pagination "
                "(Section 1.5).", st),
              PRE("curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:YourAPIToken\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\n"
                  "       \"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json", st),
              HI("maxResults is limited to 100 issues per request with the v3 API. "
                 "Use nextPageToken for projects with more than 100 issues "
                 "(Section 1.5).", st),
              SP(6),

              H3("Older API (v2) – still supported", st),
              P("Endpoint: <font name='Courier'>GET /rest/api/2/search</font><br/>"
                "Parameters as URL query string. Supports up to 1,000 issues per "
                "request and offset-based pagination with "
                "<font name='Courier'>startAt</font>.", st),
              PRE("curl -u \"name@company.com:YourAPIToken\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              HI("Tip: For new scripts, the v3 API is preferred. "
                 "Existing v2 scripts do not need to be migrated.", st),
              SP(6),

              H2("1.4  Fields required by transform_data", st),
              tbl(["Jira field", "Required", "Purpose"],
                  [["key", "✓",
                    "Issue identifier (e.g. ART_A-001)"],
                   ["fields.issuetype.name", "✓",
                    "Issue type for filtering (Feature, Bug, ...)"],
                   ["fields.created", "✓",
                    "Issue creation date"],
                   ["fields.status.name", "✓",
                    "Current status"],
                   ["changelog (expand=changelog)", "✓",
                    "Status transitions with timestamps — MUST be set in the URL"],
                   ["fields.resolution", "–",
                    "Optional — resolution type (e.g. 'Done', 'Won't Fix')"],
                   ["fields.summary", "–",
                    "Optional — issue title"]],
                  col_widths=[5.5 * cm, 1.5 * cm, 8.5 * cm]),
              SP(6),

              H2("1.5  Pagination – more than 100 issues", st),

              H3("API v3 – Cursor-based pagination (nextPageToken)", st),
              P("The v3 API returns at most 100 issues per request. Each response "
                "contains either a <font name='Courier'>nextPageToken</font> for the "
                "next page, or <font name='Courier'>\"isLast\": true</font> when all "
                "issues have been fetched. Pages must be retrieved <b>sequentially</b> "
                "— the token from the current response is used in the next request.", st),
              PRE("# Page 1 – no nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Read nextPageToken from page 1:\n"
                  "#   cat ART_A_page1.json | grep nextPageToken\n"
                  "#   (or with jq: jq -r '.nextPageToken' ART_A_page1.json)\n\n"
                  "# Page 2 – insert nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"],\n"
                  "       \"nextPageToken\":\"<token from page 1>\"}' \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Repeat until isLast:true appears in the response\n\n"
                  "# Merge all pages\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json ... \\\n"
                  "  --output ART_A_merged.json", st),
              P("Repeat until the response contains "
                "<font name='Courier'>\"isLast\": true</font>. "
                "The <b>Helper</b> merges all pages and removes duplicates "
                "automatically.", st),
              SP(6),

              H3("API v2 – Offset-based pagination (startAt) – Legacy", st),
              P("The v2 API supports up to 1,000 issues per request. "
                "With <font name='Courier'>startAt</font>, any page can be accessed "
                "directly. <b>Important:</b> "
                "<font name='Courier'>startAt</font> is only compatible with the v2 "
                "endpoint — not with the new v3 endpoint.", st),
              PRE("# Page 1 (issues 1–1,000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Page 2 (issues 1,001–2,000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Merge files with the Helper\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Increment <font name='Courier'>startAt</font> by 1,000 until the "
                "response contains fewer than 1,000 issues.", st),
              SP(6),

              H2("1.6  From JSON export to workflow file", st),
              P("After exporting, create a workflow file that maps your actual Jira "
                "statuses. The following Python snippet extracts all status names from "
                "the export:", st),
              PRE("import json\n"
                  "data = json.loads(open('ART_A_page1.json').read())\n"
                  "statuses = set()\n"
                  "for issue in data['issues']:\n"
                  "    for h in issue['changelog']['histories']:\n"
                  "        for item in h['items']:\n"
                  "            if item['field'] == 'status':\n"
                  "                statuses.add(item['toString'])\n"
                  "print(sorted(statuses))", st),
              P("From the status names found, create a "
                "<font name='Courier'>workflow.txt</font> — arrange the statuses in "
                "logical order and set the "
                "<font name='Courier'>&lt;First&gt;</font> and "
                "<font name='Courier'>&lt;Closed&gt;</font> markers. "
                "The workflow file format is described in the <b>transform_data</b> "
                "User Manual.", st)]

    # ---- 2. FAQ ----
    story += [PageBreak(),
              H1("2  Frequently Asked Questions (FAQ)", st), HR(),

              H2("What happens if expand=changelog is missing?", st),
              P("transform_data finds no status transitions and outputs empty time values "
                "for all issues. The Excel files contain no usable data. Always include "
                "<font name='Courier'>expand=changelog</font> in the URL.", st),

              H2("I get an 'Unauthorized' error when calling curl.", st),
              P("Check: Is the email address correct? Is the API token correct? Are they "
                "separated by a colon? Does your account have read access to the project? "
                "Tip: Generate a new API token if the old one was lost or expired.", st),

              H2("Can I merge multiple Jira projects?", st),
              P("Yes — either via JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) for a "
                "single export, or merge two separate exports with the Helper. Make sure "
                "the workflows of both projects are compatible.", st),

              H2("How large can the JSON file get?", st),
              P("Rule of thumb: approximately 2–5 KB per issue (depending on changelog "
                "length). 1,000 issues ≈ 2–5 MB. For very large projects (10,000+ "
                "issues), use pagination and the Helper.", st),

              H2("Should I use test data or real data?", st),
              P("For demos, training, and installation tests, synthetic test data from "
                "the <b>Testdata Generator</b> is the better choice — no privacy "
                "concerns, reproducible, and fully controlled. For real flow analyses "
                "and decisions, actual Jira data reflects the true workflow state.", st)]

    # ---- 3. Glossary ----
    story += [PageBreak(),
              H1("3  Glossary", st), HR(),
              tbl(["Term", "Explanation"],
                  [["ART",       "Agile Release Train — a team-of-teams structure in SAFe"],
                   ["API",       "Application Programming Interface — programming interface"],
                   ["API token", "Security key for accessing the Jira REST API; replaces "
                                 "the password in curl calls"],
                   ["Changelog", "Jira log of all status changes for an issue "
                                 "(requires expand=changelog)"],
                   ["CFD",       "Cumulative Flow Diagram — shows the cumulative issue count "
                                 "per stage over time"],
                   ["Closed stage", "The stage that marks an issue as completed "
                                    "(workflow.txt: &lt;Closed&gt;)"],
                   ["Cycle time",  "Time from the first active stage (&lt;First&gt;) to "
                                   "the closed stage"],
                   ["First stage", "First active stage where cycle time measurement begins "
                                   "(workflow.txt: &lt;First&gt;)"],
                   ["Helper",    "SituationReport module for merging multiple Jira JSON files"],
                   ["Issue",     "A work item in Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JQL",       "Jira Query Language — query language for Jira searches, "
                                 "e.g. project=ART_A"],
                   ["JSON",      "JavaScript Object Notation — format of Jira API exports"],
                   ["Stage",     "One step in the workflow (corresponds to a Jira column or "
                                 "status name)"],
                   ["Workflow",  "Ordered sequence of stages that an issue passes through"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate get_data manuals as PDF in German and English."""
    st = make_styles()

    for lang, output, content_fn in [
        ("de", OUTPUT_DE, content_de),
        ("en", OUTPUT_EN, content_en),
    ]:
        story = [NextPageTemplate("normal")]
        story += content_fn(st)
        doc = _GDDoc(str(output), lang=lang)
        doc.multiBuild(story)
        print(f"PDF created: {output}")


if __name__ == "__main__":
    main()
