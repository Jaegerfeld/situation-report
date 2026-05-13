# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       21.04.2026
# Geaendert:      13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer transform_data als PDF in allen 5 Sprachen:
#   Deutsch, Englisch, Rumaenisch, Portugiesisch, Franzoesisch.
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
OUTPUT_RO = Path(__file__).parent / "transform_data_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "transform_data_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "transform_data_ManuelUtilisateur.pdf"

_HEADER = {
    "de": "transform_data -- Benutzerhandbuch",
    "en": "transform_data -- User Manual",
    "ro": "transform_data -- Manual de Utilizator",
    "pt": "transform_data -- Manual do Utilizador",
    "fr": "transform_data -- Manuel d'utilisation",
}
_PAGE_LABEL = {
    "de": "Seite %d",
    "en": "Page %d",
    "ro": "Pagina %d",
    "pt": "Pagina %d",
    "fr": "Page %d",
}
_COVER_TITLE2 = {
    "de": "Benutzerhandbuch",
    "en": "User Manual",
    "ro": "Manual de Utilizator",
    "pt": "Manual do Utilizador",
    "fr": "Manuel d'utilisation",
}
_COVER_SUBTITLE = {
    "de": "Jira-Daten aufbereiten fuer Metriken und Berichte",
    "en": "Prepare Jira data for metrics and reports",
    "ro": "Pregatiti datele Jira pentru metrici si rapoarte",
    "pt": "Preparar dados Jira para metricas e relatorios",
    "fr": "Preparer les donnees Jira pour les metriques et rapports",
}
_COVER_AUDIENCE = {
    "de": "Fuer nicht-technische Anwender",
    "en": "For non-technical users",
    "ro": "Pentru utilizatori non-tehnici",
    "pt": "Para utilizadores nao tecnicos",
    "fr": "Pour les utilisateurs non techniques",
}


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
        canvas.drawString(2.2*cm, h - 0.7*cm, _HEADER[self._lang])
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(w/2, 1.0*cm, _PAGE_LABEL[self._lang] % doc.page)
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
    canvas.drawCentredString(w/2, h*0.545, _COVER_TITLE2[lang])
    canvas.setFont("Helvetica", 12)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.49, _COVER_SUBTITLE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.455, w*0.8, h*0.455)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report - github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09,
                             f"{_COVER_AUDIENCE[lang]} -- Version {_VERSION}")
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


def _make_toc(lang):
    toc = TableOfContents()
    sfx = lang
    toc.levelStyles = [
        ParagraphStyle(f"TOCH1_{sfx}", fontName="Helvetica-Bold", fontSize=11,
                       leading=18, leftIndent=0, spaceAfter=2),
        ParagraphStyle(f"TOCH2_{sfx}", fontName="Helvetica", fontSize=9,
                       leading=15, leftIndent=16, spaceAfter=1),
        ParagraphStyle(f"TOCH3_{sfx}", fontName="Helvetica-Oblique", fontSize=8,
                       leading=13, leftIndent=28, spaceAfter=1),
    ]
    return toc


# ---------------------------------------------------------------------------
# Content — German
# ---------------------------------------------------------------------------

