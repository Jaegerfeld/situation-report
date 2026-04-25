# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       21.04.2026
# Geaendert:      25.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer transform_data als PDF-Datei.
#   Produziert beide Sprachversionen: Deutsch (transform_data_Benutzerhandbuch.pdf)
#   und Englisch (transform_data_UserManual.pdf).
#   Kapitel: Einleitung, Eingabedateien, Workflow-Definition, GUI-Bedienung,
#   Ausgabedateien, Datumsberechnung, FAQ und Glossar.
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
    BaseDocTemplate, Frame, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

OUTPUT_DE = Path(__file__).parent / "transform_data_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "transform_data_UserManual.pdf"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("H1", fontName="Helvetica-Bold", fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8, keepWithNext=1),
        h2=s("H2", fontName="Helvetica-Bold", fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5, keepWithNext=1),
        h3=s("H3", fontName="Helvetica-BoldOblique", fontSize=11, textColor=C_BLUE,
              spaceBefore=10, spaceAfter=4, keepWithNext=1),
        body=s("Body", fontName="Helvetica", fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("Bullet", fontName="Helvetica", fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3, bulletIndent=4),
        hint=s("Hint", fontName="Helvetica-Oblique", fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        code=s("Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        caption=s("Caption", fontName="Helvetica-Oblique", fontSize=8,
                  textColor=C_HINT, leading=11, alignment=TA_CENTER, spaceAfter=8),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

def _make_header_text(lang: str) -> str:
    return "transform_data -- Benutzerhandbuch" if lang == "de" else "transform_data -- User Manual"


class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, lang="de", **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=lambda c, d, lang=lang: build_cover(c, d, lang)),
            PageTemplate(id="normal",
                         frames=[Frame(margin, margin,
                                       w - 2*margin, h - 2*margin - 1.2*cm,
                                       id="normal", showBoundary=0)],
                         onPage=self._header_footer),
        ])

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, h - 1.1*cm, w, 1.1*cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2*cm, h - 0.7*cm, _make_header_text(self._lang))
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont("Helvetica", 8)
        page_label = "Seite %d" if self._lang == "de" else "Page %d"
        canvas.drawCentredString(w/2, 1.0*cm, page_label % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2*cm, 1.4*cm, w - 2.2*cm, 1.4*cm)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if hasattr(flowable, "toc_level"):
            self.notify("TOCEntry",
                        (flowable.toc_level, flowable.getPlainText(), self.page))


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def build_cover(canvas, doc, lang="de"):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 32)
    canvas.drawCentredString(w/2, h*0.60, "transform_data")
    canvas.setFont("Helvetica-Bold", 18)
    title2 = "Benutzerhandbuch" if lang == "de" else "User Manual"
    canvas.drawCentredString(w/2, h*0.545, title2)
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(C_LIGHT)
    subtitle = ("Jira-Daten aufbereiten fuer Metriken und Berichte"
                if lang == "de"
                else "Prepare Jira data for metrics and reports")
    canvas.drawCentredString(w/2, h*0.49, subtitle)
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.455, w*0.8, h*0.455)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report - github.com/Jaegerfeld/situation-report")
    audience = ("Fuer nicht-technische Anwender" if lang == "de"
                else "For non-technical users")
    canvas.drawCentredString(w/2, h*0.09, f"{audience} — Version {_VERSION}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Helper flowables
# ---------------------------------------------------------------------------

class TocHeading(Paragraph):
    def __init__(self, text, style, level):
        super().__init__(text, style)
        self.toc_level = level


def H1(text, st): return TocHeading(text, st["h1"], 0)
def H2(text, st): return TocHeading(text, st["h2"], 1)
def H3(text, st): return TocHeading(text, st["h3"], 2)
def P(text, st):  return Paragraph(text, st["body"])
def BL(text, st): return Paragraph("- " + text, st["bullet"])
def HI(text, st): return Paragraph(text, st["hint"])
def CD(text, st): return Paragraph(text, st["code"])
def SP(n=6):      return Spacer(1, n)


def box(text, st, bg="#eaf4fb"):
    t = Table([[Paragraph(text, st["body"])]], colWidths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor(bg)),
        ("BOX",           (0,0), (-1,-1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t


def tbl(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_MID),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Content — German
# ---------------------------------------------------------------------------

def content_de(st):
    """Build German document story."""
    story = []

    story.append(PageBreak())
    story.append(H1("Inhalt", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # 1
    story.append(PageBreak())
    story.append(H1("1  Was ist transform_data?", st))
    story.append(P(
        "transform_data ist das erste Modul in der situation-report-Werkzeugkette. "
        "Es liest einen Rohdaten-Export aus Ihrem Ticketsystem (Jira) und bereitet "
        "die Daten fuer die weitere Analyse auf. Das Ergebnis sind drei "
        "<b>Excel-Dateien</b>, die zeigen, wie lange Issues in welchen Workflow-Schritten "
        "verbracht haben und wie sich der Bestand ueber die Zeit entwickelt hat.", st))
    story.append(P(
        "Das Programm besitzt eine einfache grafische Oberflaeche (GUI): "
        "keine Programmierkenntnisse erforderlich. Sie waehlen zwei Dateien aus, "
        "klicken auf 'Ausfuehren' und erhalten die Excel-Dateien automatisch.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Was transform_data liefert:</b><br/>"
        "- <b>IssueTimes.xlsx</b>: Alle Issues mit Meilensteinzeitpunkten und Minuten "
        "pro Workflow-Stage.<br/>"
        "- <b>Transitions.xlsx</b>: Vollstaendige Statushistorie aller Issues.<br/>"
        "- <b>CFD.xlsx</b>: Taeglich Eintrittszaehlungen je Stage fuer das Cumulative Flow Diagram.", st))
    story.append(SP(8))
    story.append(P(
        "Die erzeugten Excel-Dateien werden anschliessend vom Modul <b>build_reports</b> "
        "verwendet, um Diagramme und Berichte zu erstellen.", st))

    # 2
    story.append(PageBreak())
    story.append(H1("2  Voraussetzungen und Installation", st))
    story.append(H2("2.1  Was muss installiert sein?", st))
    story.append(P(
        "Damit transform_data funktioniert, muss auf dem Rechner <b>Python 3.11 oder "
        "neuer</b> installiert sein. Ausserdem muessen einige Python-Pakete vorhanden "
        "sein. Wer das Programm fuer Sie eingerichtet hat, sollte dies bereits erledigt "
        "haben.", st))
    story.append(H2("2.2  Programm starten", st))
    story.append(P("Es gibt zwei Moeglichkeiten, transform_data zu starten:", st))
    story.append(BL(
        "<b>Doppelklick</b> auf die Datei <b>transform_data_gui.pyw</b> im Projektordner "
        "-- oeffnet die grafische Oberflaeche ohne ein Konsolenfenster.", st))
    story.append(BL(
        "<b>Terminal / Eingabeaufforderung</b>: Ins Projektverzeichnis wechseln und "
        "<font name='Courier'>python -m transform_data</font> eingeben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wer die GUI regelmaessig nutzt, kann eine Verknuepfung zur Datei "
        "<b>transform_data_gui.pyw</b> auf dem Desktop erstellen.", st, "#e8f8f0"))

    # 3
    story.append(PageBreak())
    story.append(H1("3  Eingabedateien", st))
    story.append(P(
        "transform_data benoetigt genau zwei Dateien: den Jira-JSON-Export und die "
        "Workflow-Definitionsdatei. Beide werden in der GUI per Datei-Dialog ausgewaehlt.", st))
    story.append(H2("3.1  Jira-JSON-Export", st))
    story.append(P(
        "Dies ist ein Export aller Issues eines Jira-Projekts im JSON-Format. "
        "Er enthaelt fuer jedes Ticket die komplette Statushistorie (Changelog), "
        "Metadaten wie Issuetyp, Komponenten und Erstellungsdatum sowie den aktuellen "
        "Status.", st))
    story.append(P(
        "Wie der Export aus Jira erzeugt wird, beschreibt das Modul <b>get_data</b>. "
        "Die JSON-Datei sollte nicht manuell bearbeitet werden.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typischer Dateiname:</b> ART_A.json, MYPROJECT.json o.ae.<br/>"
        "<b>Groesse:</b> Abhaengig von der Anzahl der Issues; haeufig einige MB.", st,
        "#fff8e1"))
    story.append(H2("3.2  Workflow-Definitionsdatei", st))
    story.append(P(
        "Die Workflow-Datei ist eine einfache Textdatei (.txt), die beschreibt, "
        "wie die Jira-Status Ihres Projekts auf logische Prozessschritte (Stages) "
        "abgebildet werden. Sie definiert ausserdem, welche Stage den Beginn der "
        "Entwicklung (First Date) und den Abschluss (Closed Date) markiert.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typischer Dateiname:</b> workflow_ART_A.txt o.ae.<br/>"
        "<b>Erstellt von:</b> Ihrem technischen Ansprechpartner oder Scrum Master -- "
        "einmalig pro Projekt, selten geaendert.", st, "#e8f8f0"))

    # 4
    story.append(PageBreak())
    story.append(H1("4  Die Workflow-Definitionsdatei", st))
    story.append(P(
        "Die Workflow-Datei steuert, wie transform_data die Jira-Status Ihres Projekts "
        "interpretiert. Sie muessen diese Datei in der Regel nicht selbst erstellen -- "
        "dieses Kapitel erklaert jedoch ihren Aufbau, damit Sie sie lesen und bei Bedarf "
        "anpassen koennen.", st))
    story.append(H2("4.1  Aufbau", st))
    story.append(P(
        "Jede Zeile der Datei beschreibt entweder eine <b>Stage</b> (einen Prozessschritt) "
        "oder einen <b>Marker</b> (einen Meilenstein). Leerzeilen werden ignoriert.", st))
    story.append(SP(4))
    story.append(P("<b>Beispiel:</b>", st))
    story.append(CD(
        "Funnel:New:Open:To Do<br/>"
        "Analysis:In Analysis:Estimated<br/>"
        "Implementation:In Implementation:In Progress<br/>"
        "Done:Canceled<br/>"
        "&lt;First&gt;Analysis<br/>"
        "&lt;InProgress&gt;Implementation<br/>"
        "&lt;Closed&gt;Done", st))
    story.append(SP(6))
    story.append(tbl(
        ["Format", "Bedeutung"],
        [
            ["Stage:Alias1:Alias2",
             "Stage mit Jira-Statusnamen, die darauf gemappt werden. Der erste Name ist der "
             "kanonische Stage-Name."],
            ["<First>Stage",
             "Diese Stage markiert den Beginn der aktiven Bearbeitung (First Date)."],
            ["<InProgress>Stage",
             "Diese Stage setzt das Implementation Date."],
            ["<Closed>Stage",
             "Diese Stage markiert den Abschluss (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Reihenfolge der Stages", st))
    story.append(P(
        "Die Stages werden in der Reihenfolge aufgefuehrt, in der sie im Prozess "
        "durchlaufen werden. Diese Reihenfolge wird fuer das Cumulative Flow Diagram "
        "und fuer die Berechnung des Closed Date bei uebersprungenen Stages verwendet.", st))
    story.append(H2("4.3  Nicht gemappte Jira-Status", st))
    story.append(P(
        "Enthaelt der Jira-Export Status, die in der Workflow-Datei nicht definiert sind, "
        "gibt transform_data eine Warnung aus. Die Zeit wird der letzten bekannten Stage "
        "zugerechnet (Carry-forward).", st))

    # 5
    story.append(PageBreak())
    story.append(H1("5  Die grafische Oberflaeche (GUI)", st))
    story.append(P(
        "Nach dem Start oeffnet sich ein Fenster mit Datei-Auswahl-Feldern, "
        "Optionen und einem Log-Bereich fuer Statusmeldungen.", st))
    story.append(H2("5.1  Dateien auswaehlen", st))
    story.append(P("Laden Sie die beiden Eingabedateien:", st))
    story.append(BL(
        "<b>JSON-Datei</b> - Klicken Sie auf 'Durchsuchen' und waehlen Sie Ihren "
        "Jira-Export aus. Ausgabeordner und Praefix werden automatisch vorbelegt.", st))
    story.append(BL(
        "<b>Workflow-Datei</b> - Waehlen Sie die passende .txt-Workflow-Datei "
        "fuer Ihr Projekt aus.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wenn Sie die JSON-Datei zuerst auswaehlen, werden Ausgabeordner "
        "und Praefix automatisch vorausgefuellt.", st, "#e8f8f0"))
    story.append(H2("5.2  Ausgabe konfigurieren", st))
    story.append(SP(4))
    story.append(tbl(
        ["Feld", "Bedeutung"],
        [
            ["Ausgabeordner",
             "Verzeichnis, in das die drei Excel-Dateien gespeichert werden. "
             "Standard: Verzeichnis der JSON-Datei."],
            ["Praefix",
             "Namens-Praefix fuer die Ausgabedateien. Aus 'ART_A' werden z.B. "
             "ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx und ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Verarbeitung starten", st))
    story.append(P(
        "Klicken Sie auf <b>'Ausfuehren'</b>. Das Programm liest die Daten ein, "
        "berechnet alle Werte und speichert die drei Excel-Dateien. "
        "Der Fortschritt und eventuelle Warnungen erscheinen im Log-Bereich.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Warnungen im Log beachten:</b> Eine Warnung ueber nicht gemappte Status "
        "bedeutet nicht, dass die Verarbeitung fehlgeschlagen ist. "
        "Die Ausgabedateien werden trotzdem erstellt.", st, "#fff8e1"))
    story.append(H2("5.4  Sprache und Hilfe", st))
    story.append(P(
        "Im Menue <b>Optionen</b> koennen Sie zwischen Deutsch und Englisch wechseln. "
        "Alle Beschriftungen werden sofort aktualisiert. "
        "Unter <b>Hilfe &rarr; Manual</b> oeffnet sich dieses Handbuch "
        "in der jeweils aktiven Sprache im Browser.", st))

    # 6
    story.append(PageBreak())
    story.append(H1("6  Die Ausgabedateien", st))
    story.append(P(
        "transform_data erzeugt drei Excel-Dateien. Diese Dateien dienen als "
        "Eingabe fuer build_reports und sollten nicht manuell bearbeitet werden.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(P(
        "Die wichtigste Ausgabedatei. Sie enthaelt eine Zeile pro Issue mit allen "
        "Zeitangaben.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Project",            "Projektschluessel (z.B. ART_A)"],
            ["Key",                "Issue-Schluessel (z.B. ART_A-123)"],
            ["Issuetype",          "Typ des Issues (z.B. Feature, Bug, Story)"],
            ["Status",             "Aktueller Jira-Status"],
            ["Created Date",       "Erstellungsdatum des Issues in Jira"],
            ["First Date",         "Erster Eintritt in die <First>-Stage"],
            ["Implementation Date","Erster Eintritt in die <InProgress>-Stage"],
            ["Closed Date",        "Zeitpunkt des Abschlusses (leer = noch offen)"],
            ["Stage-Spalten",      "Je eine Spalte pro Stage: Minuten in dieser Stage"],
            ["Resolution",         "Abschlussart aus Jira"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(H2("6.2  Transitions.xlsx", st))
    story.append(P(
        "Enthaelt die vollstaendige Statushistorie aller Issues -- einen Eintrag pro "
        "Statuswechsel. Nuetzlich fuer detaillierte Analysen einzelner Issues.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Key",        "Issue-Schluessel"],
            ["Transition", "Stage-Name (oder 'Created' fuer den Erstellungszeitpunkt)"],
            ["Timestamp",  "Datum und Uhrzeit des Statuswechsels"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("6.3  CFD.xlsx", st))
    story.append(P(
        "Enthaelt fuer jeden Kalendertag die Anzahl der Issues, die an diesem Tag in "
        "die jeweilige Stage eingetreten sind. build_reports akkumuliert diese Werte "
        "kumulativ und erzeugt daraus das Cumulative Flow Diagram.", st))

    # 7
    story.append(PageBreak())
    story.append(H1("7  Wie werden Datum und Zeiten berechnet?", st))
    story.append(P(
        "Dieses Kapitel erklaert, nach welchen Regeln transform_data die Meilenstein-"
        "Daten (First Date, Closed Date) und die Stage-Zeiten ermittelt.", st))
    story.append(H2("7.1  Stage-Zeiten", st))
    story.append(tbl(
        ["Situation", "Regel"],
        [
            ["Issue erstellt, aber noch kein Statuswechsel",
             "Die Zeit von der Erstellung bis zum ersten Statuswechsel wird der "
             "initialen Stage zugerechnet."],
            ["Statuswechsel zu einer nicht gemappten Stage",
             "Die Zeit laeuft in der letzten bekannten Stage weiter (Carry-forward)."],
            ["Aktueller Status",
             "Die letzte bekannte Stage akkumuliert Zeit bis zum Zeitpunkt der Verarbeitung."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "Das First Date wird gesetzt, sobald ein Issue zum ersten Mal in die mit "
        "<b>&lt;First&gt;</b> markierte Stage wechselt. "
        "Es repraesentiert den Beginn der aktiven Bearbeitung.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Uebersprungene First-Stage:</b> Betritt ein Issue eine Stage nach der "
        "&lt;First&gt;-Stage, ohne diese selbst zu betreten, wird der Eintrittszeitpunkt "
        "als First Date verwendet.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "Das Closed Date wird beim Eintritt in die mit <b>&lt;Closed&gt;</b> markierte "
        "Stage gesetzt. Bei Issues, die mehrfach geoeffnet und geschlossen wurden, "
        "zaehlt der <b>letzte</b> Schliessungszeitpunkt.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Wiedergeoeffnete Issues:</b> Befindet sich ein Issue aktuell in einer Stage "
        "vor der &lt;Closed&gt;-Stage, wird kein Closed Date gesetzt -- auch wenn die "
        "Stage zuvor schon einmal erreicht wurde.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Nie bearbeitete Issues:</b> Issues ohne First Date (direkt von To Do nach "
        "Closed gesprungen) erhalten kein Closed Date und zaehlen nicht in der "
        "Flow Velocity.", st, "#e8eaf6"))

    # 8
    story.append(PageBreak())
    story.append(H1("8  Haeufige Fragen und Tipps", st))
    faqs = [
        ("Ein Issue hat kein First Date -- warum?",
         "Das Issue hat weder die <First>-Stage noch eine Stage danach (vor Closed) "
         "erreicht. In build_reports wird es als 'To Do' gezaehlt."),
        ("Ein Issue hat kein Closed Date -- warum?",
         "Moegliche Gruende: (1) Das Issue ist noch offen. "
         "(2) Es hat kein First Date. "
         "(3) Es wurde nach dem Abschluss wieder geoeffnet. "
         "(4) Die <Closed>-Stage wurde uebersprungen und es gibt keine spaetere Stage."),
        ("Im Log erscheint eine Warnung ueber nicht gemappte Status.",
         "Einige Jira-Status sind nicht in der Workflow-Datei definiert. "
         "Die Verarbeitung wird trotzdem abgeschlossen. Wenden Sie sich an Ihren "
         "technischen Ansprechpartner, um die Workflow-Datei zu ergaenzen."),
        ("Die Ausgabedateien werden nicht erstellt.",
         "Pruefen Sie, ob der Ausgabeordner existiert und ob Sie Schreibrechte haben. "
         "Stellen Sie sicher, dass die Dateien nicht in Excel geoeffnet sind."),
        ("Welche Datei verwende ich fuer build_reports?",
         "IssueTimes.xlsx ist die Pflichtdatei fuer alle Metriken ausser CFD. "
         "CFD.xlsx benoetigen Sie zusaetzlich fuer das Cumulative Flow Diagram."),
        ("Wie oft muss ich transform_data ausfuehren?",
         "Immer dann, wenn Sie aktualisierte Daten aus Jira benoetigen."),
        ("Was bedeutet 'Carry-forward'?",
         "Zeit in einem nicht gemappten Status wird der letzten bekannten Stage "
         "zugerechnet -- es gibt keinen Zeitverlust."),
    ]
    for q, a in faqs:
        story.append(H3("F: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # 9
    story.append(PageBreak())
    story.append(H1("9  Glossar", st))
    story.append(tbl(
        ["Begriff", "Erklaerung"],
        [
            ["Carry-forward",
             "Zeit in einem nicht gemappten Status wird der letzten bekannten Stage zugerechnet."],
            ["CFD",
             "Cumulative Flow Diagram -- zeigt die Entwicklung des Bestands nach Stages."],
            ["Closed Date",
             "Datum des Abschlusses eines Issues."],
            ["First Date",
             "Datum der ersten aktiven Bearbeitung."],
            ["Implementation Date",
             "Datum des Entwicklungsbeginns."],
            ["Issue",
             "Ein Ticket im Ticketsystem (z.B. eine Jira-Karte)."],
            ["JSON",
             "Einfaches Textformat fuer strukturierte Daten."],
            ["Marker",
             "Zeilen in der Workflow-Datei, die eine Stage als Meilenstein auszeichnen: "
             "<First>, <InProgress>, <Closed>."],
            ["Praefix",
             "Namens-Vorsatz fuer die Ausgabedateien (z.B. 'ART_A')."],
            ["Stage",
             "Ein logischer Prozessschritt, dem ein oder mehrere Jira-Status zugeordnet sind."],
            ["Workflow-Datei",
             "Textdatei, die die Stages und Marker eines Projekts beschreibt."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content — English
# ---------------------------------------------------------------------------

def content_en(st):
    """Build English document story."""
    story = []

    story.append(PageBreak())
    story.append(H1("Contents", st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOCH1en", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle("TOCH2en", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle("TOCH3en", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    story.append(toc)

    # 1
    story.append(PageBreak())
    story.append(H1("1  What is transform_data?", st))
    story.append(P(
        "transform_data is the first module in the situation-report toolchain. "
        "It reads a raw data export from your issue tracker (Jira) and prepares "
        "the data for further analysis. The result is three <b>Excel files</b> that "
        "show how long issues spent in each workflow step and how the backlog evolved "
        "over time.", st))
    story.append(P(
        "The program has a simple graphical user interface (GUI): no programming "
        "knowledge required. Select two files, click 'Run', and the Excel files are "
        "produced automatically.", st))
    story.append(SP(8))
    story.append(box(
        "<b>What transform_data produces:</b><br/>"
        "- <b>IssueTimes.xlsx</b>: All issues with milestone timestamps and minutes "
        "per workflow stage.<br/>"
        "- <b>Transitions.xlsx</b>: Complete status history of all issues.<br/>"
        "- <b>CFD.xlsx</b>: Daily entry counts per stage for the Cumulative Flow Diagram.", st))
    story.append(SP(8))
    story.append(P(
        "The generated Excel files are then used by the <b>build_reports</b> module "
        "to create charts and reports.", st))

    # 2
    story.append(PageBreak())
    story.append(H1("2  Prerequisites and Installation", st))
    story.append(H2("2.1  What needs to be installed?", st))
    story.append(P(
        "transform_data requires <b>Python 3.11 or later</b> to be installed on the "
        "machine, along with several Python packages. Whoever set up the program for "
        "you should have already taken care of this.", st))
    story.append(H2("2.2  Starting the program", st))
    story.append(P("There are two ways to start transform_data:", st))
    story.append(BL(
        "<b>Double-click</b> on <b>transform_data_gui.pyw</b> in the project folder "
        "-- opens the GUI without a console window.", st))
    story.append(BL(
        "<b>Terminal / Command Prompt</b>: Navigate to the project directory and "
        "enter <font name='Courier'>python -m transform_data</font>.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip:</b> If you use the GUI regularly, create a shortcut to "
        "<b>transform_data_gui.pyw</b> on your desktop.", st, "#e8f8f0"))

    # 3
    story.append(PageBreak())
    story.append(H1("3  Input Files", st))
    story.append(P(
        "transform_data requires exactly two files: the Jira JSON export and the "
        "workflow definition file. Both are selected in the GUI via file dialogs.", st))
    story.append(H2("3.1  Jira JSON Export", st))
    story.append(P(
        "This is an export of all issues in a Jira project in JSON format. "
        "It contains the complete status history (changelog), metadata such as issue "
        "type and creation date, and the current status for each ticket.", st))
    story.append(P(
        "How to generate the export from Jira is described in the <b>get_data</b> module. "
        "The JSON file should not be edited manually.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typical filename:</b> ART_A.json, MYPROJECT.json, etc.<br/>"
        "<b>Size:</b> Depends on the number of issues; often several MB.", st, "#fff8e1"))
    story.append(H2("3.2  Workflow Definition File", st))
    story.append(P(
        "The workflow file is a plain text file (.txt) that describes how the Jira "
        "statuses in your project map to logical process steps (stages). It also "
        "defines which stage marks the start of active work (First Date) and "
        "completion (Closed Date).", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typical filename:</b> workflow_ART_A.txt, etc.<br/>"
        "<b>Created by:</b> Your technical contact or Scrum Master -- "
        "once per project, rarely changed.", st, "#e8f8f0"))

    # 4
    story.append(PageBreak())
    story.append(H1("4  The Workflow Definition File", st))
    story.append(P(
        "The workflow file controls how transform_data interprets the Jira statuses "
        "in your project. You usually do not need to create this file yourself -- "
        "this chapter explains its structure so you can read and adjust it if needed.", st))
    story.append(H2("4.1  Structure", st))
    story.append(P(
        "Each line describes either a <b>stage</b> (a process step) or a <b>marker</b> "
        "(a milestone). Blank lines are ignored.", st))
    story.append(SP(4))
    story.append(P("<b>Example:</b>", st))
    story.append(CD(
        "Funnel:New:Open:To Do<br/>"
        "Analysis:In Analysis:Estimated<br/>"
        "Implementation:In Implementation:In Progress<br/>"
        "Done:Canceled<br/>"
        "&lt;First&gt;Analysis<br/>"
        "&lt;InProgress&gt;Implementation<br/>"
        "&lt;Closed&gt;Done", st))
    story.append(SP(6))
    story.append(tbl(
        ["Format", "Meaning"],
        [
            ["Stage:Alias1:Alias2",
             "Stage with Jira status names mapped to it. The first name is the "
             "canonical stage name."],
            ["<First>Stage",
             "This stage marks the start of active work (First Date)."],
            ["<InProgress>Stage",
             "This stage sets the Implementation Date."],
            ["<Closed>Stage",
             "This stage marks completion (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Stage order", st))
    story.append(P(
        "Stages are listed in the order they are traversed in the process. "
        "This order is used for the Cumulative Flow Diagram and for computing "
        "the Closed Date when stages are skipped.", st))
    story.append(H2("4.3  Unmapped Jira statuses", st))
    story.append(P(
        "If the Jira export contains statuses not defined in the workflow file, "
        "transform_data issues a warning. Time in unmapped statuses is attributed "
        "to the last known stage (carry-forward).", st))

    # 5
    story.append(PageBreak())
    story.append(H1("5  The Graphical User Interface (GUI)", st))
    story.append(P(
        "After starting, a window opens with file selection fields, options, "
        "and a log area for status messages.", st))
    story.append(H2("5.1  Selecting files", st))
    story.append(P("Load the two input files:", st))
    story.append(BL(
        "<b>JSON File</b> - Click 'Browse' and select your Jira export. "
        "The output folder and prefix are filled in automatically.", st))
    story.append(BL(
        "<b>Workflow File</b> - Select the appropriate .txt workflow file "
        "for your project.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip:</b> If you select the JSON file first, the output folder "
        "and prefix are pre-filled automatically.", st, "#e8f8f0"))
    story.append(H2("5.2  Configuring output", st))
    story.append(SP(4))
    story.append(tbl(
        ["Field", "Meaning"],
        [
            ["Output Folder",
             "Directory where the three Excel files are saved. "
             "Default: directory of the JSON file."],
            ["Prefix",
             "Name prefix for output files. 'ART_A' produces "
             "ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx, and ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Starting the transformation", st))
    story.append(P(
        "Click <b>'Run'</b>. The program reads the data, computes all values, "
        "and saves the three Excel files. Progress and any warnings appear in the "
        "log area.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Warnings in the log:</b> A warning about unmapped statuses does not mean "
        "the transformation failed -- the output files are still produced.", st, "#fff8e1"))
    story.append(H2("5.4  Language and Help", st))
    story.append(P(
        "Use the <b>Options</b> menu to switch between German and English. "
        "All labels update immediately. "
        "Under <b>Help &rarr; Manual</b>, this manual opens in the active language "
        "in your browser.", st))

    # 6
    story.append(PageBreak())
    story.append(H1("6  Output Files", st))
    story.append(P(
        "transform_data produces three Excel files. These files serve as input for "
        "build_reports and should not be edited manually.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(P(
        "The main output file. Contains one row per issue with all time data.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Content"],
        [
            ["Project",            "Project key (e.g. ART_A)"],
            ["Key",                "Issue key (e.g. ART_A-123)"],
            ["Issuetype",          "Issue type (e.g. Feature, Bug, Story)"],
            ["Status",             "Current Jira status"],
            ["Created Date",       "Issue creation date in Jira"],
            ["First Date",         "First entry into the <First> stage"],
            ["Implementation Date","First entry into the <InProgress> stage"],
            ["Closed Date",        "Completion timestamp (empty = still open)"],
            ["Stage columns",      "One column per stage: minutes spent in that stage"],
            ["Resolution",         "Closure type from Jira"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(H2("6.2  Transitions.xlsx", st))
    story.append(P(
        "Contains the complete status history of all issues -- one entry per status "
        "change. Useful for detailed analysis of individual issues.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Column", "Content"],
        [
            ["Key",        "Issue key"],
            ["Transition", "Stage name (or 'Created' for the creation timestamp)"],
            ["Timestamp",  "Date and time of the status change"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("6.3  CFD.xlsx", st))
    story.append(P(
        "Contains, for each calendar day, the number of issues that entered each "
        "stage on that day. build_reports accumulates these values cumulatively "
        "to produce the Cumulative Flow Diagram.", st))

    # 7
    story.append(PageBreak())
    story.append(H1("7  How are Dates and Times Calculated?", st))
    story.append(P(
        "This chapter explains the rules transform_data uses to determine milestone "
        "dates (First Date, Closed Date) and stage times.", st))
    story.append(H2("7.1  Stage times", st))
    story.append(tbl(
        ["Situation", "Rule"],
        [
            ["Issue created but no status change yet",
             "Time from creation to the first status change is attributed to the "
             "initial stage."],
            ["Status change to an unmapped stage",
             "Time continues in the last known stage (carry-forward). No time is lost."],
            ["Current status",
             "The last known stage accumulates time until processing time."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "The First Date is set when an issue first enters the stage marked "
        "<b>&lt;First&gt;</b> in the workflow file. It represents the start of "
        "active work.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Skipped First stage:</b> If an issue enters a stage after the "
        "&lt;First&gt; stage without entering it directly, the entry timestamp "
        "of that later stage is used as the First Date.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "The Closed Date is set when an issue enters the stage marked "
        "<b>&lt;Closed&gt;</b>. If an issue was closed and re-opened multiple times, "
        "the <b>last</b> closing timestamp is used.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Re-opened issues:</b> If an issue is currently in a stage before "
        "&lt;Closed&gt;, no Closed Date is set -- even if the stage was reached "
        "previously.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Never-worked issues:</b> Issues without a First Date (jumped directly "
        "from To Do to Closed) receive no Closed Date and are not counted in "
        "Flow Velocity.", st, "#e8eaf6"))

    # 8
    story.append(PageBreak())
    story.append(H1("8  Frequently Asked Questions", st))
    faqs = [
        ("An issue has no First Date -- why?",
         "The issue never reached the <First> stage or any stage after it. "
         "In build_reports it is counted as 'To Do'."),
        ("An issue has no Closed Date -- why?",
         "Possible reasons: (1) The issue is still open. "
         "(2) It has no First Date. "
         "(3) It was re-opened after closing. "
         "(4) The <Closed> stage was skipped with no later stage in the workflow."),
        ("The log shows a warning about unmapped statuses.",
         "Some Jira statuses in the export are not defined in the workflow file. "
         "Processing still completes. Contact your technical contact to update "
         "the workflow file."),
        ("The output files are not created.",
         "Check that the output folder exists and you have write permissions. "
         "Make sure the files are not open in Excel."),
        ("Which file do I use for build_reports?",
         "IssueTimes.xlsx is required for all metrics except CFD. "
         "CFD.xlsx is additionally needed for the Cumulative Flow Diagram."),
        ("How often do I need to run transform_data?",
         "Whenever you need updated data from Jira."),
        ("What does 'carry-forward' mean?",
         "Time spent in an unmapped status is attributed to the last known stage "
         "-- no time is lost."),
    ]
    for q, a in faqs:
        story.append(H3("Q: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # 9
    story.append(PageBreak())
    story.append(H1("9  Glossary", st))
    story.append(tbl(
        ["Term", "Explanation"],
        [
            ["Carry-forward",
             "Time in an unmapped status is attributed to the last known stage."],
            ["CFD",
             "Cumulative Flow Diagram -- shows backlog evolution over time by stage."],
            ["Closed Date",
             "The date an issue was completed."],
            ["First Date",
             "The date active work began on an issue."],
            ["Implementation Date",
             "The date development work started."],
            ["Issue",
             "A ticket in the issue tracker (e.g. a Jira card)."],
            ["JSON",
             "A simple text format for structured data."],
            ["Marker",
             "Lines in the workflow file that designate a stage as a milestone: "
             "<First>, <InProgress>, <Closed>."],
            ["Prefix",
             "Name prefix for output files (e.g. 'ART_A')."],
            ["Stage",
             "A logical process step mapped to one or more Jira statuses."],
            ["Workflow file",
             "Text file describing the stages and markers of a project."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_doc(output: Path, lang: str, story_fn, title: str, subject: str):
    """Render one PDF for the given language."""
    st = make_styles()
    doc = ManualDoc(str(output), lang=lang,
                    title=title, author="Robert Seebauer", subject=subject)
    body = [Spacer(1, 1), NextPageTemplate("normal")]
    story_content, toc = story_fn(st)
    body.extend(story_content)
    doc.multiBuild(body)
    print(f"PDF erstellt: {output}")


def main():
    """Generate German and English transform_data user manuals."""
    _build_doc(OUTPUT_DE, "de", content_de,
               "transform_data Benutzerhandbuch",
               "Jira-Daten aufbereiten fuer Metriken und Berichte")
    _build_doc(OUTPUT_EN, "en", content_en,
               "transform_data User Manual",
               "Prepare Jira data for metrics and reports")


if __name__ == "__main__":
    main()
