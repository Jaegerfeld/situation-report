# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       17.04.2026
# Geaendert:      22.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer build_reports als PDF-Datei.
#   Enthaelt alle Kapitel fuer Nicht-Techniker: Einleitung, Dateien,
#   GUI-Bedienung, Metriken-Erklaerungen und Tipps.
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

OUTPUT = Path(__file__).parent / "build_reports_Benutzerhandbuch.pdf"


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
        canvas.drawString(2.2*cm, h - 0.7*cm, "build_reports -- Benutzerhandbuch")
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
# Cover page (drawn via onFirstPage callback)
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
    canvas.drawCentredString(w/2, h*0.60, "build_reports")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(w/2, h*0.545, "Benutzerhandbuch")
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.49,
                             "Flow-Metriken fuer agile Teams - Einrichtung und Bedienung")
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
    tbl = Table([[Paragraph(text, st["body"])]], colWidths=[16*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor(bg)),
        ("BOX",           (0,0), (-1,-1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return tbl


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
    story.append(H1("1  Was ist build_reports?", st))
    story.append(P(
        "build_reports ist ein Werkzeug, das automatisch aussagekraeftige Diagramme "
        "ueber den Fortschritt und die Effizienz Ihres agilen Teams erstellt. "
        "Als Eingabe werden die Daten verwendet, die das Modul <b>transform_data</b> "
        "aus Ihrem Ticketsystem (z.&nbsp;B. Jira) exportiert hat. build_reports liest "
        "diese Dateien und berechnet daraus mehrere <b>Flow-Metriken</b> - grafische "
        "Auswertungen, die zeigen, wie schnell und wie viel Ihr Team liefert.", st))
    story.append(P(
        "Das Programm besitzt eine einfache grafische Oberflaeche (GUI): keine "
        "Programmierkenntnisse erforderlich. Per Knopfdruck werden die Diagramme im "
        "Browser angezeigt oder als PDF-Datei gespeichert.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Uebersicht der Metriken</b><br/>"
        "- <b>Flow Time / Cycle Time</b>: Wie lange dauert es, bis ein Issue fertig ist?<br/>"
        "- <b>Flow Velocity / Throughput</b>: Wie viele Issues schliesst das Team pro Woche ab?<br/>"
        "- <b>Flow Load / WIP</b>: Wie viele Issues sind gleichzeitig in Bearbeitung?<br/>"
        "- <b>Cumulative Flow Diagram</b>: Wie entwickelt sich der Bestand ueber die Zeit?<br/>"
        "- <b>Flow Distribution</b>: Wie verteilen sich die Issues auf Typen und Status?", st))

    # =========================================================================
    # 2. Voraussetzungen
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("2  Voraussetzungen und Installation", st))

    story.append(H2("2.1  Was muss installiert sein?", st))
    story.append(P(
        "Damit build_reports funktioniert, muss auf dem Rechner <b>Python 3.11 oder "
        "neuer</b> installiert sein. Ausserdem muessen einige Python-Pakete vorhanden "
        "sein. Wer das Programm fuer Sie eingerichtet hat, sollte dies bereits erledigt "
        "haben.", st))

    story.append(H2("2.2  Programm starten", st))
    story.append(P("Es gibt zwei Moeglichkeiten, build_reports zu starten:", st))
    story.append(BL(
        "<b>Doppelklick</b> auf die Datei <b>build_reports_gui.pyw</b> im Projektordner "
        "-- oeffnet die grafische Oberflaeche ohne ein Konsolenfenster.", st))
    story.append(BL(
        "<b>Terminal / Eingabeaufforderung</b>: Ins Projektverzeichnis wechseln und "
        "<font name='Courier'>python -m build_reports</font> eingeben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wer die GUI regelmaessig nutzt, kann eine Verknuepfung zur Datei "
        "<b>build_reports_gui.pyw</b> auf dem Desktop erstellen.", st, "#e8f8f0"))

    # =========================================================================
    # 3. Eingabedateien
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("3  Eingabedateien", st))
    story.append(P(
        "build_reports benoetigt eine oder zwei Excel-Dateien, die vom Modul "
        "<b>transform_data</b> erstellt wurden. Diese Dateien duerfen nicht von Hand "
        "bearbeitet werden - der Aufbau muss exakt dem erwarteten Format entsprechen.",
        st))

    story.append(H2("3.1  IssueTimes.xlsx  (Pflichtdatei)", st))
    story.append(P(
        "Diese Datei enthaelt alle Issues (Tickets) mit ihren Zeitangaben und dem "
        "aktuellen Bearbeitungsstatus. Sie wird fuer alle Metriken ausser dem "
        "Cumulative Flow Diagram benoetigt.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Bedeutung"],
        [
            ["Project",       "Projektschluessel (z.B. ARTA)"],
            ["Key",           "Issue-Schluessel (z.B. ARTA-123)"],
            ["Issuetype",     "Typ des Issues (z.B. Feature, Bug, Story)"],
            ["Status",        "Aktueller Status (z.B. In Progress, Done)"],
            ["Created",       "Erstellungsdatum des Issues"],
            ["First Date",    "Datum, an dem das Issue erstmals aktiv bearbeitet wurde"],
            ["Closed Date",   "Datum des Abschlusses (leer = noch offen)"],
            ["Resolution",    "Abschlussart (z.B. Fixed, Duplicate)"],
            ["Stage-Spalten", "Je eine Spalte pro Workflow-Stage mit Minuten in dieser Stage"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.2  CFD.xlsx  (optional, fuer Cumulative Flow Diagram)", st))
    story.append(P(
        "Diese Datei enthaelt tagesgenaue Zaehlungen, wie viele Issues sich an jedem "
        "Tag in welchem Status befanden. Sie wird nur benoetigt, wenn das Cumulative "
        "Flow Diagram berechnet werden soll.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Bedeutung"],
        [
            ["Day",           "Datum (YYYY-MM-DD)"],
            ["Stage-Spalten", "Je eine Spalte pro Status mit der Anzahl Issues an diesem Tag"],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(SP(8))
    story.append(H2("3.3  PI-Konfigurationsdatei  (optional, fuer Flow Velocity)", st))
    story.append(P(
        "Mit einer optionalen JSON-Konfigurationsdatei koennen Sie eigene PI-Intervalle "
        "(Program Increments) fuer das Flow-Velocity-Balkendiagramm definieren. Ohne "
        "diese Datei werden automatisch Kalenderquartale verwendet.", st))
    story.append(SP(4))
    story.append(P("<b>Beispiel (Datumsmodus):</b>", st))
    story.append(CD(
        '{ "mode": "date",<br/>'
        '&nbsp;&nbsp;"intervals": [<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.1", "from": "2025-01-06", "to": "2025-04-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.2", "from": "2025-04-05", "to": "2025-07-04"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.3", "from": "2025-07-05", "to": "2025-10-03"},<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;{"name": "PI 2025.4", "from": "2025-10-04", "to": "2026-01-02"}<br/>'
        '&nbsp;&nbsp;]<br/>'
        '}', st))
    story.append(P(
        "Die Datei muss die Endung <b>.json</b> haben. Kopieren Sie die mitgelieferte "
        "Beispieldatei <b>pi_config_example.json</b> und passen Sie die Datumsangaben "
        "und Namen an Ihre PI-Termine an. Das Format muss erhalten bleiben.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Datumsangaben immer im Format <b>YYYY-MM-DD</b> (Jahr-Monat-Tag). "
        "Beispiel: 6. Januar 2025 = 2025-01-06.", st, "#fff8e1"))

    # =========================================================================
    # 4. GUI
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("4  Die grafische Oberflaeche (GUI)", st))
    story.append(P(
        "Nach dem Start oeffnet sich das Hauptfenster. Es besteht aus drei Bereichen: "
        "dem <b>Dateibereich</b> (oben), dem <b>Filterbereich</b> (Mitte) und dem "
        "<b>Aktionsbereich</b> (unten) mit dem Log-Fenster.", st))

    story.append(H2("4.1  Dateien laden", st))
    story.append(P("Laden Sie zuerst die benoetigten Dateien:", st))
    story.append(BL(
        "<b>IssueTimes</b> - Klicken Sie auf den Ordner-Button rechts neben dem Feld "
        "und waehlen Sie die <b>IssueTimes.xlsx</b>-Datei aus. Nach dem Laden erscheinen "
        "die verfuegbaren Projekte und Issuetypen automatisch im Log.", st))
    story.append(BL(
        "<b>CFD (optional)</b> - Waehlen Sie die <b>CFD.xlsx</b>-Datei, wenn Sie das "
        "Cumulative Flow Diagram benoetigen.", st))
    story.append(BL(
        "<b>PI-Konfig (optional)</b> - Waehlen Sie Ihre JSON-Konfigurationsdatei fuer "
        "eigene PI-Intervalle. Lassen Sie das Feld leer, um Kalenderquartale zu "
        "verwenden.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Beim Hover ueber ein Eingabefeld erscheint ein Tooltip, der "
        "erklaert, wofuer das Feld verwendet wird.", st, "#e8f8f0"))

    story.append(H2("4.2  Filter setzen", st))
    story.append(P(
        "Mit Filtern schraenken Sie ein, welche Issues in die Auswertung einfliessen:",
        st))
    story.append(SP(4))
    story.append(tbl(
        ["Filter / Ausschluss", "Beschreibung"],
        [
            ["Von / Bis",
             "Nur Issues beruecksichtigen, die in diesem Zeitraum abgeschlossen wurden. "
             "Format: YYYY-MM-DD. Der Kalender-Button oeffnet einen Datums-Picker."],
            ["Letzte 365 Tage",
             "Setzt Von und Bis automatisch auf die letzten 365 Tage bis heute."],
            ["Projekte",
             "Nur bestimmte Projekte auswerten. Mehrere Projekte mit Komma trennen, "
             "z.B. ARTA, ARTB. Der Auswahl-Button zeigt alle verfuegbaren Projekte."],
            ["Issuetypen",
             "Nur bestimmte Issue-Typen auswerten, z.B. Feature, Bug. "
             "Leer lassen = alle Typen. Der Auswahl-Button zeigt eine Auswahlliste."],
            ["Ausschliessen: Status",
             "Issues mit bestimmten Jira-Status vollstaendig aus allen Metriken entfernen, "
             "z.B. 'Canceled'. Der Auswahl-Button zeigt alle vorhandenen Status."],
            ["Ausschliessen: Resolution",
             "Issues mit bestimmten Abschlussarten ausschliessen, z.B. 'Won't Do' oder "
             "'Duplicate'. Der Auswahl-Button zeigt alle vorhandenen Resolutions."],
            ["Zero-Day-Issues ausschliessen",
             "Checkbox: Issues, deren Durchlaufzeit (First bis Closed Date) kuerzer als "
             "der eingestellte Schwellwert ist, werden komplett entfernt. Standard: "
             "5 Minuten. Typisch fuer Issues, die manuell durch den Workflow geklickt "
             "wurden ohne echte Entwicklungsarbeit."],
        ],
        col_widths=[3.8*cm, 12.2*cm]))

    story.append(H2("4.3  Metriken und CT-Methode auswaehlen", st))
    story.append(P(
        "Ueber die Checkboxen waehlen Sie aus, welche Metriken berechnet werden sollen. "
        "Mit <b>Alle</b> und <b>Keine</b> koennen alle Checkboxen auf einmal gesetzt "
        "oder geleert werden.", st))
    story.append(SP(4))
    story.append(P(
        "Die <b>CT-Methode</b> bestimmt, wie die Durchlaufzeit (Cycle Time) berechnet "
        "wird - nur relevant fuer die Flow-Time-Metrik:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Methode", "Berechnung"],
        [
            ["Methode A (Standard)",
             "Differenz in Kalendertagen zwischen First Date und Closed Date. "
             "Einfach und nachvollziehbar."],
            ["Methode B",
             "Summe der Minuten in den einzelnen Workflow-Stages (letzte Stage "
             "ausgeschlossen), dividiert durch 1440. Misst nur aktive Bearbeitungszeit."],
        ],
        col_widths=[4*cm, 12*cm]))

    story.append(H2("4.4  Bericht erstellen", st))
    story.append(P("Sie haben zwei Moeglichkeiten:", st))
    story.append(BL(
        "<b>Im Browser anzeigen</b> - Alle Diagramme werden in Ihrem Standard-Browser "
        "geoeffnet. Die Diagramme sind dort vollstaendig interaktiv: Hineinzoomen, "
        "Datenpunkte per Hover-Tooltip inspizieren und einzelne Kategorien in der "
        "Legende ein- und ausblenden.", st))
    story.append(BL(
        "<b>Reports exportieren</b> - Alle Diagramme werden in eine mehrseitige PDF-Datei "
        "exportiert. Ein Speicherdialog fragt nach Dateiname und Speicherort. "
        "Zusaetzlich zur PDF werden automatisch zwei Excel-Dateien erstellt: eine "
        "Report-Excel mit allen Issues, Statusgruppen und Durchlaufzeiten sowie -- bei "
        "vorhandenen Zero-Day Issues -- eine separate Datei fuer diese Issues.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Waehrend die Berechnungen laufen, ist die Oberflaeche kurz "
        "gesperrt. Der Fortschritt wird im Log-Fenster angezeigt. Bitte nicht schliessen "
        "oder klicken, bis das Log die Fertigmeldung zeigt.", st, "#fff8e1"))

    story.append(H2("4.5  Templates -- Konfiguration speichern und laden", st))
    story.append(P(
        "Im Menue <b>Templates</b> koennen Sie alle aktuellen Einstellungen "
        "(Dateipfade, Filter, Metrikauswahl, CT-Methode, Terminologie) als JSON-Datei "
        "speichern und spaeter wieder laden. So muessen Sie nicht jedes Mal alle Felder "
        "neu ausfuellen.", st))
    story.append(BL(
        "<b>Speichern...</b> - Waehlen Sie einen Speicherort und einen Namen fuer die "
        "Konfigurationsdatei (z.B. meinTeam_Quartalsbericht.json).", st))
    story.append(BL(
        "<b>Laden...</b> - Oeffnen Sie eine gespeicherte Konfigurationsdatei. Alle "
        "Felder werden automatisch befuellt. Falls eine gespeicherte Datei nicht mehr "
        "gefunden wird, erscheint ein Hinweis im Log.", st))

    story.append(H2("4.6  Sprache und Terminologie", st))
    story.append(P(
        "Im Menue <b>Optionen</b> koennen Sie Sprache und Terminologie umschalten:", st))
    story.append(BL(
        "<b>Sprache</b> - Wechselt zwischen Deutsch und Englisch. Alle Beschriftungen, "
        "Tooltips und Menupunkte werden sofort aktualisiert.", st))
    story.append(BL(
        "<b>Terminologie</b> - Wechselt zwischen <b>SAFe</b> und <b>Global</b>. "
        "Im SAFe-Modus heissen die Metriken z.B. 'Flow Time', im Global-Modus "
        "'Cycle Time'. Diese Umstellung betrifft nur die Bezeichnungen, nicht die "
        "Berechnungen.", st))

    # =========================================================================
    # 5. Metriken
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("5  Die Metriken im Ueberblick", st))
    story.append(P(
        "Dieser Abschnitt erklaert jede Metrik in einfachen Worten: was sie misst, "
        "was die Diagramme zeigen und wie man die Ergebnisse interpretiert.", st))

    # --- 5.1 Flow Time -------------------------------------------------------
    story.append(H2("5.1  Flow Time / Cycle Time", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Die Durchlaufzeit - also die Anzahl der Tage, die "
        "ein Issue von der ersten Bearbeitung bis zum Abschluss benoetigt. Je kuerzer, "
        "desto besser.", st))

    story.append(H3("Diagramm 1: Boxplot (Verteilung)", st))
    story.append(P(
        "Der Boxplot zeigt auf einen Blick, wie die Durchlaufzeiten verteilt sind. "
        "Im Kopf des Diagramms stehen die wichtigsten Kennzahlen:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Kennzahl", "Bedeutung"],
        [
            ["Min / Max",   "Kuerzeste und laengste gemessene Durchlaufzeit"],
            ["Q1 / Q3",     "25% bzw. 75% der Issues liegen unterhalb dieses Werts"],
            ["Median",      "Die mittlere Durchlaufzeit -- 50% der Issues liegen darunter"],
            ["Mittelwert",  "Durchschnittliche Durchlaufzeit (kann durch Ausreisser verzerrt sein)"],
            ["P85 / P95",   "85% bzw. 95% der Issues wurden innerhalb dieser Zeit fertig"],
            ["Std.abw.",    "Standardabweichung -- wie stark streuen die Werte?"],
            ["VK",          "Variationskoeffizient -- relative Streuung (kleiner = stabiler Prozess)"],
            ["Zero-Day",    "Anzahl Issues mit Durchlaufzeit 0 (von der Auswertung ausgeschlossen)"],
        ],
        col_widths=[3*cm, 13*cm]))
    story.append(SP(4))
    story.append(HI(
        "Roter Punkt im Boxplot = statistischer Ausreisser. Im Browser koennen Sie den "
        "Issue-Schluessel per Hover-Tooltip ablesen.", st))

    story.append(H3("Diagramm 2: Scatterplot (Verlauf ueber Zeit)", st))
    story.append(P(
        "Jeder Punkt ist ein abgeschlossenes Issue. Die X-Achse zeigt das Abschlussdatum, "
        "die Y-Achse die Durchlaufzeit in Tagen. Farben und Referenzlinien helfen bei "
        "der Einordnung:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Element", "Bedeutung"],
        [
            ["Blauer Punkt",   "Normale Issues (unterhalb des 85. Perzentils)"],
            ["Oranger Punkt",  "Langsame Issues (zwischen 85. und 95. Perzentil)"],
            ["Roter Punkt",    "Sehr langsame Issues (oberhalb des 95. Perzentils)"],
            ["Blaue Kurve",    "LOESS-Trendlinie -- zeigt den Trend der Durchlaufzeit ueber die Zeit"],
            ["Rote Linie",     "Median-Referenzlinie"],
            ["Gruene Linie",   "85. Perzentil-Referenzlinie"],
            ["Cyan-Linie",     "95. Perzentil-Referenzlinie"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Interpretation:</b> Steigt die LOESS-Trendlinie nach rechts an, werden "
        "Issues mit der Zeit langsamer. Eine flache Linie signalisiert einen stabilen "
        "Prozess. Viele rote und orange Punkte deuten auf haeufige Engpaesse hin.", st))

    # --- 5.2 Flow Velocity ---------------------------------------------------
    story.append(H2("5.2  Flow Velocity / Throughput", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Der Durchsatz -- also wie viele Issues das Team pro "
        "Woche oder pro PI abschliesst. Eine konstant hohe Velocity zeigt ein "
        "lieferfaehiges Team.", st))
    story.append(SP(4))
    story.append(tbl(
        ["Diagramm", "Zeigt"],
        [
            ["Tagesfrequenz (Histogramm)",
             "Wie oft kommt es vor, dass genau 1, 2, 3 ... Issues an einem Tag "
             "abgeschlossen werden. Zeigt typische Tagesleistungen."],
            ["Wochenverlauf (Linienchart)",
             "Anzahl der pro Woche abgeschlossenen Issues ueber den gesamten Zeitraum. "
             "Schwankungen und Trends werden sofort sichtbar."],
            ["PI-Verlauf (Balkendiagramm)",
             "Anzahl der abgeschlossenen Issues pro PI (Program Increment) oder Quartal. "
             "Die rote Linie zeigt den Durchschnitt. Balkenfarben: "
             "Grau = erster Balken; Orange = laufendes PI; Blau = abgeschlossene PIs; "
             "Hellgrau = zukuenftige PIs."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    # --- 5.3 Flow Load -------------------------------------------------------
    story.append(H2("5.3  Flow Load / WIP  (Work in Progress)", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Wie viele Issues sich gerade gleichzeitig in "
        "Bearbeitung befinden und wie alt sie bereits sind. Zu viele parallele Issues "
        "verlangsamen die Lieferung (je mehr WIP, desto laenger die Durchlaufzeit).", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm zeigt einen gruppierten Boxplot: jede Stage erhaelt eine Box, "
        "die das Alter (in Tagen) der aktuell dort befindlichen Issues zeigt. "
        "Einzelne Punkte stellen einzelne Issues dar -- im Browser sehen Sie den "
        "Issue-Schluessel beim Hover.", st))
    story.append(SP(4))
    story.append(P(
        "Gestrichelte Referenzlinien aus den abgeschlossenen Issues (Median, 85. "
        "Perzentil, 95. Perzentil) geben Orientierung: Issues, die bereits ueber dem "
        "95. Perzentil der abgeschlossenen Issues liegen, sind stark verzoegert.", st))

    # --- 5.4 CFD -------------------------------------------------------------
    story.append(H2("5.4  Cumulative Flow Diagram (CFD)", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Die Entwicklung des Gesamtbestands ueber Zeit, "
        "aufgeteilt nach Workflow-Stage. Ein gut funktionierendes System zeigt "
        "parallele, gleichmaessig steigende Baender ohne Aufblehungen in einzelnen "
        "Stages.", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm ist ein gestapeltes Flaechendiagramm: Jede farbige Schicht "
        "entspricht einer Stage. Die erste Stage liegt oben, die letzte (Done/Closed) "
        "unten. Zwei schwarze Trendlinien zeigen:", st))
    story.append(BL(
        "<b>Obere Linie (Zufluss):</b> Wie schnell waechst der Gesamtbestand?", st))
    story.append(BL(
        "<b>Untere Linie (Abfluss):</b> Wie schnell werden Issues abgeschlossen?", st))
    story.append(SP(4))
    story.append(P(
        "Das <b>In/Out-Verhaeltnis</b> im Diagrammtitel (z.B. 'Ratio In/out 1.80 : 1') "
        "zeigt, ob mehr eingeht als abgeschlossen wird. Ein Wert von 1.0 bedeutet "
        "ausgewogenes System; Werte deutlich ueber 1.0 bedeuten wachsendes Backlog.",
        st))
    story.append(SP(4))
    story.append(P(
        "Die X-Achse zeigt Monatsgrenzen mit grosser Beschriftung (z.B. 'Jan 2025') "
        "und ISO-Kalenderwochen mit kleiner grauer Beschriftung (z.B. 'W03'), damit "
        "die Labels nicht ueberlappen.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Hinweis:</b> Das CFD benoetigt die optionale CFD.xlsx-Datei. Ohne diese "
        "Datei kann die CFD-Metrik nicht berechnet werden.", st, "#fff8e1"))

    # --- 5.5 Flow Distribution -----------------------------------------------
    story.append(H2("5.5  Flow Distribution", st))
    story.append(P(
        "<b>Was wird gemessen?</b> Die Zusammensetzung aller Issues nach Typ (z.B. "
        "Feature, Bug, Story) und nach aktuellem Status. Zeigt auf einen Blick, "
        "welche Issue-Arten dominieren und wie der Bestand ueber die Status verteilt "
        "ist.", st))
    story.append(SP(4))
    story.append(P(
        "Das Diagramm besteht aus zwei Donut-Diagrammen nebeneinander: links nach "
        "Issuetyp, rechts nach Status. Jede Kategorie zeigt Anzahl und prozentualen "
        "Anteil.", st))

    # =========================================================================
    # 6. PDF-Export
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("6  PDF-Export", st))
    story.append(P(
        "Der PDF-Export erzeugt eine mehrseitige PDF-Datei mit allen ausgewaehlten "
        "Diagrammen. Jedes Diagramm erscheint auf einer eigenen Seite.", st))
    story.append(SP(6))
    story.append(tbl(
        ["Schritt", "Aktion"],
        [
            ["1", "Dateien laden und Filter setzen (wie in Kapitel 4 beschrieben)."],
            ["2", "Gewuenschte Metriken per Checkbox auswaehlen."],
            ["3", "Auf 'Reports exportieren' klicken."],
            ["4", "Im Speicherdialog Dateiname und Speicherort waehlen und bestaetigen."],
            ["5", "Das Programm rechnet und exportiert; der Fortschritt erscheint im Log."],
            ["6", "Nach Abschluss stehen PDF und Report-Excel am gewaehlten Speicherort bereit."],
        ],
        col_widths=[1.5*cm, 14.5*cm]))
    story.append(SP(8))
    story.append(H2("6.1  Automatische Report-Excel", st))
    story.append(P(
        "Bei jedem PDF-Export wird automatisch eine Excel-Datei mit dem gleichen Namen "
        "erzeugt (z.B. report.xlsx neben report.pdf). Diese Datei enthaelt alle "
        "gefilterten Issues im IssueTimes-Format, ergaenzt um drei Spalten:", st))
    story.append(SP(4))
    story.append(tbl(
        ["Spalte", "Inhalt"],
        [
            ["Status Group",
             "Statusgruppe des Issues: 'To Do' (noch nicht gestartet), "
             "'In Progress' (in Bearbeitung) oder 'Done' (abgeschlossen). "
             "Abgeleitet aus First Date und Closed Date."],
            ["Cycle Time (First->Closed)",
             "Durchlaufzeit in Kalendertagen von First Date bis Closed Date "
             "(Methode A). Leer, wenn eines der Daten fehlt."],
            ["Cycle Time B (days in Status)",
             "Summe der Minuten in allen Workflow-Stages ausser der letzten, "
             "dividiert durch 1440 (Methode B). Leer, wenn eines der Daten fehlt."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(SP(8))
    story.append(box(
        "<b>Zero-Day Issues:</b> Zwei Mechanismen greifen unabhaengig voneinander:<br/>"
        "1. <b>Ausschluss-Filter (vor der Berechnung):</b> Ist die Checkbox "
        "'Zero-Day-Issues ausschliessen' aktiv, werden Issues mit einer Durchlaufzeit "
        "unterhalb des eingestellten Schwellwerts (Standard: 5 Minuten) komplett aus "
        "allen Metriken entfernt.<br/>"
        "2. <b>Innerhalb der Flow-Time-Metrik:</b> Issues mit einer Durchlaufzeit von "
        "0 Tagen (gleicher Kalendertag) werden separat ausgewiesen und nicht in die "
        "Statistik eingerechnet.<br/>"
        "In beiden Faellen wird eine separate Excel-Datei erstellt "
        "(z.B. report_zero_day_issues.xlsx im gleichen Ordner).", st,
        "#fff8e1"))

    # =========================================================================
    # 7. FAQ
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("7  Haeufige Fragen und Tipps", st))

    faqs = [
        (
            "Die Diagramme erscheinen nicht im Browser.",
            "Pruefen Sie, ob ein Standard-Browser eingestellt ist. Versuchen Sie "
            "alternativ den PDF-Export. Stellen Sie sicher, dass die IssueTimes-Datei "
            "korrekt geladen wurde (Log kontrollieren)."
        ),
        (
            "Der PDF-Export dauert sehr lange oder schlaegt fehl.",
            "Das Rendern der Diagramme als PDF benoetigt das Kaleido-Paket. Falls dies "
            "noch nicht eingerichtet wurde, wenden Sie sich an Ihren technischen "
            "Ansprechpartner."
        ),
        (
            "Im Log erscheint 'Stage nur in IssueTimes' oder 'Stage nur in CFD'.",
            "Die Stage-Spalten in IssueTimes.xlsx und CFD.xlsx stimmen nicht ueberein. "
            "Dies ist ein Hinweis, der die Auswertung nicht abbricht, aber darauf "
            "hindeutet, dass die Dateien aus unterschiedlichen Workflow-Versionen stammen."
        ),
        (
            "Wie kann ich nur ein bestimmtes Projekt auswerten?",
            "Geben Sie im Feld 'Projekte' den gewuenschten Projektschluessel ein "
            "(z.B. ARTA). Mehrere Projekte mit Komma trennen. Alternativ: Auswahl-Button "
            "fuer eine Liste aller verfuegbaren Projekte."
        ),
        (
            "Das Cumulative Flow Diagram erscheint nicht.",
            "Die CFD-Metrik benoetigt eine CFD.xlsx-Datei. Laden Sie diese im Feld "
            "'CFD (optional)'."
        ),
        (
            "Was ist der Unterschied zwischen PI-Intervallen und Quartalen?",
            "Standardmaessig werden Kalenderquartale (Q1-Q4) als Zeitabschnitte "
            "verwendet. Mit einer PI-Konfigurationsdatei koennen Sie eigene Zeitintervalle "
            "definieren, die Ihren tatsaechlichen PIs entsprechen -- zum Beispiel wenn "
            "Ihr PI am 6. Januar beginnt statt am 1. Januar."
        ),
        (
            "Wie sichere ich meine Einstellungen?",
            "Nutzen Sie das Menue 'Templates' -> 'Speichern...', um alle aktuellen "
            "Einstellungen in einer JSON-Datei zu sichern. Beim naechsten Mal: "
            "'Templates' -> 'Laden...'. Ausschluss-Einstellungen koennen zusaetzlich "
            "dauerhaft unter 'Templates' -> 'Ausschluesse als Standard speichern' "
            "hinterlegt werden."
        ),
        (
            "Ein Issue erscheint in den Metriken, obwohl es nie wirklich bearbeitet wurde.",
            "Das kommt vor, wenn ein Issue manuell innerhalb von Sekunden durch alle "
            "Workflow-Stages geklickt wurde -- ohne echte Entwicklungsarbeit. Aktivieren "
            "Sie in der GUI unter 'Ausschluesse' die Checkbox 'Zero-Day-Issues "
            "ausschliessen' (Schwellwert z.B. 5 Minuten). Das Issue wird dann komplett "
            "aus allen Metriken entfernt und in einer separaten Excel-Datei dokumentiert."
        ),
        (
            "Kann ich die Ergebnisse auch ohne Computer vorfahren?",
            "Ja: Exportieren Sie zunaechst einen PDF-Bericht. Die PDF-Datei enthaelt "
            "alle Diagramme und kann auf jedem Geraet geoeffnet werden. Fuer interaktive "
            "Praesentationen empfiehlt sich die Browser-Anzeige."
        ),
    ]
    for q, a in faqs:
        story.append(H3("F: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    # =========================================================================
    # 8. Glossar
    # =========================================================================
    story.append(PageBreak())
    story.append(H1("8  Glossar", st))
    story.append(tbl(
        ["Begriff", "Erklaerung"],
        [
            ["Closed Date",    "Das Datum, an dem ein Issue abgeschlossen wurde."],
            ["Cycle Time",     "Andere Bezeichnung fuer Flow Time (Global-Terminologie)."],
            ["First Date",     "Datum der ersten aktiven Bearbeitung eines Issues."],
            ["Flow Load",      "Anzahl der aktuell in Bearbeitung befindlichen Issues (SAFe-Term)."],
            ["Flow Time",      "Durchlaufzeit von der ersten Bearbeitung bis zum Abschluss."],
            ["Flow Velocity",  "Anzahl abgeschlossener Issues pro Zeitraum (SAFe-Term)."],
            ["Issue",          "Ein Ticket im Ticketsystem (z.B. eine Jira-Karte)."],
            ["Issuetyp",       "Kategorie eines Issues, z.B. Feature, Bug, Story, Task."],
            ["IssueTimes",     "Die von transform_data erzeugte Excel-Datei mit allen Issues."],
            ["JSON",           "Einfaches Textformat fuer Konfigurationsdateien."],
            ["LOESS",          "Statistisches Glaettungsverfahren fuer Trendlinien."],
            ["P85 / P95",      "85. bzw. 95. Perzentil der Durchlaufzeiten."],
            ["PI",             "Program Increment -- ein fester Planungs- und Lieferzeitraum."],
            ["Resolution",     "Abschlussart eines Issues, z.B. 'Done', 'Won't Do', 'Duplicate'."],
            ["SAFe",           "Scaled Agile Framework -- ein Framework fuer agile Skalierung."],
            ["Stage",          "Ein Schritt im Workflow, z.B. Analyse, Implementierung, Done."],
            ["Template",       "Gespeicherte Konfigurationsdatei mit allen Einstellungen."],
            ["Throughput",     "Andere Bezeichnung fuer Flow Velocity (Global-Terminologie)."],
            ["WIP",            "Work in Progress -- Issues, die aktuell in Bearbeitung sind."],
            ["Zero-Day Issue", "Issue, dessen Durchlaufzeit (First bis Closed Date) so kurz "
                               "ist, dass es keine echte Bearbeitungszeit repraesentiert. "
                               "Entsteht meist durch manuelles Durchklicken im Workflow. "
                               "Kann per Schwellwert-Filter aus allen Metriken entfernt werden."],
        ],
        col_widths=[4*cm, 12*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st = make_styles()
    doc = ManualDoc(
        str(OUTPUT),
        title="build_reports Benutzerhandbuch",
        author="Robert Seebauer",
        subject="Flow-Metriken fuer agile Teams",
    )

    story = [
        Spacer(1, 1),             # fills the cover frame (drawn by build_cover)
        NextPageTemplate("normal"),
    ]
    story_content, toc = content(st)
    story.extend(story_content)

    doc.multiBuild(story)
    print("PDF erstellt: %s" % OUTPUT)


if __name__ == "__main__":
    main()
