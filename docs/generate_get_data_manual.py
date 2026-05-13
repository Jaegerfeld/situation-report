# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       08.05.2026
# Geändert:       13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für get_data als PDF in fünf Sprachen:
#   DE, EN, RO, PT, FR. Da get_data noch in Entwicklung ist, beschreibt
#   das Handbuch den manuellen Export echter Jira-Daten (REST API,
#   API-Token, curl, Paginierung, Helper).
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
OUTPUT_RO = Path(__file__).parent / "get_data_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "get_data_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "get_data_ManuelUtilisateur.pdf"

_ASSETS = Path(__file__).parent / "assets"
CONTENT_WIDTH = 15.5 * cm

C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

_HEADER = {
    "de": "get_data  --  Benutzerhandbuch",
    "en": "get_data  --  User Manual",
    "ro": "get_data  --  Manual de Utilizator",
    "pt": "get_data  --  Manual do Utilizador",
    "fr": "get_data  --  Manuel d'utilisation",
}

_PAGE_LABEL = {
    "de": "Seite %d",
    "en": "Page %d",
    "ro": "Pagina %d",
    "pt": "Página %d",
    "fr": "Page %d",
}

_COVER_SUBTITLE = {
    "de": "Benutzerhandbuch",
    "en": "User Manual",
    "ro": "Manual de Utilizator",
    "pt": "Manual do Utilizador",
    "fr": "Manuel d'utilisation",
}

_COVER_TAGLINE = {
    "de": "Jira-Daten für SituationReport exportieren",
    "en": "Export Jira data for SituationReport",
    "ro": "Exportați date Jira pentru SituationReport",
    "pt": "Exportar dados Jira para SituationReport",
    "fr": "Exporter des données Jira pour SituationReport",
}

_COVER_AUDIENCE = {
    "de": "Fuer Agile Coaches und PI Manager",
    "en": "For Agile Coaches and PI Managers",
    "ro": "Pentru Agile Coaches si Manageri PI",
    "pt": "Para Agile Coaches e Gestores de PI",
    "fr": "Pour les Agile Coaches et les PI Managers",
}


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles() -> dict:
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

    def __init__(self, filename: str, lang: str = "de", **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        self._header_text = _HEADER[lang]
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
        canvas.drawCentredString(w / 2, 1.0 * cm, _PAGE_LABEL[self._lang] % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2 * cm, 1.4 * cm, w - 2.2 * cm, 1.4 * cm)
        canvas.restoreState()


def _build_cover(canvas, doc, lang: str = "de"):
    w, h = A4
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
    canvas.drawCentredString(w / 2, h * 0.515, _COVER_SUBTITLE[lang])
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w / 2, h * 0.47, _COVER_TAGLINE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w * 0.2, h * 0.44, w * 0.8, h * 0.44)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w / 2, h * 0.12,
                             "situation-report -- github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w / 2, h * 0.09,
                             f"{_COVER_AUDIENCE[lang]} -- Version {_VERSION}")
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
    story = []

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
    story = []

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
# Content — Romanian
# ---------------------------------------------------------------------------