def content_de(st):
    story = []
    story.append(PageBreak())
    story.append(H1("Inhalt", st))
    toc = _make_toc("de")
    story.append(toc)

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

    story.append(PageBreak())
    story.append(H1("2  Voraussetzungen und Installation", st))
    story.append(H2("2.1  Was muss installiert sein?", st))
    story.append(P(
        "transform_data wird als <b>portables Paket</b> geliefert. Eine separate "
        "Python-Installation ist nicht notwendig.", st))
    story.append(BL("<b>Windows:</b> Python ist bereits im Paket enthalten -- einfach entpacken und starten.", st))
    story.append(BL(
        "<b>macOS / Linux:</b> Beim ersten Start wird einmalig eine Python-Umgebung "
        "eingerichtet (ca. 1 Minute, Internet erforderlich). Danach laeuft die App offline.", st))
    story.append(H2("2.2  Programm starten", st))
    story.append(BL("<b>Windows:</b> <b>TransformData.bat</b> doppelklicken.", st))
    story.append(BL("<b>macOS:</b> Rechtsklick auf <b>TransformData.command</b> → <i>Oeffnen</i>.", st))
    story.append(BL("<b>Linux:</b> Im Terminal: <font name='Courier'>./TransformData.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp (Windows):</b> Beim ersten Start erscheint moeglicherweise ein "
        "SmartScreen-Hinweis. Auf <b>Weitere Informationen</b> → "
        "<b>Trotzdem ausfuehren</b> klicken.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("3  Eingabedateien", st))
    story.append(P(
        "transform_data benoetigt genau zwei Dateien: den Jira-JSON-Export und die "
        "Workflow-Definitionsdatei. Beide werden in der GUI per Datei-Dialog ausgewaehlt.", st))
    story.append(H2("3.1  Jira-JSON-Export", st))
    story.append(P(
        "Dies ist ein Export aller Issues eines Jira-Projekts im JSON-Format. "
        "Er enthaelt fuer jedes Ticket die komplette Statushistorie (Changelog), "
        "Metadaten wie Issuetyp, Komponenten und Erstellungsdatum sowie den aktuellen Status.", st))
    story.append(P(
        "Wie der Export aus Jira erzeugt wird, beschreibt das Modul <b>get_data</b>. "
        "Die JSON-Datei sollte nicht manuell bearbeitet werden.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typischer Dateiname:</b> ART_A.json, MYPROJECT.json o.ae.<br/>"
        "<b>Groesse:</b> Abhaengig von der Anzahl der Issues; haeufig einige MB.", st, "#fff8e1"))
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

    story.append(PageBreak())
    story.append(H1("4  Die Workflow-Definitionsdatei", st))
    story.append(P(
        "Die Workflow-Datei steuert, wie transform_data die Jira-Status Ihres Projekts "
        "interpretiert. Sie muessen diese Datei in der Regel nicht selbst erstellen -- "
        "dieses Kapitel erklaert jedoch ihren Aufbau.", st))
    story.append(H2("4.1  Aufbau", st))
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
            ["Stage:Alias1:Alias2", "Stage mit Jira-Statusnamen. Der erste Name ist der kanonische Stage-Name."],
            ["<First>Stage", "Diese Stage markiert den Beginn der aktiven Bearbeitung (First Date)."],
            ["<InProgress>Stage", "Diese Stage setzt das Implementation Date."],
            ["<Closed>Stage", "Diese Stage markiert den Abschluss (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Reihenfolge der Stages", st))
    story.append(P(
        "Die Stages werden in der Reihenfolge aufgefuehrt, in der sie im Prozess "
        "durchlaufen werden. Diese Reihenfolge wird fuer das CFD und fuer die "
        "Berechnung des Closed Date bei uebersprungenen Stages verwendet.", st))
    story.append(H2("4.3  Nicht gemappte Jira-Status", st))
    story.append(P(
        "Enthaelt der Jira-Export Status, die in der Workflow-Datei nicht definiert sind, "
        "gibt transform_data eine Warnung aus. Die Zeit wird der letzten bekannten Stage "
        "zugerechnet (Carry-forward).", st))

    story.append(PageBreak())
    story.append(H1("5  Die grafische Oberflaeche (GUI)", st))
    story.append(P(
        "Nach dem Start oeffnet sich ein Fenster mit Datei-Auswahl-Feldern, "
        "Optionen und einem Log-Bereich fuer Statusmeldungen.", st))
    story.append(H2("5.1  Dateien auswaehlen", st))
    story.append(BL(
        "<b>JSON-Datei</b> - Klicken Sie auf 'Durchsuchen' und waehlen Sie Ihren "
        "Jira-Export aus. Ausgabeordner und Praefix werden automatisch vorbelegt.", st))
    story.append(BL(
        "<b>Workflow-Datei</b> - Waehlen Sie die passende .txt-Workflow-Datei fuer Ihr Projekt aus.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tipp:</b> Wenn Sie die JSON-Datei zuerst auswaehlen, werden Ausgabeordner "
        "und Praefix automatisch vorausgefuellt.", st, "#e8f8f0"))
    story.append(H2("5.2  Ausgabe konfigurieren", st))
    story.append(tbl(
        ["Feld", "Bedeutung"],
        [
            ["Ausgabeordner", "Verzeichnis fuer die drei Excel-Dateien. Standard: Verzeichnis der JSON-Datei."],
            ["Praefix", "Namens-Praefix. Aus 'ART_A' werden ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx und ART_A_CFD.xlsx."],
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
        "Unter <b>Hilfe &rarr; Manual</b> oeffnet sich dieses Handbuch im Browser.", st))

    story.append(PageBreak())
    story.append(H1("6  Die Ausgabedateien", st))
    story.append(P(
        "transform_data erzeugt drei Excel-Dateien. Diese Dateien dienen als "
        "Eingabe fuer build_reports und sollten nicht manuell bearbeitet werden.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
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
        "die jeweilige Stage eingetreten sind. build_reports erzeugt daraus das "
        "Cumulative Flow Diagram.", st))

    story.append(PageBreak())
    story.append(H1("7  Wie werden Datum und Zeiten berechnet?", st))
    story.append(H2("7.1  Stage-Zeiten", st))
    story.append(tbl(
        ["Situation", "Regel"],
        [
            ["Issue erstellt, aber noch kein Statuswechsel",
             "Die Zeit von der Erstellung bis zum ersten Statuswechsel wird der initialen Stage zugerechnet."],
            ["Statuswechsel zu einer nicht gemappten Stage",
             "Die Zeit laeuft in der letzten bekannten Stage weiter (Carry-forward)."],
            ["Aktueller Status",
             "Die letzte bekannte Stage akkumuliert Zeit bis zum Zeitpunkt der Verarbeitung."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "Das First Date wird gesetzt, sobald ein Issue zum ersten Mal in die mit "
        "<b>&lt;First&gt;</b> markierte Stage wechselt.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Uebersprungene First-Stage:</b> Betritt ein Issue eine Stage nach der "
        "&lt;First&gt;-Stage direkt, wird der Eintrittszeitpunkt als First Date verwendet.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "Das Closed Date wird beim Eintritt in die mit <b>&lt;Closed&gt;</b> markierte "
        "Stage gesetzt. Bei mehrfach geoeffneten Issues zaehlt der <b>letzte</b> Schliessungszeitpunkt.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Wiedergeoeffnete Issues:</b> Befindet sich ein Issue in einer Stage vor "
        "&lt;Closed&gt;, wird kein Closed Date gesetzt.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Nie bearbeitete Issues:</b> Issues ohne First Date erhalten kein Closed Date "
        "und zaehlen nicht in der Flow Velocity.", st, "#e8eaf6"))

    story.append(PageBreak())
    story.append(H1("8  Haeufige Fragen und Tipps", st))
    faqs = [
        ("Ein Issue hat kein First Date -- warum?",
         "Das Issue hat weder die <First>-Stage noch eine Stage danach erreicht. "
         "In build_reports wird es als 'To Do' gezaehlt."),
        ("Ein Issue hat kein Closed Date -- warum?",
         "Moegliche Gruende: (1) Das Issue ist noch offen. (2) Es hat kein First Date. "
         "(3) Es wurde nach dem Abschluss wieder geoeffnet."),
        ("Im Log erscheint eine Warnung ueber nicht gemappte Status.",
         "Einige Jira-Status sind nicht in der Workflow-Datei definiert. "
         "Die Verarbeitung wird trotzdem abgeschlossen."),
        ("Die Ausgabedateien werden nicht erstellt.",
         "Pruefen Sie, ob der Ausgabeordner existiert und ob Sie Schreibrechte haben. "
         "Stellen Sie sicher, dass die Dateien nicht in Excel geoeffnet sind."),
        ("Welche Datei verwende ich fuer build_reports?",
         "IssueTimes.xlsx ist die Pflichtdatei fuer alle Metriken. "
         "CFD.xlsx benoetigen Sie zusaetzlich fuer das Cumulative Flow Diagram."),
        ("Wie oft muss ich transform_data ausfuehren?",
         "Immer dann, wenn Sie aktualisierte Daten aus Jira benoetigen."),
        ("Was bedeutet 'Carry-forward'?",
         "Zeit in einem nicht gemappten Status wird der letzten bekannten Stage zugerechnet."),
    ]
    for q, a in faqs:
        story.append(H3("F: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    story.append(PageBreak())
    story.append(H1("9  Glossar", st))
    story.append(tbl(
        ["Begriff", "Erklaerung"],
        [
            ["Carry-forward", "Zeit in einem nicht gemappten Status wird der letzten bekannten Stage zugerechnet."],
            ["CFD", "Cumulative Flow Diagram -- zeigt die Entwicklung des Bestands nach Stages."],
            ["Closed Date", "Datum des Abschlusses eines Issues."],
            ["First Date", "Datum der ersten aktiven Bearbeitung."],
            ["Implementation Date", "Datum des Entwicklungsbeginns."],
            ["Issue", "Ein Ticket im Ticketsystem (z.B. eine Jira-Karte)."],
            ["JSON", "Einfaches Textformat fuer strukturierte Daten."],
            ["Marker", "Zeilen in der Workflow-Datei, die eine Stage als Meilenstein auszeichnen: <First>, <InProgress>, <Closed>."],
            ["Praefix", "Namens-Vorsatz fuer die Ausgabedateien (z.B. 'ART_A')."],
            ["Stage", "Ein logischer Prozessschritt, dem ein oder mehrere Jira-Status zugeordnet sind."],
            ["Workflow-Datei", "Textdatei, die die Stages und Marker eines Projekts beschreibt."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content — English
# ---------------------------------------------------------------------------

def content_en(st):
    story = []
    story.append(PageBreak())
    story.append(H1("Contents", st))
    toc = _make_toc("en")
    story.append(toc)

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
        "- <b>IssueTimes.xlsx</b>: All issues with milestone timestamps and minutes per workflow stage.<br/>"
        "- <b>Transitions.xlsx</b>: Complete status history of all issues.<br/>"
        "- <b>CFD.xlsx</b>: Daily entry counts per stage for the Cumulative Flow Diagram.", st))
    story.append(SP(8))
    story.append(P(
        "The generated Excel files are then used by the <b>build_reports</b> module "
        "to create charts and reports.", st))

    story.append(PageBreak())
    story.append(H1("2  Prerequisites and Installation", st))
    story.append(H2("2.1  What needs to be installed?", st))
    story.append(P("transform_data is delivered as a <b>portable package</b>. No separate Python installation is required.", st))
    story.append(BL("<b>Windows:</b> Python is already included in the package — just unzip and run.", st))
    story.append(BL("<b>macOS / Linux:</b> On the first launch, a Python environment is set up automatically (approx. 1 minute, internet required).", st))
    story.append(H2("2.2  Starting the program", st))
    story.append(BL("<b>Windows:</b> Double-click <b>TransformData.bat</b>.", st))
    story.append(BL("<b>macOS:</b> Right-click <b>TransformData.command</b> → <i>Open</i> (once, to bypass Gatekeeper).", st))
    story.append(BL("<b>Linux:</b> In a terminal: <font name='Courier'>./TransformData.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Tip (Windows):</b> On the first launch, SmartScreen may show a warning. "
        "Click <b>More info</b> → <b>Run anyway</b>.", st, "#e8f8f0"))

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
    story.append(P("How to generate the export from Jira is described in the <b>get_data</b> module. "
                   "The JSON file should not be edited manually.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typical filename:</b> ART_A.json, MYPROJECT.json, etc.<br/>"
        "<b>Size:</b> Depends on the number of issues; often several MB.", st, "#fff8e1"))
    story.append(H2("3.2  Workflow Definition File", st))
    story.append(P(
        "The workflow file is a plain text file (.txt) that describes how the Jira "
        "statuses in your project map to logical process steps (stages). It also "
        "defines which stage marks the start of active work (First Date) and completion (Closed Date).", st))
    story.append(SP(4))
    story.append(box(
        "<b>Typical filename:</b> workflow_ART_A.txt, etc.<br/>"
        "<b>Created by:</b> Your technical contact or Scrum Master -- once per project, rarely changed.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("4  The Workflow Definition File", st))
    story.append(P(
        "The workflow file controls how transform_data interprets the Jira statuses "
        "in your project. You usually do not need to create this file yourself -- "
        "this chapter explains its structure so you can read and adjust it if needed.", st))
    story.append(H2("4.1  Structure", st))
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
            ["Stage:Alias1:Alias2", "Stage with Jira status names mapped to it. The first name is the canonical stage name."],
            ["<First>Stage", "This stage marks the start of active work (First Date)."],
            ["<InProgress>Stage", "This stage sets the Implementation Date."],
            ["<Closed>Stage", "This stage marks completion (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Stage order", st))
    story.append(P(
        "Stages are listed in the order they are traversed in the process. "
        "This order is used for the CFD and for computing the Closed Date when stages are skipped.", st))
    story.append(H2("4.3  Unmapped Jira statuses", st))
    story.append(P(
        "If the Jira export contains statuses not defined in the workflow file, "
        "transform_data issues a warning. Time in unmapped statuses is attributed "
        "to the last known stage (carry-forward).", st))

    story.append(PageBreak())
    story.append(H1("5  The Graphical User Interface (GUI)", st))
    story.append(P("After starting, a window opens with file selection fields, options, and a log area.", st))
    story.append(H2("5.1  Selecting files", st))
    story.append(BL("<b>JSON File</b> - Click 'Browse' and select your Jira export. Output folder and prefix are filled in automatically.", st))
    story.append(BL("<b>Workflow File</b> - Select the appropriate .txt workflow file for your project.", st))
    story.append(SP(4))
    story.append(box("<b>Tip:</b> If you select the JSON file first, the output folder and prefix are pre-filled automatically.", st, "#e8f8f0"))
    story.append(H2("5.2  Configuring output", st))
    story.append(tbl(
        ["Field", "Meaning"],
        [
            ["Output Folder", "Directory where the three Excel files are saved. Default: directory of the JSON file."],
            ["Prefix", "Name prefix for output files. 'ART_A' produces ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx, and ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Starting the transformation", st))
    story.append(P(
        "Click <b>'Run'</b>. The program reads the data, computes all values, "
        "and saves the three Excel files. Progress and any warnings appear in the log area.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Warnings in the log:</b> A warning about unmapped statuses does not mean "
        "the transformation failed -- the output files are still produced.", st, "#fff8e1"))
    story.append(H2("5.4  Language and Help", st))
    story.append(P(
        "Use the <b>Options</b> menu to switch between German and English. "
        "Under <b>Help &rarr; Manual</b>, this manual opens in your browser.", st))

    story.append(PageBreak())
    story.append(H1("6  Output Files", st))
    story.append(P("transform_data produces three Excel files used as input for build_reports.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
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
    story.append(P("Contains the complete status history of all issues -- one entry per status change.", st))
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
        "Contains, for each calendar day, the number of issues that entered each stage on that day. "
        "build_reports accumulates these values to produce the Cumulative Flow Diagram.", st))

    story.append(PageBreak())
    story.append(H1("7  How are Dates and Times Calculated?", st))
    story.append(H2("7.1  Stage times", st))
    story.append(tbl(
        ["Situation", "Rule"],
        [
            ["Issue created but no status change yet",
             "Time from creation to the first status change is attributed to the initial stage."],
            ["Status change to an unmapped stage",
             "Time continues in the last known stage (carry-forward). No time is lost."],
            ["Current status",
             "The last known stage accumulates time until processing time."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "The First Date is set when an issue first enters the stage marked "
        "<b>&lt;First&gt;</b>. It represents the start of active work.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Skipped First stage:</b> If an issue enters a stage after &lt;First&gt; "
        "without entering it directly, that entry timestamp is used as the First Date.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "The Closed Date is set when an issue enters the stage marked <b>&lt;Closed&gt;</b>. "
        "If closed and re-opened multiple times, the <b>last</b> closing timestamp is used.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Re-opened issues:</b> If an issue is currently before &lt;Closed&gt;, "
        "no Closed Date is set.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Never-worked issues:</b> Issues without a First Date receive no Closed Date "
        "and are not counted in Flow Velocity.", st, "#e8eaf6"))

    story.append(PageBreak())
    story.append(H1("8  Frequently Asked Questions", st))
    faqs = [
        ("An issue has no First Date -- why?",
         "The issue never reached the <First> stage or any stage after it. In build_reports it is counted as 'To Do'."),
        ("An issue has no Closed Date -- why?",
         "Possible reasons: (1) The issue is still open. (2) It has no First Date. (3) It was re-opened after closing."),
        ("The log shows a warning about unmapped statuses.",
         "Some Jira statuses are not defined in the workflow file. Processing still completes."),
        ("The output files are not created.",
         "Check that the output folder exists and you have write permissions. Make sure the files are not open in Excel."),
        ("Which file do I use for build_reports?",
         "IssueTimes.xlsx is required for all metrics. CFD.xlsx is additionally needed for the Cumulative Flow Diagram."),
        ("How often do I need to run transform_data?",
         "Whenever you need updated data from Jira."),
        ("What does 'carry-forward' mean?",
         "Time in an unmapped status is attributed to the last known stage -- no time is lost."),
    ]
    for q, a in faqs:
        story.append(H3("Q: " + q, st))
        story.append(P("A: " + a, st))
        story.append(SP(4))

    story.append(PageBreak())
    story.append(H1("9  Glossary", st))
    story.append(tbl(
        ["Term", "Explanation"],
        [
            ["Carry-forward", "Time in an unmapped status is attributed to the last known stage."],
            ["CFD", "Cumulative Flow Diagram -- shows backlog evolution over time by stage."],
            ["Closed Date", "The date an issue was completed."],
            ["First Date", "The date active work began on an issue."],
            ["Implementation Date", "The date development work started."],
            ["Issue", "A ticket in the issue tracker (e.g. a Jira card)."],
            ["JSON", "A simple text format for structured data."],
            ["Marker", "Lines in the workflow file that designate a stage as a milestone: <First>, <InProgress>, <Closed>."],
            ["Prefix", "Name prefix for output files (e.g. 'ART_A')."],
            ["Stage", "A logical process step mapped to one or more Jira statuses."],
            ["Workflow file", "Text file describing the stages and markers of a project."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content — Romanian
# ---------------------------------------------------------------------------

def content_ro(st):
    story = []
    story.append(PageBreak())
    story.append(H1("Cuprins", st))
    toc = _make_toc("ro")
    story.append(toc)

    story.append(PageBreak())
    story.append(H1("1  Ce este transform_data?", st))
    story.append(P(
        "transform_data este primul modul din lantul de instrumente situation-report. "
        "Citeste un export de date brute din sistemul dvs. de tickete (Jira) si "
        "pregateste datele pentru analiza ulterioara. Rezultatul sunt trei "
        "<b>fisiere Excel</b> care arata cat timp au petrecut issue-urile in "
        "fiecare etapa a fluxului de lucru.", st))
    story.append(P(
        "Programul are o interfata grafica simpla (GUI): nu sunt necesare cunostinte "
        "de programare. Selectati doua fisiere, faceti clic pe 'Executare' si "
        "fisierele Excel sunt generate automat.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Ce produce transform_data:</b><br/>"
        "- <b>IssueTimes.xlsx</b>: Toate issue-urile cu marcajele de timp si minutele per etapa.<br/>"
        "- <b>Transitions.xlsx</b>: Istoricul complet al statusurilor pentru toate issue-urile.<br/>"
        "- <b>CFD.xlsx</b>: Numarul zilnic de intrari pe etapa pentru Diagrama de Flux Cumulativ.", st))
    story.append(SP(8))
    story.append(P(
        "Fisierele Excel generate sunt utilizate de modulul <b>build_reports</b> "
        "pentru a crea diagrame si rapoarte.", st))

    story.append(PageBreak())
    story.append(H1("2  Cerinte si instalare", st))
    story.append(H2("2.1  Ce trebuie instalat?", st))
    story.append(P("transform_data este livrat ca <b>pachet portabil</b>. Nu este necesara o instalare separata Python.", st))
    story.append(BL("<b>Windows:</b> Python este deja inclus in pachet -- dezarhivati si porniti.", st))
    story.append(BL("<b>macOS / Linux:</b> La prima pornire, un mediu Python este configurat automat (aprox. 1 minut, internet necesar).", st))
    story.append(H2("2.2  Pornirea programului", st))
    story.append(BL("<b>Windows:</b> Dublu-clic pe <b>TransformData.bat</b>.", st))
    story.append(BL("<b>macOS:</b> Clic dreapta pe <b>TransformData.command</b> → <i>Deschidere</i>.", st))
    story.append(BL("<b>Linux:</b> In terminal: <font name='Courier'>./TransformData.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Sfat (Windows):</b> La prima pornire, SmartScreen poate afisa un avertisment. "
        "Faceti clic pe <b>Mai multe informatii</b> → <b>Rulare oricum</b>.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("3  Fisiere de intrare", st))
    story.append(P(
        "transform_data necesita exact doua fisiere: exportul JSON din Jira si "
        "fisierul de definitie a fluxului de lucru. Ambele se selecteaza in GUI.", st))
    story.append(H2("3.1  Exportul JSON din Jira", st))
    story.append(P(
        "Acesta este un export al tuturor issue-urilor dintr-un proiect Jira in format JSON. "
        "Contine istoricul complet al statusurilor (changelog), metadate si statusul curent.", st))
    story.append(P("Cum se genereaza exportul din Jira este descris in modulul <b>get_data</b>.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nume tipic:</b> ART_A.json, MYPROJECT.json etc.<br/>"
        "<b>Dimensiune:</b> Depinde de numarul de issue-uri; adesea cativa MB.", st, "#fff8e1"))
    story.append(H2("3.2  Fisierul de definitie a fluxului", st))
    story.append(P(
        "Fisierul de flux este un fisier text simplu (.txt) care descrie cum statusurile "
        "Jira din proiectul dvs. sunt mapate la etape logice ale procesului. "
        "Defineste si care etapa marcheaza inceputul lucrului activ si inchiderea.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nume tipic:</b> workflow_ART_A.txt etc.<br/>"
        "<b>Creat de:</b> Contactul tehnic sau Scrum Master -- o data per proiect, rar modificat.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("4  Fisierul de definitie a fluxului", st))
    story.append(P(
        "Fisierul de flux controleaza modul in care transform_data interpreteaza "
        "statusurile Jira. De obicei nu trebuie sa il creati dvs.", st))
    story.append(H2("4.1  Structura", st))
    story.append(P("<b>Exemplu:</b>", st))
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
        ["Format", "Semnificatie"],
        [
            ["Etapa:Alias1:Alias2", "Etapa cu statusurile Jira mapate. Primul nume este numele canonic al etapei."],
            ["<First>Etapa", "Aceasta etapa marcheaza inceputul lucrului activ (First Date)."],
            ["<InProgress>Etapa", "Aceasta etapa seteaza Implementation Date."],
            ["<Closed>Etapa", "Aceasta etapa marcheaza finalizarea (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Ordinea etapelor", st))
    story.append(P(
        "Etapele sunt listate in ordinea in care sunt parcurse in proces. "
        "Aceasta ordine este utilizata pentru CFD si pentru calculul Closed Date.", st))
    story.append(H2("4.3  Statusuri nemapate", st))
    story.append(P(
        "Daca exportul Jira contine statusuri nedefinite in fisierul de flux, "
        "transform_data afiseaza un avertisment. Timpul este atribuit ultimei etape cunoscute.", st))

    story.append(PageBreak())
    story.append(H1("5  Interfata grafica (GUI)", st))
    story.append(P("Dupa pornire, se deschide o fereastra cu campuri de selectie fisiere si un jurnal de stare.", st))
    story.append(H2("5.1  Selectarea fisierelor", st))
    story.append(BL("<b>Fisier JSON</b> - Faceti clic pe 'Navigare' si selectati exportul Jira. Dosarul de iesire si prefixul sunt completate automat.", st))
    story.append(BL("<b>Fisier de flux</b> - Selectati fisierul .txt corespunzator proiectului dvs.", st))
    story.append(SP(4))
    story.append(box("<b>Sfat:</b> Daca selectati mai intai fisierul JSON, dosarul de iesire si prefixul sunt precompletate automat.", st, "#e8f8f0"))
    story.append(H2("5.2  Configurarea iesirii", st))
    story.append(tbl(
        ["Camp", "Semnificatie"],
        [
            ["Dosar de iesire", "Directorul in care sunt salvate cele trei fisiere Excel. Implicit: directorul fisierului JSON."],
            ["Prefix", "Prefixul numelui fisierelor. Din 'ART_A' rezulta ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx si ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Pornirea procesarii", st))
    story.append(P(
        "Faceti clic pe <b>'Executare'</b>. Programul citeste datele, calculeaza toate "
        "valorile si salveaza cele trei fisiere Excel. Progresul apare in jurnal.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Atentie la avertismente:</b> Un avertisment despre statusuri nemapate nu "
        "inseamna ca procesarea a esuat -- fisierele de iesire sunt totusi create.", st, "#fff8e1"))
    story.append(H2("5.4  Limba si ajutor", st))
    story.append(P(
        "Utilizati meniul <b>Optiuni</b> pentru a schimba limba. "
        "Sub <b>Ajutor &rarr; Manual</b>, acest manual se deschide in browser.", st))

    story.append(PageBreak())
    story.append(H1("6  Fisierele de iesire", st))
    story.append(P("transform_data produce trei fisiere Excel utilizate ca intrare pentru build_reports.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(tbl(
        ["Coloana", "Continut"],
        [
            ["Project",            "Cheia proiectului (ex. ART_A)"],
            ["Key",                "Cheia issue-ului (ex. ART_A-123)"],
            ["Issuetype",          "Tipul issue-ului (ex. Feature, Bug, Story)"],
            ["Status",             "Statusul curent Jira"],
            ["Created Date",       "Data crearii issue-ului in Jira"],
            ["First Date",         "Prima intrare in etapa <First>"],
            ["Implementation Date","Prima intrare in etapa <InProgress>"],
            ["Closed Date",        "Marca de timp a finalizarii (gol = inca deschis)"],
            ["Coloane etape",      "Cate o coloana per etapa: minute petrecute in acea etapa"],
            ["Resolution",         "Tipul inchiderii din Jira"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(H2("6.2  Transitions.xlsx", st))
    story.append(P("Contine istoricul complet al statusurilor -- o inregistrare per modificare de status.", st))
    story.append(tbl(
        ["Coloana", "Continut"],
        [
            ["Key",        "Cheia issue-ului"],
            ["Transition", "Numele etapei (sau 'Created' pentru marca de timp a crearii)"],
            ["Timestamp",  "Data si ora modificarii de status"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("6.3  CFD.xlsx", st))
    story.append(P(
        "Contine, pentru fiecare zi calendaristica, numarul de issue-uri care au "
        "intrat in fiecare etapa in acea zi. build_reports acumuleaza aceste valori "
        "pentru Diagrama de Flux Cumulativ.", st))

    story.append(PageBreak())
    story.append(H1("7  Cum se calculeaza datele si timpii?", st))
    story.append(H2("7.1  Timpii pe etape", st))
    story.append(tbl(
        ["Situatie", "Regula"],
        [
            ["Issue creat, dar fara modificare de status",
             "Timpul de la creare pana la prima modificare este atribuit etapei initiale."],
            ["Modificare de status catre o etapa nemapata",
             "Timpul continua in ultima etapa cunoscuta (carry-forward)."],
            ["Status curent",
             "Ultima etapa cunoscuta acumuleaza timp pana la momentul procesarii."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "First Date este setat cand un issue intra pentru prima data in etapa "
        "marcata cu <b>&lt;First&gt;</b>. Reprezinta inceputul lucrului activ.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Etapa First sarita:</b> Daca un issue intra intr-o etapa dupa &lt;First&gt; "
        "fara a o atinge direct, marca de timp a acelei etape este utilizata ca First Date.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "Closed Date este setat la intrarea in etapa marcata cu <b>&lt;Closed&gt;</b>. "
        "Daca un issue a fost inchis si redeschis de mai multe ori, se utilizeaza "
        "<b>ultima</b> marca de timp de inchidere.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Issue-uri redeschise:</b> Daca un issue se afla intr-o etapa inaintea "
        "&lt;Closed&gt;, nu se seteaza Closed Date.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Issue-uri niciodata lucrate:</b> Issue-urile fara First Date nu primesc "
        "Closed Date si nu sunt numarate in Flow Velocity.", st, "#e8eaf6"))

    story.append(PageBreak())
    story.append(H1("8  Intrebari frecvente si sfaturi", st))
    faqs = [
        ("Un issue nu are First Date -- de ce?",
         "Issue-ul nu a atins niciodata etapa <First> sau vreo etapa ulterioara. In build_reports este numarat ca 'To Do'."),
        ("Un issue nu are Closed Date -- de ce?",
         "Motive posibile: (1) Issue-ul este inca deschis. (2) Nu are First Date. (3) A fost redeschis dupa inchidere."),
        ("Jurnalul afiseaza un avertisment despre statusuri nemapate.",
         "Unele statusuri Jira nu sunt definite in fisierul de flux. Procesarea se finalizeaza totusi."),
        ("Fisierele de iesire nu sunt create.",
         "Verificati daca dosarul de iesire exista si aveti permisiuni de scriere. Asigurati-va ca fisierele nu sunt deschise in Excel."),
        ("Ce fisier folosesc pentru build_reports?",
         "IssueTimes.xlsx este obligatoriu pentru toate metricile. CFD.xlsx este necesar suplimentar pentru Diagrama de Flux Cumulativ."),
        ("Cat de des trebuie sa rulez transform_data?",
         "Ori de cate ori aveti nevoie de date actualizate din Jira."),
        ("Ce inseamna 'carry-forward'?",
         "Timpul petrecut intr-un status nemadat este atribuit ultimei etape cunoscute -- nu se pierde timp."),
    ]
    for q, a in faqs:
        story.append(H3("I: " + q, st))
        story.append(P("R: " + a, st))
        story.append(SP(4))

    story.append(PageBreak())
    story.append(H1("9  Glosar", st))
    story.append(tbl(
        ["Termen", "Explicatie"],
        [
            ["Carry-forward", "Timpul intr-un status nemadat este atribuit ultimei etape cunoscute."],
            ["CFD", "Cumulative Flow Diagram -- arata evolutia stocului pe etape in timp."],
            ["Closed Date", "Data finalizarii unui issue."],
            ["First Date", "Data inceperii lucrului activ la un issue."],
            ["Implementation Date", "Data inceperii lucrului de dezvoltare."],
            ["Issue", "Un tichet in sistemul de tickete (ex. un card Jira)."],
            ["JSON", "Format text simplu pentru date structurate."],
            ["Marker", "Linii in fisierul de flux care desemneaza o etapa ca jalon: <First>, <InProgress>, <Closed>."],
            ["Prefix", "Prefixul numelui fisierelor de iesire (ex. 'ART_A')."],
            ["Etapa (Stage)", "Un pas logic al procesului mapat la unul sau mai multe statusuri Jira."],
            ["Fisier de flux", "Fisier text care descrie etapele si jalonii unui proiect."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content — Portuguese
# ---------------------------------------------------------------------------

def content_pt(st):
    story = []
    story.append(PageBreak())
    story.append(H1("Indice", st))
    toc = _make_toc("pt")
    story.append(toc)

    story.append(PageBreak())
    story.append(H1("1  O que e o transform_data?", st))
    story.append(P(
        "transform_data e o primeiro modulo da cadeia de ferramentas situation-report. "
        "Le um exporto de dados brutos do seu sistema de tickets (Jira) e prepara "
        "os dados para analise posterior. O resultado sao tres <b>ficheiros Excel</b> "
        "que mostram quanto tempo os issues passaram em cada etapa do fluxo de trabalho.", st))
    story.append(P(
        "O programa tem uma interface grafica simples (GUI): nao sao necessarios "
        "conhecimentos de programacao. Selecione dois ficheiros, clique em 'Executar' "
        "e os ficheiros Excel sao produzidos automaticamente.", st))
    story.append(SP(8))
    story.append(box(
        "<b>O que o transform_data produz:</b><br/>"
        "- <b>IssueTimes.xlsx</b>: Todos os issues com marcas de tempo e minutos por etapa.<br/>"
        "- <b>Transitions.xlsx</b>: Historico completo de statusos de todos os issues.<br/>"
        "- <b>CFD.xlsx</b>: Contagens diarias de entradas por etapa para o Diagrama de Fluxo Cumulativo.", st))
    story.append(SP(8))
    story.append(P(
        "Os ficheiros Excel gerados sao utilizados pelo modulo <b>build_reports</b> "
        "para criar graficos e relatorios.", st))

    story.append(PageBreak())
    story.append(H1("2  Requisitos e instalacao", st))
    story.append(H2("2.1  O que precisa de ser instalado?", st))
    story.append(P("transform_data e fornecido como um <b>pacote portatil</b>. Nao e necessaria uma instalacao Python separada.", st))
    story.append(BL("<b>Windows:</b> O Python ja esta incluido no pacote -- basta descompactar e iniciar.", st))
    story.append(BL("<b>macOS / Linux:</b> No primeiro arranque, um ambiente Python e configurado automaticamente (aprox. 1 minuto, internet necessaria).", st))
    story.append(H2("2.2  Iniciar o programa", st))
    story.append(BL("<b>Windows:</b> Duplo clique em <b>TransformData.bat</b>.", st))
    story.append(BL("<b>macOS:</b> Clique com o botao direito em <b>TransformData.command</b> → <i>Abrir</i>.", st))
    story.append(BL("<b>Linux:</b> No terminal: <font name='Courier'>./TransformData.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Dica (Windows):</b> No primeiro arranque, o SmartScreen pode mostrar um aviso. "
        "Clique em <b>Mais informacoes</b> → <b>Executar mesmo assim</b>.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("3  Ficheiros de entrada", st))
    story.append(P(
        "transform_data requer exatamente dois ficheiros: o exporto JSON do Jira e o "
        "ficheiro de definicao do fluxo de trabalho. Ambos sao selecionados na GUI.", st))
    story.append(H2("3.1  Exporto JSON do Jira", st))
    story.append(P(
        "Este e um exporto de todos os issues de um projeto Jira em formato JSON. "
        "Contem o historico completo de statusos (changelog), metadados e o status atual.", st))
    story.append(P("Como gerar o exporto do Jira e descrito no modulo <b>get_data</b>.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nome tipico:</b> ART_A.json, MYPROJECT.json, etc.<br/>"
        "<b>Tamanho:</b> Depende do numero de issues; frequentemente varios MB.", st, "#fff8e1"))
    story.append(H2("3.2  Ficheiro de definicao do fluxo", st))
    story.append(P(
        "O ficheiro de fluxo e um ficheiro de texto simples (.txt) que descreve como os "
        "statusos Jira do seu projeto sao mapeados para etapas logicas do processo. "
        "Tambem define qual etapa marca o inicio do trabalho ativo e o fecho.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nome tipico:</b> workflow_ART_A.txt, etc.<br/>"
        "<b>Criado por:</b> O seu contacto tecnico ou Scrum Master -- uma vez por projeto, raramente alterado.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("4  O ficheiro de definicao do fluxo", st))
    story.append(P(
        "O ficheiro de fluxo controla como o transform_data interpreta os statusos Jira. "
        "Normalmente nao precisa de criar este ficheiro.", st))
    story.append(H2("4.1  Estrutura", st))
    story.append(P("<b>Exemplo:</b>", st))
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
        ["Formato", "Significado"],
        [
            ["Etapa:Alias1:Alias2", "Etapa com statusos Jira mapeados. O primeiro nome e o nome canonico da etapa."],
            ["<First>Etapa", "Esta etapa marca o inicio do trabalho ativo (First Date)."],
            ["<InProgress>Etapa", "Esta etapa define o Implementation Date."],
            ["<Closed>Etapa", "Esta etapa marca a conclusao (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Ordem das etapas", st))
    story.append(P(
        "As etapas sao listadas na ordem em que sao percorridas no processo. "
        "Esta ordem e usada para o CFD e para calcular o Closed Date quando etapas sao ignoradas.", st))
    story.append(H2("4.3  Statusos nao mapeados", st))
    story.append(P(
        "Se o exporto Jira contiver statusos nao definidos no ficheiro de fluxo, "
        "o transform_data emite um aviso. O tempo e atribuido a ultima etapa conhecida.", st))

    story.append(PageBreak())
    story.append(H1("5  A interface grafica (GUI)", st))
    story.append(P("Apos o inicio, abre-se uma janela com campos de selecao de ficheiros e um registo de estado.", st))
    story.append(H2("5.1  Selecionar ficheiros", st))
    story.append(BL("<b>Ficheiro JSON</b> - Clique em 'Procurar' e selecione o exporto Jira. A pasta de saida e o prefixo sao preenchidos automaticamente.", st))
    story.append(BL("<b>Ficheiro de fluxo</b> - Selecione o ficheiro .txt adequado para o seu projeto.", st))
    story.append(SP(4))
    story.append(box("<b>Dica:</b> Se selecionar primeiro o ficheiro JSON, a pasta de saida e o prefixo sao preenchidos automaticamente.", st, "#e8f8f0"))
    story.append(H2("5.2  Configurar a saida", st))
    story.append(tbl(
        ["Campo", "Significado"],
        [
            ["Pasta de saida", "Diretorio onde os tres ficheiros Excel sao guardados. Predefinicao: diretorio do ficheiro JSON."],
            ["Prefixo", "Prefixo do nome dos ficheiros. 'ART_A' produz ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx e ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Iniciar a transformacao", st))
    story.append(P(
        "Clique em <b>'Executar'</b>. O programa le os dados, calcula todos os valores "
        "e guarda os tres ficheiros Excel. O progresso e quaisquer avisos aparecem no registo.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Avisos no registo:</b> Um aviso sobre statusos nao mapeados nao significa "
        "que a transformacao falhou -- os ficheiros de saida sao criados na mesma.", st, "#fff8e1"))
    story.append(H2("5.4  Idioma e ajuda", st))
    story.append(P(
        "Use o menu <b>Opcoes</b> para mudar o idioma. "
        "Em <b>Ajuda &rarr; Manual</b>, este manual abre no browser.", st))

    story.append(PageBreak())
    story.append(H1("6  Ficheiros de saida", st))
    story.append(P("transform_data produz tres ficheiros Excel utilizados como entrada para build_reports.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(tbl(
        ["Coluna", "Conteudo"],
        [
            ["Project",            "Chave do projeto (ex. ART_A)"],
            ["Key",                "Chave do issue (ex. ART_A-123)"],
            ["Issuetype",          "Tipo do issue (ex. Feature, Bug, Story)"],
            ["Status",             "Status atual do Jira"],
            ["Created Date",       "Data de criacao do issue no Jira"],
            ["First Date",         "Primeira entrada na etapa <First>"],
            ["Implementation Date","Primeira entrada na etapa <InProgress>"],
            ["Closed Date",        "Marca de tempo da conclusao (vazio = ainda aberto)"],
            ["Colunas de etapas",  "Uma coluna por etapa: minutos passados nessa etapa"],
            ["Resolution",         "Tipo de fecho do Jira"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(H2("6.2  Transitions.xlsx", st))
    story.append(P("Contem o historico completo de statusos de todos os issues -- uma entrada por alteracao de status.", st))
    story.append(tbl(
        ["Coluna", "Conteudo"],
        [
            ["Key",        "Chave do issue"],
            ["Transition", "Nome da etapa (ou 'Created' para a marca de tempo de criacao)"],
            ["Timestamp",  "Data e hora da alteracao de status"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("6.3  CFD.xlsx", st))
    story.append(P(
        "Contem, para cada dia do calendario, o numero de issues que entraram em cada etapa "
        "nesse dia. build_reports acumula estes valores para o Diagrama de Fluxo Cumulativo.", st))

    story.append(PageBreak())
    story.append(H1("7  Como sao calculadas as datas e durações?", st))
    story.append(H2("7.1  Tempos por etapa", st))
    story.append(tbl(
        ["Situacao", "Regra"],
        [
            ["Issue criado mas sem alteracao de status",
             "O tempo desde a criacao ate a primeira alteracao e atribuido a etapa inicial."],
            ["Alteracao de status para uma etapa nao mapeada",
             "O tempo continua na ultima etapa conhecida (carry-forward)."],
            ["Status atual",
             "A ultima etapa conhecida acumula tempo ate ao momento do processamento."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "O First Date e definido quando um issue entra pela primeira vez na etapa "
        "marcada com <b>&lt;First&gt;</b>. Representa o inicio do trabalho ativo.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Etapa First ignorada:</b> Se um issue entrar numa etapa apos &lt;First&gt; "
        "sem a atingir diretamente, a marca de tempo dessa etapa e usada como First Date.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "O Closed Date e definido ao entrar na etapa marcada com <b>&lt;Closed&gt;</b>. "
        "Se fechado e reaberto varias vezes, usa-se a <b>ultima</b> marca de tempo de fecho.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Issues reabertos:</b> Se um issue estiver antes de &lt;Closed&gt;, "
        "nao e definido Closed Date.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Issues nunca trabalhados:</b> Issues sem First Date nao recebem Closed Date "
        "e nao sao contados no Flow Velocity.", st, "#e8eaf6"))

    story.append(PageBreak())
    story.append(H1("8  Perguntas frequentes e dicas", st))
    faqs = [
        ("Um issue nao tem First Date -- porque?",
         "O issue nunca atingiu a etapa <First> nem qualquer etapa posterior. No build_reports e contado como 'To Do'."),
        ("Um issue nao tem Closed Date -- porque?",
         "Razoes possiveis: (1) O issue ainda esta aberto. (2) Nao tem First Date. (3) Foi reaberto apos o fecho."),
        ("O registo mostra um aviso sobre statusos nao mapeados.",
         "Alguns statusos Jira nao estao definidos no ficheiro de fluxo. O processamento conclui na mesma."),
        ("Os ficheiros de saida nao sao criados.",
         "Verifique se a pasta de saida existe e se tem permissoes de escrita. Certifique-se de que os ficheiros nao estao abertos no Excel."),
        ("Que ficheiro uso para o build_reports?",
         "IssueTimes.xlsx e obrigatorio para todas as metricas. CFD.xlsx e adicionalmente necessario para o Diagrama de Fluxo Cumulativo."),
        ("Com que frequencia devo executar o transform_data?",
         "Sempre que precisar de dados atualizados do Jira."),
        ("O que significa 'carry-forward'?",
         "O tempo num status nao mapeado e atribuido a ultima etapa conhecida -- nenhum tempo e perdido."),
    ]
    for q, a in faqs:
        story.append(H3("P: " + q, st))
        story.append(P("R: " + a, st))
        story.append(SP(4))

    story.append(PageBreak())
    story.append(H1("9  Glossario", st))
    story.append(tbl(
        ["Termo", "Explicacao"],
        [
            ["Carry-forward", "Tempo num status nao mapeado e atribuido a ultima etapa conhecida."],
            ["CFD", "Cumulative Flow Diagram -- mostra a evolucao do stock por etapas ao longo do tempo."],
            ["Closed Date", "A data de conclusao de um issue."],
            ["First Date", "A data em que o trabalho ativo num issue comecou."],
            ["Implementation Date", "A data em que o trabalho de desenvolvimento comecou."],
            ["Issue", "Um ticket no sistema de tickets (ex. um cartao Jira)."],
            ["JSON", "Formato de texto simples para dados estruturados."],
            ["Marcador (Marker)", "Linhas no ficheiro de fluxo que designam uma etapa como marco: <First>, <InProgress>, <Closed>."],
            ["Prefixo", "Prefixo do nome dos ficheiros de saida (ex. 'ART_A')."],
            ["Etapa (Stage)", "Um passo logico do processo mapeado para um ou mais statusos Jira."],
            ["Ficheiro de fluxo", "Ficheiro de texto que descreve as etapas e marcos de um projeto."],
        ],
        col_widths=[4.5*cm, 11.5*cm]))

    return story, toc


# ---------------------------------------------------------------------------
# Content — French
# ---------------------------------------------------------------------------

def content_fr(st):
    story = []
    story.append(PageBreak())
    story.append(H1("Table des matieres", st))
    toc = _make_toc("fr")
    story.append(toc)

    story.append(PageBreak())
    story.append(H1("1  Qu'est-ce que transform_data ?", st))
    story.append(P(
        "transform_data est le premier module de la chaine d'outils situation-report. "
        "Il lit un export de donnees brutes de votre systeme de tickets (Jira) et "
        "prepare les donnees pour une analyse ulterieure. Le resultat sont trois "
        "<b>fichiers Excel</b> qui montrent combien de temps les issues ont passe "
        "dans chaque etape du flux de travail.", st))
    story.append(P(
        "Le programme dispose d'une interface graphique simple (GUI) : aucune "
        "connaissance en programmation n'est requise. Selectionnez deux fichiers, "
        "cliquez sur 'Executer' et les fichiers Excel sont produits automatiquement.", st))
    story.append(SP(8))
    story.append(box(
        "<b>Ce que produit transform_data :</b><br/>"
        "- <b>IssueTimes.xlsx</b> : Tous les issues avec horodatages et minutes par etape.<br/>"
        "- <b>Transitions.xlsx</b> : Historique complet des statuts de tous les issues.<br/>"
        "- <b>CFD.xlsx</b> : Comptages d'entrees quotidiens par etape pour le Diagramme de Flux Cumulatif.", st))
    story.append(SP(8))
    story.append(P(
        "Les fichiers Excel generes sont ensuite utilises par le module <b>build_reports</b> "
        "pour creer des graphiques et des rapports.", st))

    story.append(PageBreak())
    story.append(H1("2  Prerequis et installation", st))
    story.append(H2("2.1  Que faut-il installer ?", st))
    story.append(P("transform_data est fourni sous forme de <b>paquet portable</b>. Aucune installation Python separee n'est necessaire.", st))
    story.append(BL("<b>Windows :</b> Python est deja inclus dans le paquet -- decompressez et demarrez.", st))
    story.append(BL("<b>macOS / Linux :</b> Au premier lancement, un environnement Python est configure automatiquement (environ 1 minute, internet requis).", st))
    story.append(H2("2.2  Demarrer le programme", st))
    story.append(BL("<b>Windows :</b> Double-cliquez sur <b>TransformData.bat</b>.", st))
    story.append(BL("<b>macOS :</b> Clic droit sur <b>TransformData.command</b> → <i>Ouvrir</i>.", st))
    story.append(BL("<b>Linux :</b> Dans un terminal : <font name='Courier'>./TransformData.sh</font>", st))
    story.append(SP(4))
    story.append(box(
        "<b>Conseil (Windows) :</b> Au premier lancement, SmartScreen peut afficher un avertissement. "
        "Cliquez sur <b>Plus d'informations</b> → <b>Executer quand meme</b>.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("3  Fichiers d'entree", st))
    story.append(P(
        "transform_data necessite exactement deux fichiers : l'export JSON de Jira et le "
        "fichier de definition du flux de travail. Les deux sont selectionnes dans la GUI.", st))
    story.append(H2("3.1  Export JSON de Jira", st))
    story.append(P(
        "Il s'agit d'un export de tous les issues d'un projet Jira au format JSON. "
        "Il contient l'historique complet des statuts (changelog), les metadonnees et le statut actuel.", st))
    story.append(P("La procedure d'export depuis Jira est decrite dans le module <b>get_data</b>.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nom typique :</b> ART_A.json, MYPROJECT.json, etc.<br/>"
        "<b>Taille :</b> Depend du nombre d'issues ; souvent plusieurs Mo.", st, "#fff8e1"))
    story.append(H2("3.2  Fichier de definition du flux", st))
    story.append(P(
        "Le fichier de flux est un fichier texte simple (.txt) qui decrit comment les "
        "statuts Jira de votre projet sont mappes aux etapes logiques du processus. "
        "Il definit egalement quelle etape marque le debut du travail actif et la cloture.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Nom typique :</b> workflow_ART_A.txt, etc.<br/>"
        "<b>Cree par :</b> Votre contact technique ou Scrum Master -- une fois par projet, rarement modifie.", st, "#e8f8f0"))

    story.append(PageBreak())
    story.append(H1("4  Le fichier de definition du flux", st))
    story.append(P(
        "Le fichier de flux controle la facon dont transform_data interprete les statuts Jira. "
        "Vous n'avez generalement pas besoin de creer ce fichier vous-meme.", st))
    story.append(H2("4.1  Structure", st))
    story.append(P("<b>Exemple :</b>", st))
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
        ["Format", "Signification"],
        [
            ["Etape:Alias1:Alias2", "Etape avec les statuts Jira mappes. Le premier nom est le nom canonique de l'etape."],
            ["<First>Etape", "Cette etape marque le debut du travail actif (First Date)."],
            ["<InProgress>Etape", "Cette etape definit l'Implementation Date."],
            ["<Closed>Etape", "Cette etape marque la cloture (Closed Date)."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("4.2  Ordre des etapes", st))
    story.append(P(
        "Les etapes sont listees dans l'ordre dans lequel elles sont parcourues dans le processus. "
        "Cet ordre est utilise pour le CFD et pour calculer le Closed Date.", st))
    story.append(H2("4.3  Statuts non mappes", st))
    story.append(P(
        "Si l'export Jira contient des statuts non definis dans le fichier de flux, "
        "transform_data emet un avertissement. Le temps est attribue a la derniere etape connue.", st))

    story.append(PageBreak())
    story.append(H1("5  L'interface graphique (GUI)", st))
    story.append(P("Apres le demarrage, une fenetre s'ouvre avec des champs de selection de fichiers et un journal.", st))
    story.append(H2("5.1  Selection des fichiers", st))
    story.append(BL("<b>Fichier JSON</b> - Cliquez sur 'Parcourir' et selectionnez votre export Jira. Le dossier de sortie et le prefixe sont remplis automatiquement.", st))
    story.append(BL("<b>Fichier de flux</b> - Selectionnez le fichier .txt approprie pour votre projet.", st))
    story.append(SP(4))
    story.append(box("<b>Conseil :</b> Si vous selectionnez d'abord le fichier JSON, le dossier de sortie et le prefixe sont pre-remplis automatiquement.", st, "#e8f8f0"))
    story.append(H2("5.2  Configuration de la sortie", st))
    story.append(tbl(
        ["Champ", "Signification"],
        [
            ["Dossier de sortie", "Repertoire ou les trois fichiers Excel sont enregistres. Par defaut : repertoire du fichier JSON."],
            ["Prefixe", "Prefixe du nom des fichiers. 'ART_A' produit ART_A_IssueTimes.xlsx, ART_A_Transitions.xlsx et ART_A_CFD.xlsx."],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("5.3  Lancer la transformation", st))
    story.append(P(
        "Cliquez sur <b>'Executer'</b>. Le programme lit les donnees, calcule toutes les valeurs "
        "et enregistre les trois fichiers Excel. La progression et les avertissements apparaissent dans le journal.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Avertissements dans le journal :</b> Un avertissement sur des statuts non mappes "
        "ne signifie pas que la transformation a echoue -- les fichiers de sortie sont quand meme produits.", st, "#fff8e1"))
    story.append(H2("5.4  Langue et aide", st))
    story.append(P(
        "Utilisez le menu <b>Options</b> pour changer la langue. "
        "Sous <b>Aide &rarr; Manuel</b>, ce manuel s'ouvre dans votre navigateur.", st))

    story.append(PageBreak())
    story.append(H1("6  Fichiers de sortie", st))
    story.append(P("transform_data produit trois fichiers Excel utilises comme entree pour build_reports.", st))
    story.append(H2("6.1  IssueTimes.xlsx", st))
    story.append(tbl(
        ["Colonne", "Contenu"],
        [
            ["Project",            "Cle du projet (ex. ART_A)"],
            ["Key",                "Cle de l'issue (ex. ART_A-123)"],
            ["Issuetype",          "Type de l'issue (ex. Feature, Bug, Story)"],
            ["Status",             "Statut actuel dans Jira"],
            ["Created Date",       "Date de creation de l'issue dans Jira"],
            ["First Date",         "Premiere entree dans l'etape <First>"],
            ["Implementation Date","Premiere entree dans l'etape <InProgress>"],
            ["Closed Date",        "Horodatage de cloture (vide = encore ouvert)"],
            ["Colonnes d'etapes",  "Une colonne par etape : minutes passees dans cette etape"],
            ["Resolution",         "Type de cloture depuis Jira"],
        ],
        col_widths=[4.5*cm, 11.5*cm]))
    story.append(H2("6.2  Transitions.xlsx", st))
    story.append(P("Contient l'historique complet des statuts de tous les issues -- une entree par changement de statut.", st))
    story.append(tbl(
        ["Colonne", "Contenu"],
        [
            ["Key",        "Cle de l'issue"],
            ["Transition", "Nom de l'etape (ou 'Created' pour l'horodatage de creation)"],
            ["Timestamp",  "Date et heure du changement de statut"],
        ],
        col_widths=[4*cm, 12*cm]))
    story.append(H2("6.3  CFD.xlsx", st))
    story.append(P(
        "Contient, pour chaque jour calendaire, le nombre d'issues entres dans chaque etape ce jour-la. "
        "build_reports accumule ces valeurs pour produire le Diagramme de Flux Cumulatif.", st))

    story.append(PageBreak())
    story.append(H1("7  Comment les dates et les durees sont-elles calculees ?", st))
    story.append(H2("7.1  Temps par etape", st))
    story.append(tbl(
        ["Situation", "Regle"],
        [
            ["Issue cree mais sans changement de statut",
             "Le temps depuis la creation jusqu'au premier changement est attribue a l'etape initiale."],
            ["Changement de statut vers une etape non mappee",
             "Le temps continue dans la derniere etape connue (carry-forward)."],
            ["Statut actuel",
             "La derniere etape connue accumule le temps jusqu'au moment du traitement."],
        ],
        col_widths=[5*cm, 11*cm]))
    story.append(H2("7.2  First Date", st))
    story.append(P(
        "Le First Date est defini lorsqu'un issue entre pour la premiere fois dans l'etape "
        "marquee <b>&lt;First&gt;</b>. Il represente le debut du travail actif.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Etape First ignoree :</b> Si un issue entre dans une etape apres &lt;First&gt; "
        "sans y entrer directement, l'horodatage de cette etape est utilise comme First Date.", st, "#e8f5e9"))
    story.append(H2("7.3  Closed Date", st))
    story.append(P(
        "Le Closed Date est defini lors de l'entree dans l'etape marquee <b>&lt;Closed&gt;</b>. "
        "Si ferme et rouvert plusieurs fois, le <b>dernier</b> horodatage de fermeture est utilise.", st))
    story.append(SP(4))
    story.append(box(
        "<b>Issues rouverts :</b> Si un issue se trouve avant &lt;Closed&gt;, "
        "aucun Closed Date n'est defini.", st, "#fce4ec"))
    story.append(SP(4))
    story.append(box(
        "<b>Issues jamais travailles :</b> Les issues sans First Date ne recoivent pas de Closed Date "
        "et ne sont pas comptes dans le Flow Velocity.", st, "#e8eaf6"))

    story.append(PageBreak())
    story.append(H1("8  Questions frequentes et conseils", st))
    faqs = [
        ("Un issue n'a pas de First Date -- pourquoi ?",
         "L'issue n'a jamais atteint l'etape <First> ni aucune etape ulterieure. Dans build_reports, il est compte comme 'To Do'."),
        ("Un issue n'a pas de Closed Date -- pourquoi ?",
         "Raisons possibles : (1) L'issue est encore ouvert. (2) Il n'a pas de First Date. (3) Il a ete rouvert apres fermeture."),
        ("Le journal affiche un avertissement sur des statuts non mappes.",
         "Certains statuts Jira ne sont pas definis dans le fichier de flux. Le traitement se termine quand meme."),
        ("Les fichiers de sortie ne sont pas crees.",
         "Verifiez que le dossier de sortie existe et que vous avez les droits d'ecriture. Assurez-vous que les fichiers ne sont pas ouverts dans Excel."),
        ("Quel fichier utiliser pour build_reports ?",
         "IssueTimes.xlsx est obligatoire pour toutes les metriques. CFD.xlsx est necessaire en plus pour le Diagramme de Flux Cumulatif."),
        ("A quelle frequence dois-je executer transform_data ?",
         "Chaque fois que vous avez besoin de donnees mises a jour depuis Jira."),
        ("Que signifie 'carry-forward' ?",
         "Le temps dans un statut non mappe est attribue a la derniere etape connue -- aucun temps n'est perdu."),
    ]
    for q, a in faqs:
        story.append(H3("Q : " + q, st))
        story.append(P("R : " + a, st))
        story.append(SP(4))

    story.append(PageBreak())
    story.append(H1("9  Glossaire", st))
    story.append(tbl(
        ["Terme", "Explication"],
        [
            ["Carry-forward", "Le temps dans un statut non mappe est attribue a la derniere etape connue."],
            ["CFD", "Cumulative Flow Diagram -- montre l'evolution du stock par etapes dans le temps."],
            ["Closed Date", "La date de cloture d'un issue."],
            ["First Date", "La date de debut du travail actif sur un issue."],
            ["Implementation Date", "La date de debut du travail de developpement."],
            ["Issue", "Un ticket dans le systeme de tickets (ex. une carte Jira)."],
            ["JSON", "Format texte simple pour les donnees structurees."],
            ["Marqueur (Marker)", "Lignes dans le fichier de flux qui designent une etape comme jalon : <First>, <InProgress>, <Closed>."],
            ["Prefixe", "Prefixe du nom des fichiers de sortie (ex. 'ART_A')."],
            ["Etape (Stage)", "Une etape logique du processus mappee a un ou plusieurs statuts Jira."],
            ["Fichier de flux", "Fichier texte decrivant les etapes et jalons d'un projet."],
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
    """Generate transform_data user manuals in all 5 languages."""
    _build_doc(OUTPUT_DE, "de", content_de,
               "transform_data Benutzerhandbuch",
               "Jira-Daten aufbereiten fuer Metriken und Berichte")
    _build_doc(OUTPUT_EN, "en", content_en,
               "transform_data User Manual",
               "Prepare Jira data for metrics and reports")
    _build_doc(OUTPUT_RO, "ro", content_ro,
               "transform_data Manual de Utilizator",
               "Pregatiti datele Jira pentru metrici si rapoarte")
    _build_doc(OUTPUT_PT, "pt", content_pt,
               "transform_data Manual do Utilizador",
               "Preparar dados Jira para metricas e relatorios")
    _build_doc(OUTPUT_FR, "fr", content_fr,
               "transform_data Manuel d'utilisation",
               "Preparer les donnees Jira pour les metriques et rapports")


if __name__ == "__main__":
    main()
