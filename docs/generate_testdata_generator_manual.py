# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für testdata_generator als PDF in Deutsch und
#   Englisch. Beschreibt Start, Workflow-Datei, Parameter, vollständiges ART_A-
#   Beispiel sowie den Export echter Daten aus Jira Cloud (API-Token, curl,
#   Paginierung, Helper-Nutzung).
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

try:
    from reportlab.platypus import Image as RLImage
    _HAS_IMAGE = True
except ImportError:
    _HAS_IMAGE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DE = Path(__file__).parent / "testdata_generator_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "testdata_generator_UserManual.pdf"

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
        h1=s("TDG_H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8, keepWithNext=1),
        h2=s("TDG_H2", fontName="Helvetica-Bold", fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5, keepWithNext=1),
        h3=s("TDG_H3", fontName="Helvetica-BoldOblique", fontSize=11, textColor=C_BLUE,
              spaceBefore=10, spaceAfter=4, keepWithNext=1),
        body=s("TDG_Body", fontName="Helvetica", fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("TDG_Bullet", fontName="Helvetica", fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3, bulletIndent=4),
        code=s("TDG_Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("TDG_Hint", fontName="Helvetica-Oblique", fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        caption=s("TDG_Caption", fontName="Helvetica-Oblique", fontSize=8,
                  textColor=C_HINT, leading=11, alignment=TA_CENTER, spaceAfter=8),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

class _TDGDoc(BaseDocTemplate):
    """BaseDocTemplate with cover and normal page templates."""

    def __init__(self, filename: str, lang: str = "de", **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        self._header_text = (
            "testdata_generator  --  Benutzerhandbuch"
            if lang == "de"
            else "testdata_generator  --  User Manual"
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
        "Synthetische Jira-Daten erzeugen und echte Daten aus Jira Cloud exportieren"
        if lang == "de"
        else "Generate synthetic Jira data and export real data from Jira Cloud"
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
    canvas.drawCentredString(w / 2, h * 0.57, "testdata_generator")
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


def img(filename: str, width_cm: float, caption_text: str | None = None,
        st: dict | None = None) -> list:
    """
    Return image flowable list for embedding in a story.

    Args:
        filename:     Image filename relative to docs/assets/.
        width_cm:     Render width in centimetres (height scaled proportionally).
        caption_text: Optional caption paragraph below the image.
        st:           Style dictionary from make_styles().

    Returns:
        List of Platypus flowables (image + optional caption + spacer).
    """
    path = _ASSETS / filename
    if _HAS_IMAGE and path.exists():
        image = RLImage(str(path))
        aspect = image.imageHeight / float(image.imageWidth)
        image.drawWidth = width_cm * cm
        image.drawHeight = image.drawWidth * aspect
        result = [image]
        if caption_text and st:
            result.append(Paragraph(caption_text, st["caption"]))
        result.append(SP(8))
        return result
    placeholder = Paragraph(f"[Screenshot: {filename}]",
                             st["hint"] if st else ParagraphStyle("ph"))
    return [placeholder, SP(4)]


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

    # ---- 1. Was ist der Testdata Generator? ----
    story += [PageBreak(),
              H1("1  Was ist der Testdata Generator?", st), HR(),
              P("Der <b>Testdata Generator</b> erzeugt synthetische Jira-Issue-Daten im "
                "Jira-REST-API-Format. Die generierten Dateien sind direkt mit dem Modul "
                "<b>transform_data</b> verarbeitbar — ohne eine echte Jira-Instanz.", st),
              P("Der Generator simuliert realistische Workflow-Historien: Issues durchlaufen "
                "die definierten Stages, verbleiben unterschiedlich lange in jeder Stage, "
                "werden gelegentlich zurückgestuft und schließen mit konfigurierbarer "
                "Rate ab.", st),
              SP(6),
              box("<b>Typische Einsatzgebiete:</b><br/>"
                  "- <b>Neue Installation testen:</b> Prüfen, ob transform_data und "
                  "build_reports korrekt arbeiten<br/>"
                  "- <b>Demos und Präsentationen:</b> Realistische Daten ohne "
                  "Datenschutzbedenken<br/>"
                  "- <b>Schulungen:</b> Lernumgebung mit bekannten, kontrollierten Daten<br/>"
                  "- <b>Entwicklung:</b> Reproduzierbare Testdaten über den Seed-Parameter",
                  st),
              SP(8),
              P("Der Testdata Generator ergänzt das Modul <b>Get Data</b> (noch in "
                "Entwicklung), das echte Daten direkt aus Jira lädt. Für Produktiv-"
                "umgebungen mit echten Jira-Daten siehe Kapitel 6.", st)]

    # ---- 2. Voraussetzungen und Start ----
    story += [PageBreak(),
              H1("2  Voraussetzungen und Start", st), HR(),
              H2("2.1  Portables Paket (empfohlen)", st),
              P("Das portable Paket enthält Python bereits eingebettet — keine separate "
                "Installation erforderlich.", st),
              tbl(["Betriebssystem", "Startdatei"],
                  [["Windows",  "TestdataGenerator.bat  (Doppelklick)"],
                   ["macOS",    "TestdataGenerator.command  (Rechtsklick → Öffnen)"],
                   ["Linux",    "./TestdataGenerator.sh"]],
                  col_widths=[4 * cm, 11.5 * cm]),
              SP(6),
              HI("Hinweis für Windows: Falls beim Start eine Fehlermeldung erscheint, "
                 "die Python nicht findet — die ZIP-Datei war möglicherweise durch "
                 "Windows blockiert. Lösung: Rechtsklick auf die ZIP → Eigenschaften → "
                 "Sicherheit → Zulassen → OK → erneut entpacken.", st),
              SP(6),
              H2("2.2  Aus dem Quellcode (Python erforderlich)", st),
              CD("python -m testdata_generator", st),
              SP(6),
              H2("2.3  Die Benutzeroberfläche", st),
              P("Nach dem Start öffnet sich das Hauptfenster mit Eingabefeldern für alle "
                "Parameter. Pflichtfeld ist nur die Workflow-Datei — alle anderen Felder "
                "haben sinnvolle Standardwerte.", st)]
    story += img("Testdata-Generator-GUI.png", 13.0,
                 "Abb. 1: Benutzeroberfläche des Testdata Generators", st)

    # ---- 3. Die Workflow-Datei ----
    story += [PageBreak(),
              H1("3  Die Workflow-Datei", st), HR(),
              P("Die Workflow-Datei definiert die Stages Ihres Jira-Boards und ist das "
                "einzige Pflichtfeld des Generators. Sie hat dasselbe Format wie in "
                "transform_data — eine Datei genügt für beide Module.", st),
              H2("3.1  Format", st),
              P("Jede Zeile beschreibt eine Stage. Aliases (alternative Status-Namen im "
                "Jira-Export) werden durch Doppelpunkte abgetrennt. Zwei Sonderzeilen "
                "markieren Anfang und Ende der aktiven Bearbeitung:", st),
              PRE("KanonischerName:Alias1:Alias2\n"
                  "<First>ErsteAktiveStage\n"
                  "<Closed>AbgeschlosseneStage", st),
              tbl(["Zeile", "Bedeutung"],
                  [["KanonischerName:Alias1:Alias2",
                    "Stage mit einem oder mehreren alternativen Jira-Status-Namen"],
                   ["StageName (ohne :)", "Stage ohne Aliases"],
                   ["<First>StageName",
                    "Erste aktive Stage — wo Bearbeitung beginnt (Cycle-Time-Start)"],
                   ["<Closed>StageName",
                    "Abgeschlossene Stage — markiert ein Issue als fertig"]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(8),
              H2("3.2  ART_A Beispiel-Workflow", st),
              P("Das mitgelieferte Beispiel "
                "<font name='Courier'>workflow_ART_A.txt</font> "
                "bildet einen typischen SAFe-ART-Workflow ab:", st),
              PRE("Funnel:New:Open:To Do\n"
                  "Analysis:In Analysis:Estimated\n"
                  "Program Backlog:Ready for Dev:Backlog\n"
                  "Implementation:In Implementation:In Review:In Progress\n"
                  "Blocker\n"
                  "Validating on Staging:QA\n"
                  "Deploying to Production:Ready for Development\n"
                  "Releasing:Completed\n"
                  "Done:Canceled\n"
                  "<First>Analysis\n"
                  "<Closed>Releasing", st),
              SP(4),
              HI("Anmerkungen: 'Funnel' enthält vier Aliases — alle vier Jira-Status-Namen "
                 "werden auf 'Funnel' normiert. Analysis ist die erste aktive Stage "
                 "(Cycle-Time beginnt hier). Releasing gilt als abgeschlossen. Done (nach "
                 "Releasing) nimmt auch Canceled-Issues auf.", st)]

    # ---- 4. Parameter-Referenz ----
    story += [PageBreak(),
              H1("4  Parameter-Referenz", st), HR(),
              P("Alle Parameter sind sowohl in der GUI als auch auf der Kommandozeile "
                "verfügbar.", st),
              tbl(["Parameter", "Standard", "Beschreibung"],
                  [["--workflow FILE",         "(Pflicht)",
                    "Workflow-Definitionsdatei (.txt)"],
                   ["--output FILE.json",       "<project>_generated.json",
                    "Pfad der Ausgabedatei"],
                   ["--project KEY",            "TEST",
                    "Jira-Projekt-Key der generierten Issues"],
                   ["--issues N",               "100",
                    "Anzahl zu generierender Issues"],
                   ["--from-date YYYY-MM-DD",   "2025-01-01",
                    "Frühestes Erstellungsdatum"],
                   ["--to-date YYYY-MM-DD",     "2025-12-31",
                    "Spätestes Übergangsdatum"],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1",
                    "Issue-Typen mit Gewichtung (Summe muss nicht 1 ergeben)"],
                   ["--completion-rate FLOAT",  "0.7",
                    "Anteil Issues, die die Closed-Stage erreichen (0–1)"],
                   ["--todo-rate FLOAT",         "0.15",
                    "Anteil offener Issues, die in frühen Stages verbleiben (0–1)"],
                   ["--backflow-prob FLOAT",     "0.1",
                    "Wahrscheinlichkeit eines Rückschritts bei jedem Übergang (0–1)"],
                   ["--seed INT",               "(zufällig)",
                    "Seed für reproduzierbare Ausgabe (optional)"]],
                  col_widths=[4.5 * cm, 4 * cm, 7 * cm]),
              SP(8),
              box("<b>Tipp: Reproduzierbare Ergebnisse</b><br/>"
                  "Mit einem festen Seed (z. B. <font name='Courier'>--seed 42</font>) "
                  "erzeugt der Generator bei gleichen Parametern immer dieselbe "
                  "JSON-Datei — ideal für Demos, bei denen alle Teilnehmer "
                  "dieselben Ergebnisse sehen sollen.", st)]

    # ---- 5. ART_A – Vollständiges Beispiel ----
    story += [PageBreak(),
              H1("5  ART_A – Vollständiges Beispiel", st), HR(),
              P("Dieses Beispiel zeigt den vollständigen Ablauf vom Generator bis zum "
                "fertigen Report am fiktiven Projekt ART_A.", st),
              H2("Schritt 1: Testdaten generieren", st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A \\\n"
                  "    --issues 200 \\\n"
                  "    --from-date 2025-01-01 \\\n"
                  "    --to-date 2025-12-31 \\\n"
                  "    --issue-types Feature:0.6 Bug:0.2 Enabler:0.2 \\\n"
                  "    --completion-rate 0.75 \\\n"
                  "    --backflow-prob 0.08 \\\n"
                  "    --seed 42 \\\n"
                  "    --output ART_A_generated.json", st),
              P("Ergebnis: <font name='Courier'>ART_A_generated.json</font> mit 200 "
                "Issues, ca. 150 abgeschlossen und 50 in verschiedenen Stages offen. "
                "Dank Seed 42 ist die Ausgabe jederzeit reproduzierbar.", st),
              H2("Schritt 2: Mit transform_data verarbeiten", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              P("Erzeugt drei Excel-Dateien: "
                "<font name='Courier'>ART_A_generated_IssueTimes.xlsx</font>, "
                "<font name='Courier'>ART_A_generated_CFD.xlsx</font> und "
                "<font name='Courier'>ART_A_generated_Transitions.xlsx</font>.", st),
              H2("Schritt 3: Report mit build_reports erstellen", st),
              PRE("python -m build_reports", st),
              P("In build_reports die drei Excel-Dateien aus Schritt 2 laden — "
                "das Programm erstellt daraus Flow-Diagramme, Cycle-Time-Analysen "
                "und Metriken.", st),
              SP(6),
              box("<b>Was zu erwarten ist (Seed 42, 200 Issues):</b><br/>"
                  "- Issue-Keys: ART_A-0001 bis ART_A-0200<br/>"
                  "- Issue-Typen: ~120 Feature, ~40 Bug, ~40 Enabler<br/>"
                  "- Ca. 150 Issues im Status 'Releasing' oder 'Done'<br/>"
                  "- Erstellungsdaten verteilt über das Jahr 2025<br/>"
                  "- Gelegentliche Rückschritte (backflow-prob 0.08 = ca. 8 %)", st)]

    # ---- 6. Echte Daten aus Jira Cloud exportieren ----
    story += [PageBreak(),
              H1("6  Echte Daten aus Jira Cloud exportieren", st), HR(),
              P("Dieses Kapitel erklärt, wie Sie echte Issue-Daten aus Jira Cloud für "
                "SituationReport exportieren. Der Export liefert dieselbe JSON-Struktur "
                "wie der Testdata Generator — transform_data verarbeitet beide "
                "identisch.", st),

              H2("6.1  Was Sie benötigen", st),
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

              H2("6.2  API-Token erstellen", st),
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

              H2("6.3  Die Jira REST API abfragen", st),
              P("Die Jira REST API v2 liefert Issues im JSON-Format. Der Parameter "
                "<font name='Courier'>expand=changelog</font> ist <b>Pflicht</b> — "
                "ohne ihn fehlen die Statusübergänge, die transform_data benötigt.", st),
              PRE("curl -u \"name@firma.de:IhrAPIToken\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              P("Ersetzen Sie <font name='Courier'>firma</font> durch Ihre "
                "Atlassian-Subdomain und <font name='Courier'>ART_A</font> durch Ihren "
                "Projekt-Key.", st),
              H3("Browser-Methode (ohne curl)", st),
              P("Wer curl nicht installiert hat, kann die URL direkt im Browser aufrufen "
                "— der Browser nutzt die bestehende Jira-Session:", st),
              PRE("https://firma.atlassian.net/rest/api/2/search\n"
                  "  ?jql=project=ART_A&expand=changelog&maxResults=1000", st),
              P("Der Browser zeigt die JSON-Antwort als Text. "
                "<b>Strg+S</b> → Dateityp 'Alle Dateien' → Als "
                "<font name='Courier'>ART_A_page1.json</font> speichern.", st),
              SP(6),

              H2("6.4  Welche Felder transform_data benötigt", st),
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

              H2("6.5  Paginierung – mehr als 1.000 Issues", st),
              P("Jira liefert maximal 1.000 Issues pro Anfrage. Bei größeren Projekten "
                "mehrere Seiten abrufen und anschließend mit dem Helper zusammenführen:", st),
              PRE("# Seite 1 (Issues 1-1000)\n"
                  "curl -u \"name@firma.de:Token\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?jql=project=ART_A\\\n"
                  "&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Seite 2 (Issues 1001-2000)\n"
                  "curl -u \"name@firma.de:Token\" \\\n"
                  "  \"https://firma.atlassian.net/rest/api/2/search?jql=project=ART_A\\\n"
                  "&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Dateien mit dem Helper zusammenfuehren\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Erhöhen Sie <font name='Courier'>startAt</font> schrittweise um 1.000, "
                "bis das Ergebnis weniger als 1.000 Issues enthält — dann haben Sie alle "
                "Seiten erfasst. Der <b>Helper</b> führt die Seiten zusammen und entfernt "
                "Duplikate automatisch.", st),
              SP(6),

              H2("6.6  Vom JSON-Export zur Workflow-Datei", st),
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
                "<font name='Courier'>&lt;Closed&gt;</font> "
                "(Kapitel 3).", st)]

    # ---- 7. FAQ ----
    story += [PageBreak(),
              H1("7  Häufige Fragen (FAQ)", st), HR(),

              H2("Was passiert, wenn expand=changelog fehlt?", st),
              P("transform_data findet keine Statusübergänge und gibt für alle Issues "
                "leere Zeitwerte aus. Die Excel-Ausgaben enthalten keine nutzbaren "
                "Daten. Stellen Sie sicher, dass "
                "<font name='Courier'>expand=changelog</font> immer in der URL steht.", st),

              H2("Unterschied zwischen Testdaten und echten Daten?", st),
              P("Für Demos und Schulungen sind Testdaten die bessere Wahl — keine "
                "Datenschutzbedenken, reproduzierbar und kontrolliert. "
                "Für echte Analysen spiegeln echte Daten den tatsächlichen "
                "Workflow-Zustand wider und liefern verlässliche Flow-Metriken.", st),

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

              H2("Ich erhalte den Fehler 'Unauthorized' beim curl-Aufruf.", st),
              P("Prüfen Sie: E-Mail-Adresse und API-Token korrekt? Sind sie durch "
                "einen Doppelpunkt getrennt? Hat Ihr Konto Lesezugriff auf das Projekt? "
                "Tipp: Einen neuen API-Token generieren, falls der alte abgelaufen ist "
                "oder verloren wurde.", st)]

    # ---- 8. Glossar ----
    story += [PageBreak(),
              H1("8  Glossar", st), HR(),
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
                   ["Seed",      "Startwert für den Zufallsgenerator — gleicher Seed ergibt "
                                 "immer dieselbe Ausgabe"],
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

    # ---- 1. What is the Testdata Generator? ----
    story += [PageBreak(),
              H1("1  What is the Testdata Generator?", st), HR(),
              P("The <b>Testdata Generator</b> creates synthetic Jira issue data in "
                "Jira REST API format. The generated files can be processed directly by "
                "<b>transform_data</b> — no real Jira instance required.", st),
              P("The generator simulates realistic workflow histories: issues traverse "
                "the defined stages, spend varying amounts of time in each stage, "
                "occasionally flow backwards, and close at a configurable rate.", st),
              SP(6),
              box("<b>Typical use cases:</b><br/>"
                  "- <b>Test a new installation:</b> Verify that transform_data and "
                  "build_reports work correctly<br/>"
                  "- <b>Demos and presentations:</b> Realistic data without privacy concerns<br/>"
                  "- <b>Training:</b> Controlled learning environment with known data<br/>"
                  "- <b>Development:</b> Reproducible test data via the seed parameter",
                  st),
              SP(8),
              P("The Testdata Generator complements the <b>Get Data</b> module (still "
                "in development), which loads real data directly from Jira. For "
                "production environments with real Jira data, see Chapter 6.", st)]

    # ---- 2. Prerequisites and Start ----
    story += [PageBreak(),
              H1("2  Prerequisites and Start", st), HR(),
              H2("2.1  Portable package (recommended)", st),
              P("The portable package includes Python already bundled — no separate "
                "installation required.", st),
              tbl(["Operating system", "Start file"],
                  [["Windows",  "TestdataGenerator.bat  (double-click)"],
                   ["macOS",    "TestdataGenerator.command  (right-click → Open)"],
                   ["Linux",    "./TestdataGenerator.sh"]],
                  col_widths=[4 * cm, 11.5 * cm]),
              SP(6),
              HI("Note for Windows: If double-clicking shows an error about Python not "
                 "being found, the ZIP file may have been blocked by Windows. Fix: "
                 "right-click the ZIP → Properties → Security → Unblock → OK → "
                 "extract again.", st),
              SP(6),
              H2("2.2  From source code (Python required)", st),
              CD("python -m testdata_generator", st),
              SP(6),
              H2("2.3  The user interface", st),
              P("After launch, the main window shows input fields for all parameters. "
                "Only the workflow file is required — all other fields have sensible "
                "defaults.", st)]
    story += img("Testdata-Generator-GUI.png", 13.0,
                 "Fig. 1: Testdata Generator user interface", st)

    # ---- 3. The Workflow File ----
    story += [PageBreak(),
              H1("3  The Workflow File", st), HR(),
              P("The workflow file defines the stages of your Jira board and is the only "
                "required parameter. It uses the same format as transform_data — one "
                "file works for both modules.", st),
              H2("3.1  Format", st),
              P("Each line describes a stage. Aliases (alternative status names in the "
                "Jira export) are separated by colons. Two special lines mark the "
                "start and end of active work:", st),
              PRE("CanonicalName:Alias1:Alias2\n"
                  "<First>FirstActiveStage\n"
                  "<Closed>ClosedStage", st),
              tbl(["Line", "Meaning"],
                  [["CanonicalName:Alias1:Alias2",
                    "Stage with one or more alternative Jira status names"],
                   ["StageName (no :)", "Stage without aliases"],
                   ["<First>StageName",
                    "First active stage — where processing begins (cycle time starts here)"],
                   ["<Closed>StageName",
                    "Closed stage — marks an issue as completed"]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(8),
              H2("3.2  ART_A example workflow", st),
              P("The bundled example "
                "<font name='Courier'>workflow_ART_A.txt</font> "
                "models a typical SAFe ART workflow:", st),
              PRE("Funnel:New:Open:To Do\n"
                  "Analysis:In Analysis:Estimated\n"
                  "Program Backlog:Ready for Dev:Backlog\n"
                  "Implementation:In Implementation:In Review:In Progress\n"
                  "Blocker\n"
                  "Validating on Staging:QA\n"
                  "Deploying to Production:Ready for Development\n"
                  "Releasing:Completed\n"
                  "Done:Canceled\n"
                  "<First>Analysis\n"
                  "<Closed>Releasing", st),
              SP(4),
              HI("Notes: 'Funnel' has four aliases — all four Jira status names are "
                 "normalised to 'Funnel'. Analysis is the first active stage (cycle "
                 "time begins here). Releasing is the closed stage. Done (after "
                 "Releasing) also captures Canceled issues.", st)]

    # ---- 4. Parameter Reference ----
    story += [PageBreak(),
              H1("4  Parameter Reference", st), HR(),
              P("All parameters are available both in the GUI and on the command line.", st),
              tbl(["Parameter", "Default", "Description"],
                  [["--workflow FILE",         "(required)",
                    "Workflow definition file (.txt)"],
                   ["--output FILE.json",       "<project>_generated.json",
                    "Output file path"],
                   ["--project KEY",            "TEST",
                    "Jira project key for generated issues"],
                   ["--issues N",               "100",
                    "Number of issues to generate"],
                   ["--from-date YYYY-MM-DD",   "2025-01-01",
                    "Earliest creation date"],
                   ["--to-date YYYY-MM-DD",     "2025-12-31",
                    "Latest transition date"],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1",
                    "Issue types with weights (sum need not equal 1)"],
                   ["--completion-rate FLOAT",  "0.7",
                    "Fraction of issues reaching the closed stage (0–1)"],
                   ["--todo-rate FLOAT",         "0.15",
                    "Fraction of open issues staying in early stages (0–1)"],
                   ["--backflow-prob FLOAT",     "0.1",
                    "Probability of a backward transition at each step (0–1)"],
                   ["--seed INT",               "(random)",
                    "Seed for reproducible output (optional)"]],
                  col_widths=[4.5 * cm, 4 * cm, 7 * cm]),
              SP(8),
              box("<b>Tip: Reproducible results</b><br/>"
                  "With a fixed seed (e.g. <font name='Courier'>--seed 42</font>), the "
                  "generator always produces the same JSON file for the same parameters "
                  "— ideal for demos where all participants should see identical results.",
                  st)]

    # ---- 5. ART_A – Complete Example ----
    story += [PageBreak(),
              H1("5  ART_A – Complete Example", st), HR(),
              P("This example shows the full pipeline from generator to finished report "
                "using the fictional ART_A project.", st),
              H2("Step 1: Generate test data", st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A \\\n"
                  "    --issues 200 \\\n"
                  "    --from-date 2025-01-01 \\\n"
                  "    --to-date 2025-12-31 \\\n"
                  "    --issue-types Feature:0.6 Bug:0.2 Enabler:0.2 \\\n"
                  "    --completion-rate 0.75 \\\n"
                  "    --backflow-prob 0.08 \\\n"
                  "    --seed 42 \\\n"
                  "    --output ART_A_generated.json", st),
              P("Result: <font name='Courier'>ART_A_generated.json</font> with 200 "
                "issues — approximately 150 closed and 50 open across various stages. "
                "Seed 42 makes the output reproducible at any time.", st),
              H2("Step 2: Process with transform_data", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              P("Produces three Excel files: "
                "<font name='Courier'>ART_A_generated_IssueTimes.xlsx</font>, "
                "<font name='Courier'>ART_A_generated_CFD.xlsx</font>, and "
                "<font name='Courier'>ART_A_generated_Transitions.xlsx</font>.", st),
              H2("Step 3: Create report with build_reports", st),
              PRE("python -m build_reports", st),
              P("Load the three Excel files from Step 2 in build_reports — the "
                "module generates flow diagrams, cycle time analyses, and metrics.", st),
              SP(6),
              box("<b>Expected output (seed 42, 200 issues):</b><br/>"
                  "- Issue keys: ART_A-0001 to ART_A-0200<br/>"
                  "- Issue types: ~120 Feature, ~40 Bug, ~40 Enabler<br/>"
                  "- ~150 issues with status 'Releasing' or 'Done'<br/>"
                  "- Creation dates distributed across 2025<br/>"
                  "- Occasional backward transitions (backflow-prob 0.08 = ~8 %)", st)]

    # ---- 6. Exporting Real Data from Jira Cloud ----
    story += [PageBreak(),
              H1("6  Exporting Real Data from Jira Cloud", st), HR(),
              P("This chapter explains how to export real issue data from Jira Cloud for "
                "SituationReport. The export produces the same JSON structure as the "
                "Testdata Generator — transform_data processes both identically.", st),

              H2("6.1  What you need", st),
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

              H2("6.2  Creating an API token", st),
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

              H2("6.3  Querying the Jira REST API", st),
              P("The Jira REST API v2 returns issues as JSON. The parameter "
                "<font name='Courier'>expand=changelog</font> is <b>required</b> — "
                "without it, status transitions are missing and transform_data "
                "cannot compute time-in-stage values.", st),
              PRE("curl -u \"name@company.com:YourAPIToken\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?\\\n"
                  "jql=project=ART_A+ORDER+BY+created+ASC\\\n"
                  "&expand=changelog\\\n"
                  "&maxResults=1000\\\n"
                  "&fields=issuetype,created,status,project,summary,resolution\" \\\n"
                  "  -o ART_A_page1.json", st),
              P("Replace <font name='Courier'>company</font> with your Atlassian "
                "subdomain and <font name='Courier'>ART_A</font> with your project key.", st),
              H3("Browser method (without curl)", st),
              P("If curl is not installed, open the URL directly in your browser — "
                "it uses the existing Jira session:", st),
              PRE("https://company.atlassian.net/rest/api/2/search\n"
                  "  ?jql=project=ART_A&expand=changelog&maxResults=1000", st),
              P("The browser displays the JSON response as text. "
                "<b>Ctrl+S</b> → file type 'All files' → save as "
                "<font name='Courier'>ART_A_page1.json</font>.", st),
              SP(6),

              H2("6.4  Fields required by transform_data", st),
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

              H2("6.5  Pagination – more than 1,000 issues", st),
              P("Jira returns at most 1,000 issues per request. For larger projects, "
                "fetch multiple pages and then merge them with the Helper:", st),
              PRE("# Page 1 (issues 1-1000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?jql=project=ART_A\\\n"
                  "&expand=changelog&maxResults=1000&startAt=0\" \\\n"
                  "  -o ART_A_page1.json\n\n"
                  "# Page 2 (issues 1001-2000)\n"
                  "curl -u \"name@company.com:Token\" \\\n"
                  "  \"https://company.atlassian.net/rest/api/2/search?jql=project=ART_A\\\n"
                  "&expand=changelog&maxResults=1000&startAt=1000\" \\\n"
                  "  -o ART_A_page2.json\n\n"
                  "# Merge files with the Helper\n"
                  "python -m helper ART_A_page1.json ART_A_page2.json \\\n"
                  "  --output ART_A_merged.json", st),
              P("Increment <font name='Courier'>startAt</font> by 1,000 until the "
                "response contains fewer than 1,000 issues — then you have fetched all "
                "pages. The <b>Helper</b> merges the pages and removes duplicates "
                "automatically.", st),
              SP(6),

              H2("6.6  From JSON export to workflow file", st),
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
                "<font name='Courier'>&lt;Closed&gt;</font> markers "
                "(see Chapter 3).", st)]

    # ---- 7. FAQ ----
    story += [PageBreak(),
              H1("7  Frequently Asked Questions (FAQ)", st), HR(),

              H2("What happens if expand=changelog is missing?", st),
              P("transform_data finds no status transitions and outputs empty time values "
                "for all issues. The Excel files contain no usable data. Always include "
                "<font name='Courier'>expand=changelog</font> in the URL.", st),

              H2("Difference between test data and real data?", st),
              P("For demos and training, test data is the better choice — no privacy "
                "concerns, reproducible, and fully controlled. For real analyses, actual "
                "data reflects the true workflow state and delivers reliable flow metrics.", st),

              H2("Can I merge multiple Jira projects?", st),
              P("Yes — either via JQL "
                "(<font name='Courier'>jql=project in (ART_A, ART_B)</font>) for a "
                "single export, or merge two separate exports with the Helper. Make sure "
                "the workflows of both projects are compatible.", st),

              H2("How large can the JSON file get?", st),
              P("Rule of thumb: approximately 2–5 KB per issue (depending on changelog "
                "length). 1,000 issues ≈ 2–5 MB. For very large projects (10,000+ "
                "issues), use pagination and the Helper.", st),

              H2("I get an 'Unauthorized' error when calling curl.", st),
              P("Check: Is the email address correct? Is the API token correct? Are they "
                "separated by a colon? Does your account have read access to the project? "
                "Tip: Generate a new API token if the old one was lost or expired.", st)]

    # ---- 8. Glossary ----
    story += [PageBreak(),
              H1("8  Glossary", st), HR(),
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
                   ["Seed",      "Starting value for the random generator — same seed always "
                                 "produces the same output"],
                   ["Stage",     "One step in the workflow (corresponds to a Jira column or "
                                 "status name)"],
                   ["Workflow",  "Ordered sequence of stages that an issue passes through"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate testdata_generator manuals as PDF in German and English."""
    st = make_styles()

    for lang, output, content_fn in [
        ("de", OUTPUT_DE, content_de),
        ("en", OUTPUT_EN, content_en),
    ]:
        story = [NextPageTemplate("normal")]
        story += content_fn(st)
        doc = _TDGDoc(str(output), lang=lang)
        doc.multiBuild(story)
        print(f"PDF created: {output}")


if __name__ == "__main__":
    main()