def content_ro(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  Exportul datelor din Jira Cloud", st), HR(),
              box("<b>Notă:</b> Modulul <b>get_data</b> este încă în curs de dezvoltare. "
                  "Acest manual descrie exportul manual al datelor Jira prin intermediul "
                  "API-ului REST Jira. Acesta este același proces pe care get_data îl va "
                  "automatiza — fișierele JSON exportate pot fi procesate direct de "
                  "<b>transform_data</b>.", st,
                  bg="#fff8e1"),
              SP(10),
              P("Acest capitol explică cum să exportați date reale despre issue-uri din "
                "Jira Cloud pentru SituationReport. Exportul produce aceeași structură "
                "JSON ca și Generatorul de date de test — transform_data le procesează "
                "pe ambele identic.", st),

              H2("1.1  Ce aveți nevoie", st),
              tbl(["Cerință", "Detalii"],
                  [["Cont Jira Cloud",
                    "Un cont cu acces de citire la proiectul dorit"],
                   ["Token API",
                    "Token personal de la id.atlassian.com — creat o singură dată"],
                   ["Cheia proiectului",
                    "Codul scurt al proiectului Jira, ex. 'ART_A' sau 'SCRUM'"],
                   ["curl sau browser",
                    "curl pentru interogări automate; browser pentru teste rapide"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(8),

              H2("1.2  Crearea unui token API", st),
              P("Token-ul API înlocuiește parola pentru apelurile API și se creează o singură dată:", st),
              tbl(["Pas", "Acțiune"],
                  [["1", "Deschideți https://id.atlassian.com în browser (conectat la Jira)"],
                   ["2", "Security → API tokens → Create API token"],
                   ["3", "Introduceți o etichetă, ex. 'SituationReport', faceți clic pe 'Create'"],
                   ["4", "Copiați token-ul și păstrați-l în siguranță — este afișat o singură dată!"]],
                  col_widths=[1.5 * cm, 14 * cm]),
              SP(4),
              HI("Notă de securitate: Tratați token-ul API ca pe o parolă. Păstrați-l "
                 "într-un manager de parole și nu îl distribuiți.", st),
              SP(6),

              H2("1.3  Interogarea API-ului REST Jira", st),
              P("Jira Cloud oferă două variante de API. Utilizați API-ul v3 curent pentru "
                "scripturile noi; scripturile v2 existente continuă să funcționeze. "
                "<font name='Courier'>expand=changelog</font> este <b>obligatoriu în ambele</b> "
                "variante — fără el, tranzițiile de status lipsesc și transform_data "
                "nu poate calcula valorile de timp pe etapă.", st),

              H3("API curent (v3) – recomandat", st),
              P("Endpoint: <font name='Courier'>POST /rest/api/3/search/jql</font><br/>"
                "Parametrii sunt transmiși ca corp JSON al cererii. "
                "Răspunsul include suplimentar "
                "<font name='Courier'>isLast</font> și "
                "<font name='Courier'>nextPageToken</font> pentru paginare "
                "(Secțiunea 1.5).", st),
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
              HI("maxResults este limitat la 100 de issue-uri per cerere cu API-ul v3. "
                 "Utilizați nextPageToken pentru proiecte cu mai mult de 100 de issue-uri "
                 "(Secțiunea 1.5).", st),
              SP(6),

              H3("API mai vechi (v2) – încă suportat", st),
              P("Endpoint: <font name='Courier'>GET /rest/api/2/search</font><br/>"
                "Parametrii ca șir de interogare URL. Suportă până la 1.000 de issue-uri "
                "per cerere și paginare bazată pe offset cu "
                "<font name='Courier'>startAt</font>.", st),
              PRE("curl -u \"name@company.com:YourAPIToken\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              HI("Sfat: Pentru scripturile noi, API-ul v3 este preferat. "
                 "Scripturile v2 existente nu trebuie migrate.", st),
              SP(6),

              H2("1.4  Câmpurile necesare pentru transform_data", st),
              tbl(["Câmp Jira", "Obligatoriu", "Scop"],
                  [["key", "✓",
                    "Identificatorul issue-ului (ex. ART_A-001)"],
                   ["fields.issuetype.name", "✓",
                    "Tipul issue-ului pentru filtrare (Feature, Bug, ...)"],
                   ["fields.created", "✓",
                    "Data creării issue-ului"],
                   ["fields.status.name", "✓",
                    "Statusul curent"],
                   ["changelog (expand=changelog)", "✓",
                    "Tranziții de status cu marcaje de timp — TREBUIE setat în URL"],
                   ["fields.resolution", "–",
                    "Opțional — tipul rezoluției (ex. 'Done', 'Won't Fix')"],
                   ["fields.summary", "–",
                    "Opțional — titlul issue-ului"]],
                  col_widths=[5.5 * cm, 1.5 * cm, 8.5 * cm]),
              SP(6),

              H2("1.5  Paginare – mai mult de 100 de issue-uri", st),

              H3("API v3 – Paginare bazată pe cursor (nextPageToken)", st),
              P("API-ul v3 returnează cel mult 100 de issue-uri per cerere. Fiecare răspuns "
                "conține fie un <font name='Courier'>nextPageToken</font> pentru "
                "pagina următoare, fie <font name='Courier'>\"isLast\": true</font> când "
                "toate issue-urile au fost preluate. Paginile trebuie preluate "
                "<b>secvențial</b> — token-ul din răspunsul curent se folosește în "
                "cererea următoare.", st),
              PRE("# Pagina 1 – fara nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Cititi nextPageToken din pagina 1:\n"
                  "#   cat ART_A_page1.json | grep nextPageToken\n"
                  "#   (sau cu jq: jq -r '.nextPageToken' ART_A_page1.json)\n\n"
                  "# Pagina 2 – inserati nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"],\n"
                  "       \"nextPageToken\":\"<token din pagina 1>\"}' \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Repetati pana cand isLast:true apare in raspuns\n\n"
                  "# Imbinati toate paginile\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json ... \\\n"
                  "  --output ART_A_merged.json", st),
              P("Repetați până când răspunsul conține "
                "<font name='Courier'>\"isLast\": true</font>. "
                "<b>Helper</b> îmbină toate paginile și elimină duplicatele "
                "automat.", st),
              SP(6),

              H3("API v2 – Paginare bazată pe offset (startAt) – Moștenit", st),
              P("API-ul v2 suportă până la 1.000 de issue-uri per cerere. "
                "Cu <font name='Courier'>startAt</font>, orice pagină poate fi accesată "
                "direct. <b>Important:</b> "
                "<font name='Courier'>startAt</font> este compatibil doar cu endpoint-ul "
                "v2 — nu cu noul endpoint v3.", st),
              PRE("# Pagina 1 (issue-urile 1-1.000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Pagina 2 (issue-urile 1.001-2.000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Imbinati fisierele cu Helper\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Incrementați <font name='Courier'>startAt</font> cu 1.000 până când "
                "răspunsul conține mai puțin de 1.000 de issue-uri.", st),
              SP(6),

              H2("1.6  De la exportul JSON la fișierul de flux", st),
              P("După export, creați un fișier de flux care mapează statusurile reale "
                "din Jira. Următorul fragment Python extrage toate numele de statusuri "
                "din export:", st),
              PRE("import json\n"
                  "data = json.loads(open('ART_A_page1.json').read())\n"
                  "statuses = set()\n"
                  "for issue in data['issues']:\n"
                  "    for h in issue['changelog']['histories']:\n"
                  "        for item in h['items']:\n"
                  "            if item['field'] == 'status':\n"
                  "                statuses.add(item['toString'])\n"
                  "print(sorted(statuses))", st),
              P("Din numele de statusuri găsite, creați un "
                "<font name='Courier'>workflow.txt</font> — ordonați statusurile în "
                "ordine logică și setați marcatorii "
                "<font name='Courier'>&lt;First&gt;</font> și "
                "<font name='Courier'>&lt;Closed&gt;</font>. "
                "Formatul fișierului de flux este descris în Manualul de Utilizator "
                "<b>transform_data</b>.", st)]

    story += [PageBreak(),
              H1("2  Întrebări frecvente (FAQ)", st), HR(),

              H2("Ce se întâmplă dacă expand=changelog lipsește?", st),
              P("transform_data nu găsește nicio tranziție de status și produce valori de "
                "timp goale pentru toate issue-urile. Fișierele Excel nu conțin date "
                "utilizabile. Includeți întotdeauna "
                "<font name='Courier'>expand=changelog</font> în URL.", st),

              H2("Primesc o eroare 'Unauthorized' la apelul curl.", st),
              P("Verificați: Adresa de e-mail este corectă? Token-ul API este corect? "
                "Sunt separate prin două puncte? Contul dvs. are acces de citire la "
                "proiect? Sfat: Generați un nou token API dacă cel vechi a fost pierdut "
                "sau a expirat.", st),

              H2("Pot îmbina mai multe proiecte Jira?", st),
              P("Da — fie prin JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) pentru un "
                "singur export, fie îmbinând două exporturi separate cu Helper. "
                "Asigurați-vă că fluxurile de lucru ale ambelor proiecte sunt "
                "compatibile.", st),

              H2("Cât de mare poate deveni fișierul JSON?", st),
              P("Regulă generală: aproximativ 2–5 KB per issue (în funcție de lungimea "
                "changelog-ului). 1.000 de issue-uri ≈ 2–5 MB. Pentru proiecte foarte "
                "mari (10.000+ issue-uri), utilizați paginarea și Helper-ul.", st),

              H2("Ar trebui să folosesc date de test sau date reale?", st),
              P("Pentru demonstrații, instruire și teste de instalare, datele sintetice "
                "de test din <b>Testdata Generator</b> sunt alegerea mai bună — fără "
                "probleme de confidențialitate, reproductibile și complet controlate. "
                "Pentru analize reale de flux și decizii, datele reale Jira reflectă "
                "starea reală a fluxului de lucru.", st)]

    story += [PageBreak(),
              H1("3  Glosar", st), HR(),
              tbl(["Termen", "Explicație"],
                  [["ART",       "Agile Release Train — o structură de echipe în SAFe"],
                   ["API",       "Application Programming Interface — interfață de programare"],
                   ["Token API", "Cheie de securitate pentru accesul la API-ul REST Jira; "
                                 "înlocuiește parola în apelurile curl"],
                   ["Changelog", "Jurnalul Jira al tuturor modificărilor de status pentru un "
                                 "issue (necesită expand=changelog)"],
                   ["CFD",       "Cumulative Flow Diagram — arată numărul cumulativ de "
                                 "issue-uri per etapă în timp"],
                   ["Etapa Closed", "Etapa care marchează un issue ca finalizat "
                                    "(workflow.txt: &lt;Closed&gt;)"],
                   ["Timp de ciclu", "Timp de la prima etapă activă (&lt;First&gt;) până la "
                                     "etapa closed"],
                   ["Etapa First", "Prima etapă activă de unde începe măsurarea timpului de "
                                   "ciclu (workflow.txt: &lt;First&gt;)"],
                   ["Helper",    "Modulul SituationReport pentru îmbinarea mai multor fișiere JSON Jira"],
                   ["Issue",     "Un element de lucru în Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JQL",       "Jira Query Language — limbaj de interogare pentru căutări "
                                 "Jira, ex. project=ART_A"],
                   ["JSON",      "JavaScript Object Notation — formatul exporturilor API Jira"],
                   ["Etapă",     "Un pas în fluxul de lucru (corespunde unei coloane sau "
                                 "unui nume de status Jira)"],
                   ["Flux de lucru", "Secvența ordonată de etape prin care trece un issue"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — Portuguese
# ---------------------------------------------------------------------------

def content_pt(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  Exportar dados do Jira Cloud", st), HR(),
              box("<b>Nota:</b> O módulo <b>get_data</b> está ainda em desenvolvimento. "
                  "Este manual descreve a exportação manual de dados Jira através da "
                  "API REST do Jira. Este é o mesmo processo que o get_data irá automatizar "
                  "— os ficheiros JSON exportados podem ser processados diretamente pelo "
                  "<b>transform_data</b>.", st,
                  bg="#fff8e1"),
              SP(10),
              P("Este capítulo explica como exportar dados reais de issues do Jira Cloud "
                "para o SituationReport. A exportação produz a mesma estrutura JSON que o "
                "Gerador de Dados de Teste — o transform_data processa ambos de forma "
                "idêntica.", st),

              H2("1.1  O que precisa", st),
              tbl(["Requisito", "Detalhes"],
                  [["Conta Jira Cloud",
                    "Uma conta com acesso de leitura ao projeto pretendido"],
                   ["Token de API",
                    "Token pessoal de id.atlassian.com — criado uma única vez"],
                   ["Chave do projeto",
                    "O código abreviado do projeto Jira, ex. 'ART_A' ou 'SCRUM'"],
                   ["curl ou browser",
                    "curl para consultas automatizadas; browser para testes rápidos"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(8),

              H2("1.2  Criar um token de API", st),
              P("O token de API substitui a sua palavra-passe nas chamadas de API e é criado uma única vez:", st),
              tbl(["Passo", "Ação"],
                  [["1", "Abra https://id.atlassian.com no browser (com sessão iniciada no Jira)"],
                   ["2", "Security → API tokens → Create API token"],
                   ["3", "Introduza uma etiqueta, ex. 'SituationReport', clique em 'Create'"],
                   ["4", "Copie o token e guarde-o em segurança — é mostrado apenas uma vez!"]],
                  col_widths=[1.5 * cm, 14 * cm]),
              SP(4),
              HI("Nota de segurança: Trate o token de API como uma palavra-passe. "
                 "Guarde-o num gestor de palavras-passe e não o partilhe.", st),
              SP(6),

              H2("1.3  Consultar a API REST do Jira", st),
              P("O Jira Cloud oferece duas variantes de API. Utilize a API v3 atual para "
                "novos scripts; os scripts v2 existentes continuam a funcionar. "
                "<font name='Courier'>expand=changelog</font> é <b>obrigatório em ambas</b> "
                "as variantes — sem ele, as transições de estado estão em falta e o "
                "transform_data não consegue calcular os valores de tempo por etapa.", st),

              H3("API atual (v3) – recomendada", st),
              P("Endpoint: <font name='Courier'>POST /rest/api/3/search/jql</font><br/>"
                "Os parâmetros são passados como corpo JSON do pedido. "
                "A resposta inclui adicionalmente "
                "<font name='Courier'>isLast</font> e "
                "<font name='Courier'>nextPageToken</font> para paginação "
                "(Secção 1.5).", st),
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
              HI("maxResults está limitado a 100 issues por pedido com a API v3. "
                 "Utilize nextPageToken para projetos com mais de 100 issues "
                 "(Secção 1.5).", st),
              SP(6),

              H3("API mais antiga (v2) – ainda suportada", st),
              P("Endpoint: <font name='Courier'>GET /rest/api/2/search</font><br/>"
                "Parâmetros como cadeia de consulta URL. Suporta até 1.000 issues por "
                "pedido e paginação baseada em offset com "
                "<font name='Courier'>startAt</font>.", st),
              PRE("curl -u \"name@company.com:YourAPIToken\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              HI("Dica: Para novos scripts, a API v3 é preferida. "
                 "Os scripts v2 existentes não precisam de ser migrados.", st),
              SP(6),

              H2("1.4  Campos necessários para o transform_data", st),
              tbl(["Campo Jira", "Obrigatório", "Finalidade"],
                  [["key", "✓",
                    "Identificador do issue (ex. ART_A-001)"],
                   ["fields.issuetype.name", "✓",
                    "Tipo de issue para filtragem (Feature, Bug, ...)"],
                   ["fields.created", "✓",
                    "Data de criação do issue"],
                   ["fields.status.name", "✓",
                    "Estado atual"],
                   ["changelog (expand=changelog)", "✓",
                    "Transições de estado com marcas de tempo — DEVE ser definido no URL"],
                   ["fields.resolution", "–",
                    "Opcional — tipo de resolução (ex. 'Done', 'Won't Fix')"],
                   ["fields.summary", "–",
                    "Opcional — título do issue"]],
                  col_widths=[5.5 * cm, 1.5 * cm, 8.5 * cm]),
              SP(6),

              H2("1.5  Paginação – mais de 100 issues", st),

              H3("API v3 – Paginação baseada em cursor (nextPageToken)", st),
              P("A API v3 devolve no máximo 100 issues por pedido. Cada resposta "
                "contém um <font name='Courier'>nextPageToken</font> para a "
                "página seguinte, ou <font name='Courier'>\"isLast\": true</font> quando "
                "todos os issues foram obtidos. As páginas devem ser obtidas "
                "<b>sequencialmente</b> — o token da resposta atual é utilizado no "
                "pedido seguinte.", st),
              PRE("# Pagina 1 – sem nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Ler nextPageToken da pagina 1:\n"
                  "#   cat ART_A_page1.json | grep nextPageToken\n"
                  "#   (ou com jq: jq -r '.nextPageToken' ART_A_page1.json)\n\n"
                  "# Pagina 2 – inserir nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"],\n"
                  "       \"nextPageToken\":\"<token da pagina 1>\"}' \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Repetir ate isLast:true aparecer na resposta\n\n"
                  "# Fundir todas as paginas\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json ... \\\n"
                  "  --output ART_A_merged.json", st),
              P("Repita até a resposta conter "
                "<font name='Courier'>\"isLast\": true</font>. "
                "O <b>Helper</b> funde todas as páginas e remove duplicados "
                "automaticamente.", st),
              SP(6),

              H3("API v2 – Paginação baseada em offset (startAt) – Legado", st),
              P("A API v2 suporta até 1.000 issues por pedido. "
                "Com <font name='Courier'>startAt</font>, qualquer página pode ser "
                "acedida diretamente. <b>Importante:</b> "
                "<font name='Courier'>startAt</font> é compatível apenas com o endpoint "
                "v2 — não com o novo endpoint v3.", st),
              PRE("# Pagina 1 (issues 1-1.000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Pagina 2 (issues 1.001-2.000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Fundir ficheiros com o Helper\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Incremente <font name='Courier'>startAt</font> em 1.000 até a "
                "resposta conter menos de 1.000 issues.", st),
              SP(6),

              H2("1.6  Do exporto JSON ao ficheiro de fluxo", st),
              P("Após a exportação, crie um ficheiro de fluxo que mapeia os seus "
                "estados reais do Jira. O seguinte fragmento Python extrai todos os "
                "nomes de estado da exportação:", st),
              PRE("import json\n"
                  "data = json.loads(open('ART_A_page1.json').read())\n"
                  "statuses = set()\n"
                  "for issue in data['issues']:\n"
                  "    for h in issue['changelog']['histories']:\n"
                  "        for item in h['items']:\n"
                  "            if item['field'] == 'status':\n"
                  "                statuses.add(item['toString'])\n"
                  "print(sorted(statuses))", st),
              P("A partir dos nomes de estado encontrados, crie um "
                "<font name='Courier'>workflow.txt</font> — organize os estados em "
                "ordem lógica e defina os marcadores "
                "<font name='Courier'>&lt;First&gt;</font> e "
                "<font name='Courier'>&lt;Closed&gt;</font>. "
                "O formato do ficheiro de fluxo é descrito no Manual do Utilizador "
                "do <b>transform_data</b>.", st)]

    story += [PageBreak(),
              H1("2  Perguntas Frequentes (FAQ)", st), HR(),

              H2("O que acontece se expand=changelog estiver em falta?", st),
              P("O transform_data não encontra transições de estado e produz valores de "
                "tempo vazios para todos os issues. Os ficheiros Excel não contêm dados "
                "utilizáveis. Inclua sempre "
                "<font name='Courier'>expand=changelog</font> no URL.", st),

              H2("Recebo um erro 'Unauthorized' ao chamar o curl.", st),
              P("Verifique: O endereço de e-mail está correto? O token de API está "
                "correto? Estão separados por dois pontos? A sua conta tem acesso de "
                "leitura ao projeto? Dica: Gere um novo token de API se o antigo foi "
                "perdido ou expirou.", st),

              H2("Posso fundir vários projetos Jira?", st),
              P("Sim — seja via JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) para uma "
                "única exportação, ou fundindo duas exportações separadas com o Helper. "
                "Certifique-se de que os fluxos de trabalho de ambos os projetos são "
                "compatíveis.", st),

              H2("Qual o tamanho máximo do ficheiro JSON?", st),
              P("Regra geral: aproximadamente 2–5 KB por issue (dependendo do tamanho "
                "do changelog). 1.000 issues ≈ 2–5 MB. Para projetos muito grandes "
                "(10.000+ issues), utilize paginação e o Helper.", st),

              H2("Devo usar dados de teste ou dados reais?", st),
              P("Para demonstrações, formação e testes de instalação, os dados de teste "
                "sintéticos do <b>Testdata Generator</b> são a melhor escolha — sem "
                "preocupações de privacidade, reproduzíveis e totalmente controlados. "
                "Para análises reais de fluxo e decisões, os dados reais do Jira "
                "refletem o estado verdadeiro do fluxo de trabalho.", st)]

    story += [PageBreak(),
              H1("3  Glossário", st), HR(),
              tbl(["Termo", "Explicação"],
                  [["ART",       "Agile Release Train — uma estrutura de equipas em SAFe"],
                   ["API",       "Application Programming Interface — interface de programação"],
                   ["Token de API", "Chave de segurança para aceder à API REST do Jira; "
                                    "substitui a palavra-passe nas chamadas curl"],
                   ["Changelog", "Registo Jira de todas as alterações de estado de um issue "
                                 "(requer expand=changelog)"],
                   ["CFD",       "Cumulative Flow Diagram — mostra a contagem cumulativa de "
                                 "issues por etapa ao longo do tempo"],
                   ["Etapa Closed", "A etapa que marca um issue como concluído "
                                    "(workflow.txt: &lt;Closed&gt;)"],
                   ["Tempo de ciclo", "Tempo desde a primeira etapa ativa (&lt;First&gt;) "
                                      "até à etapa closed"],
                   ["Etapa First", "Primeira etapa ativa onde começa a medição do tempo de "
                                   "ciclo (workflow.txt: &lt;First&gt;)"],
                   ["Helper",    "Módulo SituationReport para fundir múltiplos ficheiros JSON do Jira"],
                   ["Issue",     "Um item de trabalho no Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JQL",       "Jira Query Language — linguagem de consulta para pesquisas "
                                 "Jira, ex. project=ART_A"],
                   ["JSON",      "JavaScript Object Notation — formato das exportações da API Jira"],
                   ["Etapa",     "Um passo no fluxo de trabalho (corresponde a uma coluna ou "
                                 "nome de estado Jira)"],
                   ["Fluxo de trabalho", "Sequência ordenada de etapas pelas quais um issue passa"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — French
# ---------------------------------------------------------------------------

def content_fr(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  Exporter des données depuis Jira Cloud", st), HR(),
              box("<b>Remarque :</b> Le module <b>get_data</b> est encore en cours de "
                  "développement. Ce manuel décrit l'export manuel de données Jira via "
                  "l'API REST Jira. C'est le même processus que get_data automatisera "
                  "— les fichiers JSON exportés peuvent être traités directement par "
                  "<b>transform_data</b>.", st,
                  bg="#fff8e1"),
              SP(10),
              P("Ce chapitre explique comment exporter des données réelles d'issues "
                "depuis Jira Cloud pour SituationReport. L'export produit la même "
                "structure JSON que le Générateur de données de test — transform_data "
                "traite les deux de manière identique.", st),

              H2("1.1  Ce dont vous avez besoin", st),
              tbl(["Prérequis", "Détails"],
                  [["Compte Jira Cloud",
                    "Un compte avec accès en lecture au projet souhaité"],
                   ["Token d'API",
                    "Token personnel depuis id.atlassian.com — créé une seule fois"],
                   ["Clé du projet",
                    "Le code abrégé du projet Jira, ex. 'ART_A' ou 'SCRUM'"],
                   ["curl ou navigateur",
                    "curl pour les requêtes automatisées ; navigateur pour les tests rapides"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(8),

              H2("1.2  Créer un token d'API", st),
              P("Le token d'API remplace votre mot de passe pour les appels API et est créé une seule fois :", st),
              tbl(["Étape", "Action"],
                  [["1", "Ouvrez https://id.atlassian.com dans votre navigateur (connecté à Jira)"],
                   ["2", "Security → API tokens → Create API token"],
                   ["3", "Saisissez un libellé, ex. 'SituationReport', cliquez sur 'Create'"],
                   ["4", "Copiez le token et conservez-le en sécurité — il n'est affiché qu'une seule fois !"]],
                  col_widths=[1.5 * cm, 14 * cm]),
              SP(4),
              HI("Note de sécurité : Traitez le token d'API comme un mot de passe. "
                 "Conservez-le dans un gestionnaire de mots de passe et ne le partagez pas.", st),
              SP(6),

              H2("1.3  Interroger l'API REST Jira", st),
              P("Jira Cloud propose deux variantes d'API. Utilisez l'API v3 actuelle pour "
                "les nouveaux scripts ; les scripts v2 existants continuent de fonctionner. "
                "<font name='Courier'>expand=changelog</font> est <b>obligatoire dans les deux</b> "
                "variantes — sans lui, les transitions de statut sont absentes et "
                "transform_data ne peut pas calculer les valeurs de temps par étape.", st),

              H3("API actuelle (v3) – recommandée", st),
              P("Endpoint : <font name='Courier'>POST /rest/api/3/search/jql</font><br/>"
                "Les paramètres sont transmis dans le corps JSON de la requête. "
                "La réponse inclut également "
                "<font name='Courier'>isLast</font> et "
                "<font name='Courier'>nextPageToken</font> pour la pagination "
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
              HI("maxResults est limité à 100 issues par requête avec l'API v3. "
                 "Utilisez nextPageToken pour les projets avec plus de 100 issues "
                 "(Section 1.5).", st),
              SP(6),

              H3("API plus ancienne (v2) – toujours supportée", st),
              P("Endpoint : <font name='Courier'>GET /rest/api/2/search</font><br/>"
                "Paramètres sous forme de chaîne de requête URL. Supporte jusqu'à "
                "1 000 issues par requête et la pagination basée sur offset avec "
                "<font name='Courier'>startAt</font>.", st),
              PRE("curl -u \"name@company.com:YourAPIToken\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              HI("Conseil : Pour les nouveaux scripts, l'API v3 est préférée. "
                 "Les scripts v2 existants n'ont pas besoin d'être migrés.", st),
              SP(6),

              H2("1.4  Champs requis par transform_data", st),
              tbl(["Champ Jira", "Obligatoire", "Rôle"],
                  [["key", "✓",
                    "Identifiant de l'issue (ex. ART_A-001)"],
                   ["fields.issuetype.name", "✓",
                    "Type d'issue pour le filtrage (Feature, Bug, ...)"],
                   ["fields.created", "✓",
                    "Date de création de l'issue"],
                   ["fields.status.name", "✓",
                    "Statut actuel"],
                   ["changelog (expand=changelog)", "✓",
                    "Transitions de statut avec horodatages — DOIT être défini dans l'URL"],
                   ["fields.resolution", "–",
                    "Optionnel — type de résolution (ex. 'Done', 'Won't Fix')"],
                   ["fields.summary", "–",
                    "Optionnel — titre de l'issue"]],
                  col_widths=[5.5 * cm, 1.5 * cm, 8.5 * cm]),
              SP(6),

              H2("1.5  Pagination – plus de 100 issues", st),

              H3("API v3 – Pagination basée sur curseur (nextPageToken)", st),
              P("L'API v3 renvoie au maximum 100 issues par requête. Chaque réponse "
                "contient soit un <font name='Courier'>nextPageToken</font> pour la "
                "page suivante, soit <font name='Courier'>\"isLast\": true</font> quand "
                "tous les issues ont été récupérés. Les pages doivent être récupérées "
                "<b>séquentiellement</b> — le token de la réponse courante est utilisé "
                "dans la requête suivante.", st),
              PRE("# Page 1 – sans nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"]}' \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Lire nextPageToken depuis la page 1 :\n"
                  "#   cat ART_A_page1.json | grep nextPageToken\n"
                  "#   (ou avec jq: jq -r '.nextPageToken' ART_A_page1.json)\n\n"
                  "# Page 2 – inserer nextPageToken\n"
                  "curl -X POST \\\n"
                  "  \"https://company.atlassian.net/rest/api/3/search/jql\" \\\n"
                  "  -u \"name@company.com:Token\" \\\n"
                  "  -H \"Content-Type: application/json\" \\\n"
                  "  -d '{\"jql\":\"project=ART_A ORDER BY created ASC\",\n"
                  "       \"maxResults\":100,\"expand\":[\"changelog\"],\n"
                  "       \"fields\":[\"issuetype\",\"created\",\n"
                  "                  \"status\",\"summary\"],\n"
                  "       \"nextPageToken\":\"<token de la page 1>\"}' \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Repeter jusqu'a ce que isLast:true apparaisse\n\n"
                  "# Fusionner toutes les pages\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json ... \\\n"
                  "  --output ART_A_merged.json", st),
              P("Répétez jusqu'à ce que la réponse contienne "
                "<font name='Courier'>\"isLast\": true</font>. "
                "Le <b>Helper</b> fusionne toutes les pages et supprime les doublons "
                "automatiquement.", st),
              SP(6),

              H3("API v2 – Pagination basée sur offset (startAt) – Ancien", st),
              P("L'API v2 supporte jusqu'à 1 000 issues par requête. "
                "Avec <font name='Courier'>startAt</font>, n'importe quelle page peut "
                "être accédée directement. <b>Important :</b> "
                "<font name='Courier'>startAt</font> n'est compatible qu'avec l'endpoint "
                "v2 — pas avec le nouvel endpoint v3.", st),
              PRE("# Page 1 (issues 1-1 000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Page 2 (issues 1 001-2 000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Fusionner les fichiers avec le Helper\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Incrémentez <font name='Courier'>startAt</font> de 1 000 jusqu'à ce que "
                "la réponse contienne moins de 1 000 issues.", st),
              SP(6),

              H2("1.6  De l'export JSON au fichier de flux", st),
              P("Après l'export, créez un fichier de flux qui associe vos statuts Jira "
                "réels. Le fragment Python suivant extrait tous les noms de statut de "
                "l'export :", st),
              PRE("import json\n"
                  "data = json.loads(open('ART_A_page1.json').read())\n"
                  "statuses = set()\n"
                  "for issue in data['issues']:\n"
                  "    for h in issue['changelog']['histories']:\n"
                  "        for item in h['items']:\n"
                  "            if item['field'] == 'status':\n"
                  "                statuses.add(item['toString'])\n"
                  "print(sorted(statuses))", st),
              P("À partir des noms de statut trouvés, créez un "
                "<font name='Courier'>workflow.txt</font> — organisez les statuts dans "
                "un ordre logique et définissez les marqueurs "
                "<font name='Courier'>&lt;First&gt;</font> et "
                "<font name='Courier'>&lt;Closed&gt;</font>. "
                "Le format du fichier de flux est décrit dans le Manuel d'utilisation "
                "de <b>transform_data</b>.", st)]

    story += [PageBreak(),
              H1("2  Foire aux Questions (FAQ)", st), HR(),

              H2("Que se passe-t-il si expand=changelog est absent ?", st),
              P("transform_data ne trouve aucune transition de statut et produit des "
                "valeurs de temps vides pour tous les issues. Les fichiers Excel ne "
                "contiennent pas de données exploitables. Incluez toujours "
                "<font name='Courier'>expand=changelog</font> dans l'URL.", st),

              H2("J'obtiens une erreur 'Unauthorized' lors de l'appel curl.", st),
              P("Vérifiez : L'adresse e-mail est-elle correcte ? Le token d'API est-il "
                "correct ? Sont-ils séparés par deux-points ? Votre compte dispose-t-il "
                "d'un accès en lecture au projet ? Conseil : Générez un nouveau token "
                "d'API si l'ancien a été perdu ou a expiré.", st),

              H2("Puis-je fusionner plusieurs projets Jira ?", st),
              P("Oui — soit via JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) pour un "
                "seul export, soit en fusionnant deux exports séparés avec le Helper. "
                "Assurez-vous que les flux de travail des deux projets sont compatibles.", st),

              H2("Quelle taille peut atteindre le fichier JSON ?", st),
              P("Règle générale : environ 2–5 Ko par issue (selon la longueur du "
                "changelog). 1 000 issues ≈ 2–5 Mo. Pour les très grands projets "
                "(10 000+ issues), utilisez la pagination et le Helper.", st),

              H2("Dois-je utiliser des données de test ou des données réelles ?", st),
              P("Pour les démonstrations, la formation et les tests d'installation, les "
                "données de test synthétiques du <b>Testdata Generator</b> sont le "
                "meilleur choix — sans problèmes de confidentialité, reproductibles et "
                "entièrement contrôlées. Pour les analyses de flux réelles et les "
                "décisions, les données Jira réelles reflètent l'état réel du flux de "
                "travail.", st)]

    story += [PageBreak(),
              H1("3  Glossaire", st), HR(),
              tbl(["Terme", "Explication"],
                  [["ART",       "Agile Release Train — une structure d'équipes dans SAFe"],
                   ["API",       "Application Programming Interface — interface de programmation"],
                   ["Token d'API", "Clé de sécurité pour accéder à l'API REST Jira ; remplace "
                                   "le mot de passe dans les appels curl"],
                   ["Changelog", "Journal Jira de tous les changements de statut d'un issue "
                                 "(nécessite expand=changelog)"],
                   ["CFD",       "Cumulative Flow Diagram — montre le nombre cumulatif "
                                 "d'issues par étape dans le temps"],
                   ["Étape Closed", "L'étape qui marque un issue comme terminé "
                                    "(workflow.txt : &lt;Closed&gt;)"],
                   ["Temps de cycle", "Temps entre la première étape active (&lt;First&gt;) "
                                      "et l'étape closed"],
                   ["Étape First", "Première étape active où commence la mesure du temps de "
                                   "cycle (workflow.txt : &lt;First&gt;)"],
                   ["Helper",    "Module SituationReport pour fusionner plusieurs fichiers JSON Jira"],
                   ["Issue",     "Un élément de travail dans Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JQL",       "Jira Query Language — langage de requête pour les recherches "
                                 "Jira, ex. project=ART_A"],
                   ["JSON",      "JavaScript Object Notation — format des exports de l'API Jira"],
                   ["Étape",     "Une étape dans le flux de travail (correspond à une colonne "
                                 "ou un nom de statut Jira)"],
                   ["Flux de travail", "Séquence ordonnée d'étapes par lesquelles passe un issue"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st = make_styles()

    for lang, output, content_fn in [
        ("de", OUTPUT_DE, content_de),
        ("en", OUTPUT_EN, content_en),
        ("ro", OUTPUT_RO, content_ro),
        ("pt", OUTPUT_PT, content_pt),
        ("fr", OUTPUT_FR, content_fr),
    ]:
        story = [NextPageTemplate("normal")]
        story += content_fn(st)
        doc = _GDDoc(str(output), lang=lang)
        doc.multiBuild(story)
        print(f"PDF erstellt: {output}")


if __name__ == "__main__":
    main()
