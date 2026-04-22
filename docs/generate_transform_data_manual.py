# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       21.04.2026
# Geaendert:      22.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer transform_data als PDF-Datei.
#   Enthaelt alle Kapitel fuer Nicht-Techniker: Einleitung, Eingabedateien,
#   Workflow-Definition, GUI-Bedienung, Ausgabedateien, Datumsberechnung,
#   FAQ und Glossar.
# =============================================================================

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, NextPageTemplate, PageBreak,
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

OUTPUT = Path(__file__).parent / "transform_data_Benutzerhandbuch.pdf"


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
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=build_cover),
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
        canvas.drawString(2.2*cm, h - 0.7*cm, "transform_data -- Benutzerhandbuch")
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(w/2, 1.0*cm, "Seite %d" % doc.page)
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

def build_cover(canvas, doc):
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
    canvas.drawCentredString(w/2, h*0.545, "Benutzerhandbuch")
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.49,
                             "Jira-Daten aufbereiten fuer Metriken und Berichte")
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.455, w*0.8, h*0.455)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report - github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09,
                             "Fuer nicht-technische Anwender - Version 2026")
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
    tbl_obj = Table([[Paragraph(text, st["body"])]], colWidths=[16*cm])
    tbl_obj.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor(bg)),
        ("BOX",           (0,0), (-1,-1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return tbl_obj


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
# Content
# ---------------------------------------------------------------------------

def content(st):
    story = []

    # TOC
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

    # =========================================================================
    # 1. Einleitung
    # =========================================================================
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
        "klicken auf 'Verarbeiten' und erhalten die Excel-Dateien automatisch.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Was transform_data liefert:</b><br/>"
        "- <b>IssueTimes.xlsx</b>: Alle Issues mit Meilensteinzeitpunkten und Minuten "
        "pro Workflow-Stage.<br/>"
        "- <b>Transitions.xlsx</b>: Vollstaendige Statushistorie aller Issues.<br/>"
        "- <b>CFD.xlsx</b>: Tagesaktuelle Bestandszaehlung fuer das Cumulative Flow Diagram.", st))
    story.append(SP(8))
    story.append(P(
        "Die erzeugten Excel-Dateien werden anschliessend vom Modul <b>build_reports</b> "
        "verwendet, um Diagramme und Berichte zu erstellen.", st))

    # =========================================================================
    # 2. Voraussetzungen
    # =========================================================================
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
        "<b>Doppelklick</b> auf die Datei <b>start_gui.pyw</b> im Projektordner "
        "-- oeffnet die grafische Oberflaeche ohne ein Konsolenfenster.", st))
    story.append(BL(
        "<b>Terminal / Eingabeaufforderung</b>: Ins Projektverzeichnis wechseln und "
        "<font name='Courier'>python -m transform_data</font> eingeben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wer die GUI regelmaessig nutzt, kann eine Verknuepfung zur Datei "
        "<b>start_gui.pyw</b> auf dem Desktop erstellen.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Eingabedateien
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Eingabedateien", st))
    story.append(P(
        "transform_data benoetigt genau zwei Dateien: den Jira-JSON-Export und die "
        "Workflow-Definitionsdatei. Beide werden in der GUI per Datei-Dialog ausgewaehlt.",
        st))

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
        "Entwicklung (First Date), den Entwicklungsstart (Implementation Date) und den "
        "Abschluss (Closed Date) markiert.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typischer Dateiname:</b> workflow_ART_A.txt o.ae.<br/>"
        "<b>Erstellt von:</b> Ihrem technischen Ansprechpartner oder Scrum Master -- "
        "einmalig pro Projekt, selten geaendert.", st, "#e8f8f0"))

    # =========================================================================
    # 4. Workflow-Definitionsdatei
    # =========================================================================
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
            ["Stage",
             "Kanonischer Name eines Prozessschritts. Alle Issues, die sich in dieser "
             "Stage befinden, werden hier gezaehlt."],
            ["Stage:Alias1:Alias2",
             "Stage mit Jira-Statusnamen, die darauf gemappt werden. Alle genannten "
             "Jira-Status werden als diese Stage behandelt. Der erste Name ist der "
             "kanonische Stage-Name."],
            ["<First>Stage",
             "Diese Stage markiert den Beginn der aktiven Bearbeitung (First Date). "
             "Typisch: der erste Schritt nach dem reinen Eingang, z.B. Analysis."],
            ["<InProgress>Stage",
             "Diese Stage setzt das Implementation Date. Standard: Stage namens "
             "'Implementation', wenn vorhanden."],
            ["<Closed>Stage",
             "Diese Stage markiert den Abschluss (Closed Date). Typisch: Releasing "
             "oder Done."],
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
        "gibt transform_data eine Warnung aus:", st))
    story.append(CD(
        "WARNUNG: 2 Status in den Daten nicht in der Workflow-Datei gemappt:<br/>"
        "&nbsp;&nbsp;- To Do<br/>"
        "&nbsp;&nbsp;- Unknown<br/>"
        "&nbsp;&nbsp;> Zeit dieser Status wird der letzten bekannten Stage zugerechnet.", st))
    story.append(SP(4))
    story.append(P(
        "Die Zeit in nicht gemappten Status geht nicht verloren -- sie wird der "
        "<b>letzten bekannten Stage</b> zugerechnet (Carry-forward). "
        "Issues bleiben vollstaendig in allen Ausgaben erhalten.", st))

    # =========================================================================
    # 5. GUI
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Die grafische Oberflaeche (GUI)", st))
    story.append(P(
        "Nach dem Start oeffnet sich ein Fenster mit Datei-Auswahl-Feldern, "
        "Optionen und einem Log-Bereich fuer Statusmeldungen.", st))

    story.append(H2("5.1  Dateien auswaehlen", st))
    story.append(P("Laden Sie die beiden Eingabedateien:", st))
    story.append(BL(
        "<b>JSON-Datei</b> - Klicken Sie auf den Ordner-Button rechts neben dem "
        "JSON-Feld und waehlen Sie Ihren Jira-Export aus. Ausgabeordner und Praefix "
        "werden automatisch aus dem Dateinamen vorbelegt.", st))
    story.append(BL(
        "<b>Workflow-Datei</b> - Waehlen Sie die passende .txt-Workflow-Datei fuer "
        "Ihr Projekt aus.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wenn Sie die JSON-Datei zuerst auswaehlen, werden Ausgabeordner "
        "und Prafix automatisch vorausgefuellt. Sie muessen diese Felder nur aendern, "
        "wenn Sie einen anderen Speicherort oder Namen wuenschen.", st, "#e8f8f0"))

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
        "Klicken Sie auf <b>'Verarbeiten'</b>. Das Programm liest die Daten ein, "
        "berechnet alle Werte und speichert die drei Excel-Dateien. "
        "Der Fortschritt und eventuelle Warnungen erscheinen im Log-Bereich.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Warnungen im Log beachten:</b> Eine Warnung ueber nicht gemappte Status "
        "bedeutet nicht, dass die Verarbeitung fehlgeschlagen ist -- sie ist ein Hinweis, "
        "dass die Workflow-Datei moeglicherweise unvollstaendig ist. "
        "Die Ausgabedateien werden trotzdem erstellt.", st, "#fff8e1"))

    # =========================================================================
    # 6. Ausgabedateien
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  Die Ausgabedateien", st))
    story.append(P(
        "transform_data erzeugt drei Excel-Dateien. Diese Dateien dienen als "
        "Eingabe fuer build_reports und sollten nicht manuell bearbeitet werden.", st))

    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(P(
        "Die wichtigste Ausgabedatei. Sie enthaelt eine Zeile pro Issue mit allen "
        "Zeitangaben. Diese Datei wird von build_reports fuer alle Metriken "
        "ausser dem Cumulative Flow Diagram benoetigt.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Project",           "Projektschluessel (z.B. ART_A)"],
            ["Key",               "Issue-Schluessel (z.B. ART_A-123)"],
            ["Issuetype",         "Typ des Issues (z.B. Feature, Bug, Story)"],
            ["Status",            "Aktueller Jira-Status"],
            ["Created Date",      "Erstellungsdatum des Issues in Jira"],
            ["First Date",        "Erster Eintritt in die <First>-Stage (Beginn der Bearbeitung)"],
            ["Implementation Date","Erster Eintritt in die <InProgress>-Stage"],
            ["Closed Date",       "Zeitpunkt des Abschlusses (leer = noch offen)"],
            ["Stage-Spalten",     "Je eine Spalte pro Workflow-Stage: Minuten in dieser Stage"],
            ["Resolution",        "Abschlussart aus Jira (z.B. Fixed, Duplicate, Canceled)"],
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
        "Enthaelt fuer jeden Kalendertag die Anzahl der Issues in jeder Workflow-Stage. "
        "Diese Datei wird von build_reports fuer das Cumulative Flow Diagram benoetigt.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Day",           "Datum (YYYY-MM-DD)"],
            ["Stage-Spalten", "Je eine Spalte pro Stage: Anzahl Issues an diesem Tag"],
        ],
        col_widths=[4*cm, 12*cm]))

    # =========================================================================
    # 7. Datumsberechnung
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Wie werden Datum und Zeiten berechnet?", st))
    story.append(P(
        "Dieses Kapitel erklaert, nach welchen Regeln transform_data die Meilenstein-"
        "Daten (First Date, Closed Date) und die Stage-Zeiten ermittelt. "
        "Das Verstaendnis dieser Regeln hilft bei der Interpretation der Ergebnisse.", st))

    story.append(H2("7.1  Stage-Zeiten", st))
    story.append(P(
        "Fuer jedes Issue wird gemessen, wie viele Minuten es in jeder Stage verbracht hat. "
        "Dabei gelten folgende Regeln:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Situation", "Regel"],
        [
            ["Issue erstellt, aber noch kein Statuswechsel",
             "Die Zeit von der Erstellung bis zum ersten Statuswechsel wird der "
             "initialen Stage zugerechnet."],
            ["Statuswechsel zu einer nicht gemappten Stage",
             "Die Zeit laeuft in der letzten bekannten Stage weiter (Carry-forward). "
             "Es gibt keinen Zeitverlust."],
            ["Aktueller Status",
             "Die letzte bekannte Stage akkumuliert Zeit bis zum Zeitpunkt der Verarbeitung."],
            ["Kein Statuswechsel",
             "Alle Stage-Spalten zeigen 0 Minuten."],
        ],
        col_widths=[5*cm, 11*cm]))

    story.append(H2("7.2  First Date", st))
    story.append(P(
        "Das First Date wird gesetzt, sobald ein Issue zum ersten Mal in die in der "
        "Workflow-Datei mit <b>&lt;First&gt;</b> markierte Stage wechselt. "
        "Es repraesentiert den Beginn der aktiven Bearbeitung.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Uebersprungene First-Stage:</b> Betritt ein Issue eine Stage, die im Workflow "
        "<b>nach</b> der &lt;First&gt;-Stage, aber <b>vor</b> der &lt;Closed&gt;-Stage liegt, "
        "ohne die First-Stage selbst zu betreten, wird der Eintrittszeitpunkt dieser "
        "spaeter erreichten Stage als First Date verwendet. "
        "Gleiches gilt fuer die &lt;InProgress&gt;-Stage: wird sie uebersprungen, aber "
        "eine Stage danach (vor Closed) betreten, gilt deren Zeitstempel als "
        "Implementation Date -- sofern ein First Date vorhanden ist.<br/><br/>"
        "Issues, die ausschliesslich die Closed-Stage oder spaetere Stages erreichen "
        "ohne vorherige Entwicklungsschritte, erhalten kein First Date.", st, "#e8f5e9"))

    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "Das Closed Date wird beim Eintritt in die mit <b>&lt;Closed&gt;</b> markierte "
        "Stage gesetzt. Bei Issues, die mehrfach geoeffnet und geschlossen wurden, "
        "zaehlt der <b>letzte</b> Schliessungszeitpunkt.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Uebersprungene Closed-Stage:</b> Hat ein Issue ein First Date, aber die "
        "&lt;Closed&gt;-Stage wurde im Prozess uebersprungen (z.B. direkter Wechsel "
        "von 'Implementation' nach 'Done'), gilt die <b>erste Stage chronologisch nach "
        "der Closed-Stage</b> im Workflow als Abschlusszeitpunkt. "
        "Issues ohne First Date erhalten kein Closed Date.", st, "#fff8e1"))
    story.append(SP(4))
    story.append(box(
        "<b>Wiedergeoeffnete Issues:</b> Befindet sich ein Issue aktuell in einer Stage "
        "<b>vor</b> der &lt;Closed&gt;-Stage, wird kein Closed Date gesetzt -- auch wenn "
        "die Stage oder eine spaetere Stage zuvor schon einmal erreicht wurde. "
        "Das Issue gilt als noch offen.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Nie bearbeitete Issues:</b> Issues, die direkt von einer 'To Do'-Stage "
        "in die &lt;Closed&gt;-Stage gesprungen sind, ohne je in Bearbeitung zu sein "
        "(kein First Date), erhalten <b>kein Closed Date</b>. Sie erscheinen in keiner "
        "Metrik als abgeschlossen und zaehlen auch nicht in der Flow Velocity. "
        "Typisches Muster: Issue wurde im Ticketsystem manuell in wenigen Sekunden "
        "durch alle Status geklickt ohne echte Entwicklungsarbeit.", st, "#e8eaf6"))

    story.append(H2("7.4  Beispiele", st))
    story.append(P("Beispiel 1 -- Uebersprungene Closed-Stage (ART_A-615):", st))
    story.append(SP(4))
    story.append(tbl(
        ["Datum", "Statuswechsel", "Ergebnis"],
        [
            ["13.10.2025", "Funnel -> Analysis",
             "First Date = 13.10.2025 (Analysis ist <First>-Stage)"],
            ["07.11.2025", "Analysis -> Program Backlog", ""],
            ["07.11.2025", "Program Backlog -> Implementation",
             "Implementation Date = 07.11.2025"],
            ["21.11.2025", "Implementation -> Done",
             "Done liegt nach Releasing (<Closed>-Stage) -> Closed Date = 21.11.2025"],
        ],
        col_widths=[3*cm, 5.5*cm, 7.5*cm]))
    story.append(SP(8))
    story.append(P("Beispiel 2 -- Uebersprungene First-Stage (ART_A-583):", st))
    story.append(SP(4))
    story.append(tbl(
        ["Datum", "Statuswechsel", "Ergebnis"],
        [
            ["08.09.2025", "Funnel -> Program Backlog",
             "First Date = 08.09.2025 (Program Backlog liegt nach Analysis im Workflow)"],
            ["13.10.2025", "Program Backlog -> Implementation",
             "Implementation Date = 13.10.2025"],
            ["02.11.2025", "Implementation -> Releasing",
             "Closed Date = 02.11.2025 (Releasing ist <Closed>-Stage)"],
        ],
        col_widths=[3*cm, 5.5*cm, 7.5*cm]))
    story.append(SP(8))
    story.append(P("Beispiel 3 -- Wiedergeoeffnetes Issue (ART_A-2):", st))
    story.append(SP(4))
    story.append(tbl(
        ["Datum", "Statuswechsel", "Ergebnis"],
        [
            ["10.01.2025", "Funnel -> Implementation",
             "First Date = 10.01.2025 (Fallback: Implementation nach Analysis)"],
            ["16.01.2025", "Implementation -> Done", "Done liegt nach Releasing -> vorl. Closed Date"],
            ["17.01.2025", "Done -> Program Backlog",
             "Issue wiedergeoeffnet -- Program Backlog liegt VOR Releasing"],
            ["17.01.2025", "... -> Program Backlog (aktueller Status)",
             "Closed Date = leer (Issue ist aktuell noch offen)"],
        ],
        col_widths=[3*cm, 5.5*cm, 7.5*cm]))

    # =========================================================================
    # 8. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Haeufige Fragen und Tipps", st))

    faqs = [
        (
            "Ein Issue hat kein First Date -- warum?",
            "Das Issue hat weder die <First>-Stage noch eine Stage danach (vor Closed) "
            "erreicht. Es ist moeglicherweise direkt aus dem Eingang storniert oder "
            "ausschliesslich in Stages vor der <First>-Stage verblieben. "
            "In build_reports wird es als 'To Do' gezaehlt."
        ),
        (
            "Ein Issue hat kein Closed Date -- warum?",
            "Vier moegliche Gruende: (1) Das Issue ist noch offen und hat den "
            "Abschlusspunkt im Prozess noch nicht erreicht. "
            "(2) Es hat kein First Date -- es war nie in Bearbeitung (z. B. direkt "
            "storniert oder von To Do nach Closed gesprungen ohne Entwicklungsarbeit). "
            "Ohne First Date wird kein Closed Date gesetzt. "
            "(3) Das Issue wurde nach dem Abschluss wieder geoeffnet -- sein aktueller "
            "Status liegt vor der <Closed>-Stage. "
            "(4) Die <Closed>-Stage wurde uebersprungen und es existiert auch keine "
            "spaeteren Stage danach in der Workflow-Reihenfolge. Pruefen Sie den "
            "aktuellen Status in der IssueTimes.xlsx."
        ),
        (
            "Im Log erscheint eine Warnung ueber nicht gemappte Status.",
            "Einige Jira-Status im Export sind nicht in der Workflow-Datei definiert. "
            "Die Verarbeitung wird trotzdem abgeschlossen. Die Zeit dieser Status wird "
            "der letzten bekannten Stage zugerechnet. Wenden Sie sich an Ihren "
            "technischen Ansprechpartner, um die Workflow-Datei zu erganzen."
        ),
        (
            "Die Ausgabedateien werden nicht erstellt.",
            "Pruefen Sie, ob der Ausgabeordner existiert und ob Sie Schreibrechte "
            "haben. Beachten Sie auch, ob die Dateien moeglicherweise noch in Excel "
            "geoeffnet sind -- Excel sperrt Dateien beim Oeffnen, was das Ueberschreiben "
            "verhindert."
        ),
        (
            "Welche Datei verwende ich fuer build_reports?",
            "IssueTimes.xlsx ist die Pflichtdatei fuer alle Metriken ausser dem "
            "Cumulative Flow Diagram. CFD.xlsx benoetigen Sie zusaetzlich fuer das CFD. "
            "Transitions.xlsx wird von build_reports nicht direkt verwendet, "
            "steht aber fuer eigene Analysen bereit."
        ),
        (
            "Kann ich die Ausgabedateien manuell bearbeiten?",
            "Das sollten Sie vermeiden. build_reports erwartet ein genaues Format. "
            "Wenn Sie Daten filtern oder ergaenzen moechten, nutzen Sie die "
            "Filter-Funktion in build_reports, anstatt die Quelldateien zu veraendern."
        ),
        (
            "Wie oft muss ich transform_data ausfuehren?",
            "Immer dann, wenn Sie aktualisierte Daten aus Jira benoetigen. "
            "Ein neuer Export (get_data) gefolgt von einer neuen Verarbeitung "
            "(transform_data) liefert stets den aktuellen Stand."
        ),
        (
            "Was bedeutet 'Carry-forward'?",
            "Wenn ein Issue in einen Status wechselt, der nicht in der Workflow-Datei "
            "gemappt ist, laeuft die Zeit weiterhin in der letzten bekannten Stage. "
            "Es gibt also keinen 'Zeitverlust' -- die Minuten werden immer einer Stage "
            "zugeordnet."
        ),
    ]
    for q, a in faqs:
        story.append(H3("F: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 9. Glossar
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("9  Glossar", st))
    story.append(tbl(
        ["Begriff", "Erklaerung"],
        [
            ["Carry-forward",
             "Zeit in einem nicht gemappten Status wird der letzten bekannten Stage "
             "zugerechnet -- kein Zeitverlust."],
            ["CFD",
             "Cumulative Flow Diagram -- zeigt die Entwicklung des Bestands "
             "ueber die Zeit aufgeteilt nach Stages."],
            ["Closed Date",
             "Datum des Abschlusses eines Issues. Gesetzt beim Eintritt in die "
             "<Closed>-Stage oder, falls diese uebersprungen wurde, bei der "
             "naechsten Stage danach (sofern First Date vorhanden)."],
            ["First Date",
             "Datum der ersten aktiven Bearbeitung. Gesetzt beim ersten Eintritt "
             "in die <First>-Stage."],
            ["Implementation Date",
             "Datum des Entwicklungsbeginns. Gesetzt beim ersten Eintritt in die "
             "<InProgress>-Stage."],
            ["Issue",
             "Ein Ticket im Ticketsystem (z.B. eine Jira-Karte)."],
            ["Issuetyp",
             "Kategorie eines Issues, z.B. Feature, Bug, Story, Task."],
            ["JSON",
             "Einfaches Textformat fuer strukturierte Daten. Der Jira-Export liegt "
             "in diesem Format vor."],
            ["Kanonischer Stage-Name",
             "Der erste Name in einer Stage-Zeile der Workflow-Datei. Alle Aliase "
             "werden intern auf diesen Namen abgebildet."],
            ["Marker",
             "Zeilen in der Workflow-Datei, die eine Stage als Meilenstein auszeichnen: "
             "<First>, <InProgress>, <Closed>."],
            ["Praefix",
             "Namens-Vorsatz fuer die Ausgabedateien (z.B. 'ART_A' ergibt "
             "ART_A_IssueTimes.xlsx)."],
            ["Stage",
             "Ein logischer Prozessschritt, dem ein oder mehrere Jira-Status "
             "zugeordnet sind (z.B. 'Analysis')."],
            ["Workflow-Datei",
             "Textdatei, die die Stages und Marker eines Projekts beschreibt. "
             "Einmalig pro Projekt angelegt."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st = make_styles()
    doc = ManualDoc(
        str(OUTPUT),
        title="transform_data Benutzerhandbuch",
        author="Robert Seebauer",
        subject="Jira-Daten aufbereiten fuer Metriken und Berichte",
    )

    story = [
        Spacer(1, 1),
        NextPageTemplate("normal"),
    ]
    story_content, toc = content(st)
    story.extend(story_content)

    doc.multiBuild(story)
    print("PDF erstellt: %s" % OUTPUT)


if __name__ == "__main__":
    main()
