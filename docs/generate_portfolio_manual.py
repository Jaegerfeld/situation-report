# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für das portfolio-Modul (Solutions &
#   Portfolios) als PDF in allen fünf unterstützten Sprachen (DE, EN, RO, PT,
#   FR). Beschreibt Zweck, Grundbegriffe, Start, GUI-Bedienung, Report-Inhalt
#   (Pooled/Comparison, Management-Summary, Metriken inkl. CFD), CLI und FAQ.
# =============================================================================

import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _font_config import setup as _setup_fonts

_FN, _FB, _FI, _FBI = _setup_fonts()  # normal, bold, italic, bold_italic
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    ActionFlowable,
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import Image as RLImage

from version import __version__ as _VERSION

OUTPUT_DE = Path(__file__).parent / "portfolio_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "portfolio_UserManual.pdf"
OUTPUT_RO = Path(__file__).parent / "portfolio_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "portfolio_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "portfolio_ManuelUtilisateur.pdf"

CONTENT_WIDTH_CM = 15.5

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

_HEADER_TEXT = {
    LANG_DE: "Solutions & Portfolios  --  Benutzerhandbuch",
    LANG_EN: "Solutions & Portfolios  --  User Manual",
    LANG_RO: "Solutions & Portfolios  --  Manual de Utilizator",
    LANG_PT: "Solutions & Portfolios  --  Manual do Utilizador",
    LANG_FR: "Solutions & Portfolios  --  Manuel d'utilisation",
}
_PAGE_LABEL = {
    LANG_DE: "Seite %d",
    LANG_EN: "Page %d",
    LANG_RO: "Pagina %d",
    LANG_PT: "Pagina %d",
    LANG_FR: "Page %d",
}
_COVER_SUBTITLE = {
    LANG_DE: "Benutzerhandbuch",
    LANG_EN: "User Manual",
    LANG_RO: "Manual de Utilizator",
    LANG_PT: "Manual do Utilizador",
    LANG_FR: "Manuel d'utilisation",
}
_COVER_TAGLINE = {
    LANG_DE: "Aggregierte Flow-Reports über mehrere ARTs, Solutions und Portfolien",
    LANG_EN: "Aggregated flow reports across multiple ARTs, solutions and portfolios",
    LANG_RO: "Rapoarte de flux agregate pe mai multe ART-uri, solutii si portofolii",
    LANG_PT: "Relatorios de fluxo agregados de varios ARTs, solucoes e portefolios",
    LANG_FR: "Rapports de flux agreges sur plusieurs ARTs, solutions et portefeuilles",
}
_COVER_AUDIENCE = {
    LANG_DE: "Für Agile Coaches, RTEs und PI Manager",
    LANG_EN: "For Agile Coaches, RTEs and PI Managers",
    LANG_RO: "Pentru Agile Coaches, RTE si Manageri PI",
    LANG_PT: "Para Agile Coaches, RTEs e Gestores de PI",
    LANG_FR: "Pour les Agile Coaches, RTEs et PI Managers",
}


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("H1p", fontName=_FB, fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8),
        h2=s("H2p", fontName=_FB, fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5),
        body=s("Bodyp", fontName=_FN, fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("Bulletp", fontName=_FN, fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3),
        code=s("Codep", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("Hintp", fontName=_FI, fontSize=9,
               textColor=C_HINT, leading=13, leftIndent=12, spaceAfter=4),
        center=s("Centerp", fontName=_FN, fontSize=10, leading=15,
                 alignment=TA_CENTER, spaceAfter=6),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

class NextPageTemplate(ActionFlowable):
    def __init__(self, pt):
        super().__init__(("nextPageTemplate", pt))


_TABLE_STYLE = TableStyle([
    ("BACKGROUND",     (0, 0), (-1, 0), C_BLUE),
    ("ALIGN",          (0, 0), (-1, 0), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
    ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ("GRID",           (0, 0), (-1, -1), 0.4, C_MID),
    ("TOPPADDING",     (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
    ("LEFTPADDING",    (0, 0), (-1, -1), 8),
])

_TBL_HDR_STYLE = ParagraphStyle(
    "TblHdr_portfolio",
    fontName=_FB, fontSize=10, textColor=C_WHITE, leading=13,
)
_TBL_CELL_STYLE = ParagraphStyle(
    "TblCell_portfolio",
    fontName=_FN, fontSize=9, leading=13,
)


def tbl(data: list, col_widths=None):
    def _w(val, sty):
        return Paragraph(str(val), sty) if not isinstance(val, Paragraph) else val
    wrapped = (
        [[_w(c, _TBL_HDR_STYLE) for c in data[0]]]
        + [[_w(c, _TBL_CELL_STYLE) for c in row] for row in data[1:]]
    )
    t = Table(wrapped, colWidths=col_widths)
    t.setStyle(_TABLE_STYLE)
    return t


class _PortfolioDoc(BaseDocTemplate):

    def __init__(self, filename: str, lang: str = LANG_EN, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        margin = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=partial(_build_cover, lang=lang)),
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
        canvas.setFont(_FB, 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2*cm, h - 0.7*cm, _HEADER_TEXT[self._lang])
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont(_FN, 8)
        canvas.drawCentredString(w/2, 1.0*cm, _PAGE_LABEL[self._lang] % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2*cm, 1.4*cm, w - 2.2*cm, 1.4*cm)
        canvas.restoreState()


def _build_cover(canvas, doc, lang: str = LANG_EN):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont(_FB, 30)
    canvas.drawCentredString(w/2, h*0.62, "Solutions & Portfolios")
    canvas.setFont(_FB, 16)
    canvas.drawCentredString(w/2, h*0.565, "portfolio")
    canvas.setFont(_FB, 16)
    canvas.drawCentredString(w/2, h*0.515, _COVER_SUBTITLE[lang])
    canvas.setFont(_FN, 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.47, _COVER_TAGLINE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.15, h*0.44, w*0.85, h*0.44)
    canvas.setFont(_FN, 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report — github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09,
                             f"{_COVER_AUDIENCE[lang]} — Version {_VERSION}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------

def _P(text, st):  return Paragraph(text, st["body"])
def _BL(text, st): return Paragraph("- " + text, st["bullet"])
def _H1(text, st): return Paragraph(text, st["h1"])
def _H2(text, st): return Paragraph(text, st["h2"])
def _CD(text, st): return Paragraph(text, st["code"])
def _HI(text, st): return Paragraph(text, st["hint"])
def _SP(n=6):      return Spacer(1, n)


def _box(text, st, bg="#eaf4fb"):
    t = tbl([[Paragraph(text, st["body"])]], col_widths=[16*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(bg)),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_ACCENT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


def _hr(st):
    return HRFlowable(width=CONTENT_WIDTH_CM * cm, thickness=1,
                      color=C_ACCENT, spaceAfter=8)


_GUI_SHOT = Path(__file__).parent / "assets" / "Portfolio-GUI.png"


def _img(path, width_cm=CONTENT_WIDTH_CM):
    ri = RLImage(str(path))
    w = width_cm * cm
    return RLImage(str(path), width=w, height=w * (ri.imageHeight / ri.imageWidth))


def _gui_figure(st, caption):
    """Return the GUI screenshot flowables, or empty if the image is missing."""
    if not _GUI_SHOT.is_file():
        return []
    return [_SP(6), _img(_GUI_SHOT, 12.5), _HI(caption, st), _SP(6)]


# ---------------------------------------------------------------------------
# Content – German
# ---------------------------------------------------------------------------

def content_de(st: dict) -> list:
    story = [NextPageTemplate("normal"), PageBreak()]
    story += [
        _H1("1. Was ist 'Solutions &amp; Portfolios'?", st), _hr(st),
        _P("Bisher betrachtet SituationReport immer <b>einen</b> Team-Verbund bzw. "
           "ART. Das Modul <b>Solutions &amp; Portfolios</b> (technisch: <font name='Courier'>"
           "portfolio</font>) fasst mehrere bereits fertig konfigurierte ARTs zu einem "
           "gemeinsamen Report zusammen — auf <b>Large-Solution-</b> oder "
           "<b>Portfolio-Ebene</b>.", st),
        _P("Sie konfigurieren jeden ART wie gewohnt einmal (in build_reports, als "
           "Projekt-Template). Danach geben Sie nur noch an, welche ARTs zu einer "
           "Solution gehören — und erhalten einen aggregierten Report über alle.", st),
        _box("Kurz gesagt: <b>Solution</b> = mehrere ARTs zusammengefasst. "
             "<b>Portfolio</b> = mehrere Solutions zusammengefasst. Die ART-Reports "
             "selbst ändern sich nicht; sie werden nur referenziert.", st),
        _SP(6),

        _H1("2. Grundbegriffe", st), _hr(st),
        tbl([
            ["Begriff", "Bedeutung"],
            ["ART", "Agile Release Train bzw. Team-Verbund — die Ebene, die Sie heute "
                    "schon in build_reports auswerten."],
            ["Solution", "Eine Zusammenfassung mehrerer ARTs. Verweist auf deren "
                         "Projekt-Templates."],
            ["Portfolio", "Eine Zusammenfassung mehrerer Solutions (verschachtelt: "
                          "Portfolio &gt; Solutions &gt; ARTs)."],
            ["Template", "Eine gespeicherte Konfiguration. ARTs werden über ihr "
                         "build_reports-Template eingebunden; eine Solution kann selbst "
                         "als Template gespeichert und von einem Portfolio referenziert "
                         "werden."],
            ["Pooled", "Modus: alle Issues werden zu <b>einem</b> Datensatz "
                       "zusammengeführt — die Solution als ein System betrachtet."],
            ["Comparison", "Modus: jede Einheit (ART bzw. Solution) wird getrennt "
                           "dargestellt — zum Vergleich nebeneinander."],
        ], col_widths=[3.2*cm, 12.3*cm]),
        _SP(6),

        _H1("3. Starten", st), _hr(st),
        _H2("3.1  Über den Launcher", st),
        _P("Starten Sie SituationReport. Die Einstiegsansicht ist geteilt: <b>links</b> "
           "'Large Solutions &amp; Portfolien', <b>rechts</b> die bekannten ART-Werkzeuge. "
           "Klicken Sie links auf die Karte <b>Solutions &amp; Portfolios</b>.", st),
        _H2("3.2  Direkt", st),
        _P("Alternativ ohne Launcher:", st),
        _CD("python -m portfolio", st),
        _HI("Ohne Argumente öffnet sich die grafische Oberfläche. Mit Argumenten "
            "läuft das Kommandozeilen-Interface (siehe Abschnitt 6).", st),
        _SP(6),

        _H1("4. Die Oberfläche Schritt für Schritt", st), _hr(st),
        *_gui_figure(st, "Abb. 1: Die Oberfläche von Solutions &amp; Portfolios."),
        tbl([
            ["Feld / Aktion", "Beschreibung"],
            ["Name", "Name der Solution bzw. des Portfolios (erscheint im Report)."],
            ["Terminologie", "SAFe oder Global — Beschriftung der Metriken im Report."],
            ["Art", "<b>solution</b> (Mitglieder sind ARTs) oder <b>portfolio</b> "
                    "(Mitglieder sind Solutions)."],
            ["Von / Bis", "Optionaler Berichtszeitraum (JJJJ-MM-TT)."],
            ["ART hinzufügen", "Eine Zeile je Mitglied: Name + Quelle. Bei 'solution' "
                               "ist die Quelle ein ART-Template (.json) oder direkt eine "
                               "IssueTimes.xlsx; bei 'portfolio' ein Solution-Template (.json)."],
            ["Durchsuchen", "Datei für die Quelle auswählen."],
            ["Report-Modus", "Pooled oder Comparison (siehe Abschnitt 5)."],
            ["Speichern", "Die Konfiguration als JSON sichern (= wiederverwendbares "
                          "Template)."],
            ["Laden", "Eine gespeicherte Konfiguration öffnen."],
            ["Report erzeugen", "Erzeugt den Report. Endung <b>.html</b> = Webseite, "
                                "<b>.pdf</b> = PDF. Öffnet sich anschließend."],
        ], col_widths=[3.6*cm, 11.9*cm]),
        _SP(4),
        _box("Tipp: Eine gespeicherte Solution-Datei ist Ihr <b>Solution-Template</b>. "
             "Um ein Portfolio zu bauen, wählen Sie Art = portfolio und verweisen mit "
             "jedem Mitglied auf eine solche gespeicherte Solution-Datei.", st),
        _SP(6),

        _H1("5. Der Report", st), _hr(st),
        _H2("5.1  Management-Summary", st),
        _P("Ganz oben steht eine kompakte Kennzahlen-Tabelle — eine Zeile je Einheit "
           "(im Pooled-Modus eine Zeile für die ganze Solution/Portfolio):", st),
        tbl([
            ["Kennzahl", "Bedeutung"],
            ["Items", "Anzahl der Issues im Zeitraum."],
            ["Completed", "Davon abgeschlossen."],
            ["Open (WIP)", "Offene Issues (noch in Arbeit)."],
            ["Median / 85th / 95th CT", "Durchlaufzeit (Cycle Time) in Tagen — "
                                        "Median sowie 85. und 95. Perzentil."],
            ["&lt;= Nd", "Anteil abgeschlossener Issues innerhalb des Zielwerts "
                         "(Target CT, Standard 90 Tage)."],
            ["Median / 85th LT", "End-to-End-Lead-Time (Created bis Closed) in Tagen — "
                                 "im Pooled-Modus die Solution-Lead-Time über alle ARTs."],
        ], col_widths=[4.2*cm, 11.3*cm]),
        _SP(6),
        _H2("5.2  Pooled vs. Comparison", st),
        _P("<b>Pooled</b> beantwortet: Wie steht die Solution als Ganzes da? Alle "
           "Issues werden zusammengeführt und gemeinsam ausgewertet.", st),
        _P("<b>Comparison</b> beantwortet: Welche Einheit ist der Ausreißer? Bei "
           "einer Solution wird jeder ART getrennt gezeigt, bei einem Portfolio jede "
           "Solution. Die Diagramme stehen pro Metrik nebeneinander.", st),
        _SP(4),
        _H2("5.3  Die Metriken", st),
        tbl([
            ["Metrik", "Aussage"],
            ["Flow Velocity", "Durchsatz: abgeschlossene Items pro Zeitraum/PI."],
            ["Flow Time", "Durchlaufzeit-Verteilung (Boxplot, Scatter mit Trend)."],
            ["Flow Distribution", "Verteilung nach Issue-Typ und Stage-Anteilen."],
            ["CFD", "Cumulative Flow Diagram (siehe 5.4)."],
            ["Flow Load", "Aging WIP — nur im Comparison-Modus je ART, da workflow-"
                          "abhängig."],
        ], col_widths=[3.4*cm, 12.1*cm]),
        _SP(6),
        _H2("5.4  CFD über verschiedene Workflows", st),
        _P("Verschiedene ARTs haben oft unterschiedliche Workflow-Stages. Damit ein "
           "gemeinsames CFD möglich ist, ordnet das Modul jede Stage automatisch einer "
           "von drei <b>kanonischen Gruppen</b> zu — <b>To Do</b>, <b>In Progress</b>, "
           "<b>Done</b> — und summiert die Zahlen je Gruppe. So bleibt das CFD über "
           "ARTs mit unterschiedlichen Workflows hinweg vergleichbar.", st),
        _SP(6),

        _H2("5.5  Datenqualität &amp; Konfidenz", st),
        _P("Unter der Management-Summary steht die Tabelle <b>Data Quality per "
           "Source</b> — eine Zeile je Datenquelle: Record-Zahl, <b>Anteil</b> am "
           "Gesamtvolumen, Anteil ohne First Date, offener Anteil, ob CFD-Daten "
           "vorliegen, der Datenstand — und eine Ampel-<b>Konfidenz</b>:", st),
        tbl([
            ["Stufe", "Bedeutung"],
            ["high", "Quelle vollständig und aktuell — Zahlen belastbar."],
            ["medium", "Mehr als 10 % ohne First Date, keine CFD-Daten oder "
                       "Datenstand älter als 30 Tage."],
            ["low", "Keine Records, oder mehr als die Hälfte ohne First Date — "
                    "Durchlaufzeit-Aussagen stünden auf einer Minderheit der Daten."],
        ], col_widths=[2.4*cm, 13.1*cm]),
        _P("Der Tabellentitel zeigt den <b>Abdeckungsgrad</b> ('x/y sources "
           "delivered data'). Im PDF ist die Tabelle Seite 2. Im Comparison-Modus "
           "werden zusätzlich <b>Ausreißer</b> markiert: Median-CT- und "
           "95.-Perzentil-Zellen erscheinen rot, wenn sie das 1,5-fache des "
           "Spalten-Medians übersteigen (ab drei Einheiten).", st),
        _SP(4),
        _H2("5.6  Eigene Stage-Map (optional)", st),
        _P("Statt der festen drei Gruppen kann die Solution-Konfiguration eigene "
           "kanonische Stages definieren — ein optionaler <font name='Courier'>"
           "stage_map</font>-Block mit geordneter Zuordnung der ART-Stages und den "
           "Markern <font name='Courier'>first_stage</font>/<font name='Courier'>"
           "closed_stage</font> für die CFD-Grenzen. Nicht zugeordnete Stages "
           "fallen mit Warnung in first_stage; Konfigurationen ohne den Block "
           "verhalten sich unverändert.", st),
        _SP(6),

        _H2("5.7  ROAM-Risk-Board (optional)", st),
        _P("Verweist die Solution-Konfiguration über das Feld <font name='Courier'>"
           "risks</font> auf ein Risiko-Register (JSON mit id, title, roam, owner, "
           "impact, status_since), rendert der Report unter der Qualitätstabelle "
           "ein ROAM-Board: Zeilen in R-O-A-M-Reihenfolge (Resolved / Owned / "
           "Accepted / Mitigated), Kategorie- und Impact-Zellen farbig. Ein "
           "Owned-Risiko, das länger als 30 Tage in seiner Kategorie steht, bekommt "
           "eine rote Since-Zelle (Aging) — Ownership ohne Bewegung wird sichtbar. "
           "Ein Portfolio aggregiert die Register aller Member-Solutions und "
           "ergänzt eine Solution-Spalte. Owner sind Teams, keine Personen. Eine "
           "fehlende oder defekte Datei wird geloggt und übersprungen; im PDF ist "
           "das Board eine eigene Seite.", st),
        _SP(6),

        _H2("5.8  NFR-/Runway-Dashboard (optional)", st),
        _P("Verweist die Solution-Konfiguration über das Feld <font name='Courier'>"
           "nfr</font> auf ein NFR-Register (JSON mit den Blöcken nfrs und runway), "
           "rendert der Report unter dem ROAM-Board zwei Tabellen: die NFRs "
           "(Ziel/Ist/Status met, at_risk, violated) und die Architecture-Runway-"
           "Elemente (Status in_place, building, gap mit needed_by-Datum). Die "
           "Status pflegen Menschen im PI-Planning/-Review — das Werkzeug rechnet "
           "Ziel gegen Ist nicht selbst. Verletzte NFRs und Lücken sortieren nach "
           "oben; ein Runway-Element mit verstrichenem needed_by, das nicht in "
           "place ist, erscheint überfällig (rote Datumszelle). Ein Portfolio "
           "aggregiert die Register aller Member-Solutions mit Solution-Spalte. "
           "Owner sind Teams, keine Personen.", st),
        _SP(6),

        _H2("5.9  Capability-Map & -Health (optional)", st),
        _P("Verweist die Solution-Konfiguration über das Feld <font name='Courier'>"
           "capabilities</font> auf eine Capability-Map (JSON mit id, title, "
           "health, arts, owner, assessed_on), rendert der Report eine Tabelle "
           "der Geschäftsfähigkeiten: Health-Ampel healthy/at_risk/critical "
           "(kritisch zuerst, von Menschen im PI-Planning/-Review bewertet) und "
           "die beitragenden ARTs. Eine Capability ohne beitragenden ART wird "
           "als uncovered markiert — Geschäftswert, den niemand liefert; "
           "unbekannte ART-Namen erzeugen eine Drift-Warnung im Log. Ein "
           "Portfolio aggregiert die Maps aller Member-Solutions mit "
           "Solution-Spalte. Die Capability-Map (Geschäftsfähigkeiten) ist "
           "nicht die stage_map (Workflow-Status) — andere Dimension, andere "
           "Quelle. Owner sind Teams, keine Personen.", st),
        _SP(6),

        _H1("6. Kommandozeile (CLI)", st), _hr(st),
        _P("Für Automatisierung und reproduzierbare Reports:", st),
        _CD("python -m portfolio meine_solution.json --output report.html", st),
        _CD("python -m portfolio meine_solution.json --mode comparison --pdf report.pdf", st),
        _SP(4),
        tbl([
            ["Option", "Bedeutung"],
            ["&lt;config&gt;", "Pfad zur Solution-/Portfolio-Konfiguration (JSON)."],
            ["--output FILE", "HTML-Report in diese Datei schreiben."],
            ["--pdf FILE", "Mehrseitigen PDF-Report schreiben."],
            ["--mode pooled|comparison", "Aggregationsmodus (Standard: pooled)."],
            ["--metrics ID ...", "Bestimmte Metriken (Standard hängt vom Modus ab)."],
            ["--terminology SAFe|Global", "Beschriftungs-Modus (Standard: SAFe)."],
            ["--target-ct DAYS", "Zielwert der Cycle Time in Tagen (Standard: 90)."],
            ["--browser", "Den erzeugten HTML-Report im Browser öffnen."],
        ], col_widths=[5.0*cm, 10.5*cm]),
        _SP(6),

        _H1("7. Häufige Fragen (FAQ)", st), _hr(st),
        _H2("Muss ich die ARTs neu konfigurieren?", st),
        _P("Nein. Das Modul referenziert die bestehenden ART-Templates. Die einzige "
           "Wahrheit bleibt das jeweilige ART-Template.", st),
        _H2("Warum fehlt 'Flow Load' im Pooled-Report?", st),
        _P("Flow Load gruppiert nach aktueller Stage. Über verschiedene Workflows wäre "
           "das nicht vergleichbar, daher erscheint es nur im Comparison-Modus je ART.", st),
        _H2("Warum ist der Target-CT-Anteil niedrig oder zeigt einen Strich?", st),
        _P("Ein Strich bedeutet, dass es keine abgeschlossenen Issues mit gültiger Cycle "
           "Time im Zeitraum gibt. Ein niedriger Prozentsatz heißt, dass viele Issues "
           "länger als der Zielwert brauchen.", st),
        _H2("Wie erstelle ich ein Portfolio?", st),
        _P("Speichern Sie zuerst jede Solution. Legen Sie dann eine neue Konfiguration "
           "mit Art = portfolio an und verweisen Sie mit jedem Mitglied auf eine "
           "gespeicherte Solution-Datei.", st),
        _SP(6),

        _H1("8. Glossar", st), _hr(st),
        tbl([
            ["Begriff", "Erklärung"],
            ["ART", "Agile Release Train — Multi-Team-Struktur in SAFe."],
            ["CFD", "Cumulative Flow Diagram — kumulierte Anzahl Issues je Stage."],
            ["Cycle Time", "Zeit von der ersten aktiven Stage bis zum Abschluss."],
            ["PI", "Program Increment — fester Planungszeitraum (oft 8 bis 12 Wochen)."],
            ["Pooling", "Zusammenführen mehrerer Datensätze auf Issue-Ebene."],
            ["WIP", "Work in Progress — offene, noch nicht abgeschlossene Issues."],
        ], col_widths=[3.0*cm, 12.5*cm]),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – English
# ---------------------------------------------------------------------------

def content_en(st: dict) -> list:
    story = [NextPageTemplate("normal"), PageBreak()]
    story += [
        _H1("1. What is 'Solutions &amp; Portfolios'?", st), _hr(st),
        _P("Until now SituationReport always looked at <b>one</b> team group or ART. "
           "The <b>Solutions &amp; Portfolios</b> module (technically: <font name='Courier'>"
           "portfolio</font>) combines several already-configured ARTs into one shared "
           "report — at <b>Large-Solution</b> or <b>portfolio</b> level.", st),
        _P("You configure each ART once as usual (in build_reports, as a project "
           "template). After that you only state which ARTs belong to a solution — and "
           "get an aggregated report across all of them.", st),
        _box("In short: a <b>solution</b> = several ARTs combined. A <b>portfolio</b> = "
             "several solutions combined. The ART reports themselves do not change; they "
             "are only referenced.", st),
        _SP(6),

        _H1("2. Key concepts", st), _hr(st),
        tbl([
            ["Term", "Meaning"],
            ["ART", "Agile Release Train / team group — the level you already analyse "
                    "today in build_reports."],
            ["Solution", "A grouping of several ARTs. Refers to their project templates."],
            ["Portfolio", "A grouping of several solutions (nested: portfolio &gt; "
                          "solutions &gt; ARTs)."],
            ["Template", "A saved configuration. ARTs are included via their "
                         "build_reports template; a solution can itself be saved as a "
                         "template and referenced by a portfolio."],
            ["Pooled", "Mode: all issues are merged into <b>one</b> dataset — the "
                       "solution seen as a single system."],
            ["Comparison", "Mode: each unit (ART or solution) is shown separately, side "
                           "by side."],
        ], col_widths=[3.2*cm, 12.3*cm]),
        _SP(6),

        _H1("3. Starting", st), _hr(st),
        _H2("3.1  From the launcher", st),
        _P("Start SituationReport. The entry screen is split: <b>left</b> 'Large "
           "Solutions &amp; Portfolios', <b>right</b> the familiar ART tools. Click the "
           "<b>Solutions &amp; Portfolios</b> card on the left.", st),
        _H2("3.2  Directly", st),
        _P("Alternatively, without the launcher:", st),
        _CD("python -m portfolio", st),
        _HI("Without arguments the graphical interface opens. With arguments the "
            "command-line interface runs (see section 6).", st),
        _SP(6),

        _H1("4. The interface step by step", st), _hr(st),
        *_gui_figure(st, "Fig. 1: The Solutions &amp; Portfolios interface."),
        tbl([
            ["Field / action", "Description"],
            ["Name", "Name of the solution or portfolio (shown in the report)."],
            ["Terminology", "SAFe or Global — labelling of the report metrics."],
            ["Kind", "<b>solution</b> (members are ARTs) or <b>portfolio</b> (members "
                     "are solutions)."],
            ["From / To", "Optional reporting period (YYYY-MM-DD)."],
            ["Add ART", "One row per member: name + source. For 'solution' the source is "
                        "an ART template (.json) or an IssueTimes.xlsx directly; for "
                        "'portfolio' a solution template (.json)."],
            ["Browse", "Pick the source file."],
            ["Report mode", "Pooled or Comparison (see section 5)."],
            ["Save", "Save the configuration as JSON (= a reusable template)."],
            ["Load", "Open a saved configuration."],
            ["Generate report", "Build the report. Extension <b>.html</b> = web page, "
                                "<b>.pdf</b> = PDF. It opens afterwards."],
        ], col_widths=[3.6*cm, 11.9*cm]),
        _SP(4),
        _box("Tip: a saved solution file is your <b>solution template</b>. To build a "
             "portfolio, choose Kind = portfolio and point each member at such a saved "
             "solution file.", st),
        _SP(6),

        _H1("5. The report", st), _hr(st),
        _H2("5.1  Management summary", st),
        _P("At the very top sits a compact figures table — one row per unit (in pooled "
           "mode a single row for the whole solution/portfolio):", st),
        tbl([
            ["Figure", "Meaning"],
            ["Items", "Number of issues in the period."],
            ["Completed", "Of those, the closed ones."],
            ["Open (WIP)", "Open issues (still in progress)."],
            ["Median / 85th / 95th CT", "Cycle time in days — median plus 85th and 95th "
                                        "percentile."],
            ["&lt;= Nd", "Share of completed issues within the target (Target CT, "
                         "default 90 days)."],
            ["Median / 85th LT", "End-to-end lead time (Created to Closed) in days — in "
                                 "pooled mode the solution lead time across all ARTs."],
        ], col_widths=[4.2*cm, 11.3*cm]),
        _SP(6),
        _H2("5.2  Pooled vs. comparison", st),
        _P("<b>Pooled</b> answers: How is the solution doing as a whole? All issues "
           "are merged and analysed together.", st),
        _P("<b>Comparison</b> answers: Which unit is the outlier? For a solution "
           "each ART is shown separately, for a portfolio each solution. Charts are "
           "placed side by side per metric.", st),
        _SP(4),
        _H2("5.3  The metrics", st),
        tbl([
            ["Metric", "What it shows"],
            ["Flow Velocity", "Throughput: completed items per period/PI."],
            ["Flow Time", "Cycle-time distribution (boxplot, scatter with trend)."],
            ["Flow Distribution", "Split by issue type and stage shares."],
            ["CFD", "Cumulative Flow Diagram (see 5.4)."],
            ["Flow Load", "Aging WIP — comparison mode per ART only, as it is "
                          "workflow-dependent."],
        ], col_widths=[3.4*cm, 12.1*cm]),
        _SP(6),
        _H2("5.4  CFD across different workflows", st),
        _P("Different ARTs often use different workflow stages. To make a shared CFD "
           "possible, the module automatically maps every stage to one of three "
           "<b>canonical groups</b> — <b>To Do</b>, <b>In Progress</b>, <b>Done</b> — "
           "and sums the counts per group. This keeps the CFD comparable across ARTs "
           "with different workflows.", st),
        _SP(6),

        _H2("5.5  Data quality &amp; confidence", st),
        _P("Below the management summary, the <b>Data Quality per Source</b> table "
           "shows one row per data source: record count, its <b>share</b> of all "
           "items, the share without a First Date, the open share, whether CFD "
           "data was supplied, the data freshness — and a traffic-light "
           "<b>confidence</b>:", st),
        tbl([
            ["Level", "Meaning"],
            ["high", "Source complete and fresh — figures trustworthy."],
            ["medium", "More than 10 % without a First Date, no CFD data, or "
                       "data older than 30 days."],
            ["low", "No records, or more than half without a First Date — "
                    "cycle-time statements would rest on a minority of the data."],
        ], col_widths=[2.4*cm, 13.1*cm]),
        _P("The table title carries the <b>coverage ratio</b> ('x/y sources "
           "delivered data'). In the PDF the table is page 2. In comparison mode, "
           "<b>outliers</b> are additionally marked: Median-CT and 95th-percentile "
           "cells turn red when they exceed 1.5x the column median (three units "
           "minimum).", st),
        _SP(4),
        _H2("5.6  Custom stage map (optional)", st),
        _P("Instead of the fixed three groups, the solution configuration may "
           "define its own canonical stages — an optional <font name='Courier'>"
           "stage_map</font> block with an ordered source-stage assignment and the "
           "<font name='Courier'>first_stage</font>/<font name='Courier'>"
           "closed_stage</font> markers for the CFD boundaries. Unmapped stages "
           "fall into first_stage with a warning; configurations without the "
           "block behave unchanged.", st),
        _SP(6),

        _H2("5.7  ROAM risk board (optional)", st),
        _P("When the solution configuration references a risk register via the "
           "<font name='Courier'>risks</font> field (JSON with id, title, roam, "
           "owner, impact, status_since), the report renders a ROAM board below "
           "the quality table: rows in R-O-A-M order (Resolved / Owned / Accepted "
           "/ Mitigated) with coloured category and impact cells. An owned risk "
           "sitting in its category for more than 30 days gets a red Since cell "
           "(aging) — ownership without movement becomes visible. A portfolio "
           "aggregates the registers of all member solutions and adds a Solution "
           "column. Owners are teams, not persons. A missing or invalid file is "
           "logged and skipped; in the PDF the board is its own page.", st),
        _SP(6),

        _H2("5.8  NFR/runway dashboard (optional)", st),
        _P("When the solution configuration references an NFR register via the "
           "<font name='Courier'>nfr</font> field (JSON with nfrs and runway "
           "blocks), the report renders two tables below the ROAM board: the "
           "NFRs (target/actual/status met, at_risk, violated) and the "
           "architecture-runway elements (status in_place, building, gap with a "
           "needed_by date). People assess the statuses in PI planning/review — "
           "the tool does not compute target vs. actual itself. Violated NFRs "
           "and gaps sort first; a runway element whose needed_by has passed "
           "while not in place renders as overdue (red date cell). A portfolio "
           "aggregates the registers of all member solutions with a Solution "
           "column. Owners are teams, not persons.", st),
        _SP(6),

        _H2("5.9  Capability map & health (optional)", st),
        _P("When the solution configuration references a capability map via the "
           "<font name='Courier'>capabilities</font> field (JSON with id, "
           "title, health, arts, owner, assessed_on), the report renders a "
           "table of the business capabilities: a health traffic light "
           "healthy/at_risk/critical (critical first, assessed by people in PI "
           "planning/review) and the contributing ARTs. A capability with no "
           "contributing ART is flagged as uncovered — business value nobody "
           "delivers; unknown ART names produce a drift warning in the log. A "
           "portfolio aggregates the maps of all member solutions with a "
           "Solution column. The capability map (business capabilities) is not "
           "the stage_map (workflow stages) — different dimension, different "
           "source. Owners are teams, not persons.", st),
        _SP(6),

        _H1("6. Command line (CLI)", st), _hr(st),
        _P("For automation and reproducible reports:", st),
        _CD("python -m portfolio my_solution.json --output report.html", st),
        _CD("python -m portfolio my_solution.json --mode comparison --pdf report.pdf", st),
        _SP(4),
        tbl([
            ["Option", "Meaning"],
            ["&lt;config&gt;", "Path to the solution/portfolio configuration (JSON)."],
            ["--output FILE", "Write the HTML report to this file."],
            ["--pdf FILE", "Write a multi-page PDF report."],
            ["--mode pooled|comparison", "Aggregation mode (default: pooled)."],
            ["--metrics ID ...", "Specific metrics (default depends on the mode)."],
            ["--terminology SAFe|Global", "Labelling mode (default: SAFe)."],
            ["--target-ct DAYS", "Target cycle time in days (default: 90)."],
            ["--browser", "Open the generated HTML report in the browser."],
        ], col_widths=[5.0*cm, 10.5*cm]),
        _SP(6),

        _H1("7. Frequently asked questions (FAQ)", st), _hr(st),
        _H2("Do I have to reconfigure the ARTs?", st),
        _P("No. The module references the existing ART templates. Each ART template "
           "remains the single source of truth.", st),
        _H2("Why is 'Flow Load' missing from the pooled report?", st),
        _P("Flow Load groups by current stage. Across different workflows that is not "
           "comparable, so it appears only in comparison mode per ART.", st),
        _H2("Why is the target-CT share low or shown as a dash?", st),
        _P("A dash means there are no completed issues with a valid cycle time in the "
           "period. A low percentage means many issues take longer than the target.", st),
        _H2("How do I create a portfolio?", st),
        _P("First save each solution. Then create a new configuration with Kind = "
           "portfolio and point each member at a saved solution file.", st),
        _SP(6),

        _H1("8. Glossary", st), _hr(st),
        tbl([
            ["Term", "Explanation"],
            ["ART", "Agile Release Train — multi-team structure in SAFe."],
            ["CFD", "Cumulative Flow Diagram — cumulative issue count per stage."],
            ["Cycle Time", "Time from the first active stage to completion."],
            ["PI", "Program Increment — fixed planning period (often 8 to 12 weeks)."],
            ["Pooling", "Merging several datasets at the issue level."],
            ["WIP", "Work in Progress — open, not-yet-completed issues."],
        ], col_widths=[3.0*cm, 12.5*cm]),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – Romanian
# ---------------------------------------------------------------------------

def content_ro(st: dict) -> list:
    story = [NextPageTemplate("normal"), PageBreak()]
    story += [
        _H1("1. Ce este 'Solutions &amp; Portfolios'?", st), _hr(st),
        _P("Pana acum SituationReport analiza intotdeauna <b>un</b> grup de echipe sau "
           "ART. Modulul <b>Solutions &amp; Portfolios</b> (tehnic: <font name='Courier'>"
           "portfolio</font>) combina mai multe ART-uri deja configurate intr-un singur "
           "raport — la nivel de <b>Large Solution</b> sau <b>portofoliu</b>.", st),
        _P("Configurati fiecare ART o singura data, ca de obicei (in build_reports, ca "
           "template de proiect). Apoi indicati doar ce ART-uri apartin unei solutii — si "
           "obtineti un raport agregat peste toate.", st),
        _box("Pe scurt: o <b>solutie</b> = mai multe ART-uri combinate. Un "
             "<b>portofoliu</b> = mai multe solutii combinate. Rapoartele ART nu se "
             "modifica; sunt doar referentiate.", st),
        _SP(6),

        _H1("2. Concepte de baza", st), _hr(st),
        tbl([
            ["Termen", "Semnificatie"],
            ["ART", "Agile Release Train / grup de echipe — nivelul analizat azi in "
                    "build_reports."],
            ["Solutie", "O grupare de mai multe ART-uri. Refera template-urile lor."],
            ["Portofoliu", "O grupare de mai multe solutii (imbricat: portofoliu &gt; "
                           "solutii &gt; ART-uri)."],
            ["Template", "O configuratie salvata. ART-urile se includ prin template-ul "
                         "lor build_reports; o solutie poate fi salvata ca template si "
                         "referentiata de un portofoliu."],
            ["Pooled", "Mod: toate problemele sunt unite intr-un <b>singur</b> set — "
                       "solutia vazuta ca un sistem."],
            ["Comparison", "Mod: fiecare unitate (ART sau solutie) este afisata separat, "
                           "alaturat."],
        ], col_widths=[3.2*cm, 12.3*cm]),
        _SP(6),

        _H1("3. Pornire", st), _hr(st),
        _H2("3.1  Din launcher", st),
        _P("Porniti SituationReport. Ecranul de start este impartit: <b>stanga</b> "
           "'Large Solutions &amp; Portfolios', <b>dreapta</b> instrumentele ART "
           "cunoscute. Apasati cardul <b>Solutions &amp; Portfolios</b> din stanga.", st),
        _H2("3.2  Direct", st),
        _P("Alternativ, fara launcher:", st),
        _CD("python -m portfolio", st),
        _HI("Fara argumente se deschide interfata grafica. Cu argumente ruleaza "
            "interfata din linia de comanda (vezi sectiunea 6).", st),
        _SP(6),

        _H1("4. Interfata pas cu pas", st), _hr(st),
        *_gui_figure(st, "Fig. 1: Interfata Solutions &amp; Portfolios."),
        tbl([
            ["Camp / actiune", "Descriere"],
            ["Nume", "Numele solutiei sau portofoliului (apare in raport)."],
            ["Terminologie", "SAFe sau Global — etichetarea metricilor din raport."],
            ["Tip", "<b>solution</b> (membrii sunt ART-uri) sau <b>portfolio</b> "
                    "(membrii sunt solutii)."],
            ["De la / Pana la", "Perioada de raportare optionala (AAAA-LL-ZZ)."],
            ["Adauga ART", "Cate un rand per membru: nume + sursa. La 'solution' sursa "
                           "este un template ART (.json) sau direct un IssueTimes.xlsx; "
                           "la 'portfolio' un template de solutie (.json)."],
            ["Rasfoieste", "Alegeti fisierul sursa."],
            ["Mod raport", "Pooled sau Comparison (vezi sectiunea 5)."],
            ["Salveaza", "Salvati configuratia ca JSON (= template reutilizabil)."],
            ["Incarca", "Deschideti o configuratie salvata."],
            ["Genereaza raport", "Construieste raportul. Extensia <b>.html</b> = pagina "
                                 "web, <b>.pdf</b> = PDF. Se deschide apoi."],
        ], col_widths=[3.6*cm, 11.9*cm]),
        _SP(4),
        _box("Sfat: un fisier de solutie salvat este <b>template-ul de solutie</b>. "
             "Pentru un portofoliu, alegeti Tip = portfolio si indicati fiecare membru "
             "catre un astfel de fisier de solutie salvat.", st),
        _SP(6),

        _H1("5. Raportul", st), _hr(st),
        _H2("5.1  Rezumat de management", st),
        _P("Sus se afla un tabel compact de indicatori — cate un rand per unitate (in "
           "modul pooled, un singur rand pentru toata solutia/portofoliul):", st),
        tbl([
            ["Indicator", "Semnificatie"],
            ["Items", "Numarul de probleme in perioada."],
            ["Completed", "Dintre acestea, cele finalizate."],
            ["Open (WIP)", "Probleme deschise (inca in lucru)."],
            ["Median / 85th / 95th CT", "Cycle time in zile — mediana plus percentila "
                                        "85 si 95."],
            ["&lt;= Nd", "Procentul problemelor finalizate in limita tintei (Target CT, "
                         "implicit 90 de zile)."],
            ["Median / 85th LT", "Lead time end-to-end (Created pana la Closed) in zile — in "
                                 "modul pooled, lead time-ul solutiei peste toate ART-urile."],
        ], col_widths=[4.2*cm, 11.3*cm]),
        _SP(6),
        _H2("5.2  Pooled vs. comparison", st),
        _P("<b>Pooled</b> raspunde: Cum sta solutia in ansamblu? Toate problemele "
           "sunt unite si analizate impreuna.", st),
        _P("<b>Comparison</b> raspunde: Care unitate este exceptia? La o solutie "
           "fiecare ART este afisat separat, la un portofoliu fiecare solutie. "
           "Diagramele stau alaturat per metrica.", st),
        _SP(4),
        _H2("5.3  Metricile", st),
        tbl([
            ["Metrica", "Ce arata"],
            ["Flow Velocity", "Debit: itemi finalizati pe perioada/PI."],
            ["Flow Time", "Distributia cycle time (boxplot, scatter cu trend)."],
            ["Flow Distribution", "Distributie pe tip de problema si etape."],
            ["CFD", "Cumulative Flow Diagram (vezi 5.4)."],
            ["Flow Load", "Aging WIP — doar in modul comparison per ART, fiind "
                          "dependent de workflow."],
        ], col_widths=[3.4*cm, 12.1*cm]),
        _SP(6),
        _H2("5.4  CFD peste workflow-uri diferite", st),
        _P("ART-urile diferite au adesea etape de workflow diferite. Pentru un CFD comun, "
           "modulul mapeaza automat fiecare etapa intr-unul din trei <b>grupuri "
           "canonice</b> — <b>To Do</b>, <b>In Progress</b>, <b>Done</b> — si insumeaza "
           "valorile per grup. Astfel CFD ramane comparabil intre ART-uri cu workflow-uri "
           "diferite.", st),
        _SP(6),

        _H2("5.5  Calitatea datelor si increderea", st),
        _P("Sub rezumatul de management, tabelul <b>Data Quality per Source</b> "
           "arata cate un rand pe sursa de date: numarul de inregistrari, "
           "<b>procentul</b> din total, procentul fara First Date, procentul "
           "deschis, daca exista date CFD, actualitatea datelor — si o "
           "<b>incredere</b> tip semafor:", st),
        tbl([
            ["Nivel", "Semnificatie"],
            ["high", "Sursa completa si actuala — cifre de incredere."],
            ["medium", "Peste 10 % fara First Date, fara date CFD sau date mai "
                       "vechi de 30 de zile."],
            ["low", "Fara inregistrari sau peste jumatate fara First Date — "
                    "afirmatiile despre durata s-ar baza pe o minoritate a datelor."],
        ], col_widths=[2.4*cm, 13.1*cm]),
        _P("Titlul tabelului arata <b>gradul de acoperire</b> ('x/y sources "
           "delivered data'). In PDF tabelul este pagina 2. In modul comparison, "
           "<b>valorile aberante</b> sunt marcate suplimentar: celulele Median-CT "
           "si percentila 95 devin rosii cand depasesc de 1,5 ori mediana "
           "coloanei (minim trei unitati).", st),
        _SP(4),
        _H2("5.6  Stage map proprie (optional)", st),
        _P("In locul celor trei grupuri fixe, configuratia solutiei poate defini "
           "propriile stages canonice — un bloc optional <font name='Courier'>"
           "stage_map</font> cu atribuire ordonata a stage-urilor ART si markerii "
           "<font name='Courier'>first_stage</font>/<font name='Courier'>"
           "closed_stage</font> pentru limitele CFD. Stage-urile neatribuite cad "
           "in first_stage cu avertisment; configuratiile fara bloc se comporta "
           "neschimbat.", st),
        _SP(6),

        _H2("5.7  ROAM risk board (optional)", st),
        _P("Daca configuratia solutiei face referire la un registru de riscuri "
           "prin campul <font name='Courier'>risks</font> (JSON cu id, title, "
           "roam, owner, impact, status_since), raportul afiseaza sub tabelul de "
           "calitate un board ROAM: randuri in ordinea R-O-A-M (Resolved / Owned "
           "/ Accepted / Mitigated), cu celule colorate pentru categorie si "
           "impact. Un risc owned care sta in categoria sa mai mult de 30 de "
           "zile primeste o celula Since rosie (aging) — ownership fara miscare "
           "devine vizibil. Un portofoliu agrega registrele tuturor solutiilor "
           "membre si adauga o coloana Solution. Ownerii sunt echipe, nu "
           "persoane. Un fisier lipsa sau defect este logat si sarit; in PDF "
           "board-ul este o pagina proprie.", st),
        _SP(6),

        _H2("5.8  Dashboard NFR/runway (optional)", st),
        _P("Daca configuratia solutiei face referire la un registru NFR prin "
           "campul <font name='Courier'>nfr</font> (JSON cu blocurile nfrs si "
           "runway), raportul afiseaza sub board-ul ROAM doua tabele: NFR-urile "
           "(target/actual/status met, at_risk, violated) si elementele de "
           "architecture runway (status in_place, building, gap cu data "
           "needed_by). Statusurile sunt evaluate de oameni in PI planning/review "
           "— instrumentul nu calculeaza singur target vs. actual. NFR-urile "
           "incalcate si lacunele se sorteaza primele; un element runway cu "
           "needed_by depasit care nu este in place apare ca intarziat (celula "
           "de data rosie). Un portofoliu agrega registrele tuturor solutiilor "
           "membre cu o coloana Solution. Ownerii sunt echipe, nu persoane.", st),
        _SP(6),

        _H2("5.9  Capability map si health (optional)", st),
        _P("Daca configuratia solutiei face referire la o capability map prin "
           "campul <font name='Courier'>capabilities</font> (JSON cu id, title, "
           "health, arts, owner, assessed_on), raportul afiseaza un tabel al "
           "capabilitatilor de business: un semafor de sanatate "
           "healthy/at_risk/critical (critical primul, evaluat de oameni in PI "
           "planning/review) si ART-urile contribuitoare. O capabilitate fara "
           "ART contribuitor este marcata ca uncovered — valoare de business pe "
           "care nimeni nu o livreaza; numele de ART necunoscute produc un "
           "avertisment de drift in log. Un portofoliu agrega hartile tuturor "
           "solutiilor membre cu o coloana Solution. Capability map "
           "(capabilitati de business) nu este stage_map (statusuri de "
           "workflow) — alta dimensiune, alta sursa. Ownerii sunt echipe, nu "
           "persoane.", st),
        _SP(6),

        _H1("6. Linia de comanda (CLI)", st), _hr(st),
        _P("Pentru automatizare si rapoarte reproductibile:", st),
        _CD("python -m portfolio solutia_mea.json --output report.html", st),
        _CD("python -m portfolio solutia_mea.json --mode comparison --pdf report.pdf", st),
        _SP(4),
        tbl([
            ["Optiune", "Semnificatie"],
            ["&lt;config&gt;", "Calea catre configuratia solutiei/portofoliului (JSON)."],
            ["--output FILE", "Scrie raportul HTML in acest fisier."],
            ["--pdf FILE", "Scrie un raport PDF cu mai multe pagini."],
            ["--mode pooled|comparison", "Mod de agregare (implicit: pooled)."],
            ["--metrics ID ...", "Metrici specifice (implicit depinde de mod)."],
            ["--terminology SAFe|Global", "Mod de etichetare (implicit: SAFe)."],
            ["--target-ct DAYS", "Tinta cycle time in zile (implicit: 90)."],
            ["--browser", "Deschide raportul HTML generat in browser."],
        ], col_widths=[5.0*cm, 10.5*cm]),
        _SP(6),

        _H1("7. Intrebari frecvente (FAQ)", st), _hr(st),
        _H2("Trebuie sa reconfigurez ART-urile?", st),
        _P("Nu. Modulul refera template-urile ART existente. Fiecare template ART ramane "
           "sursa unica de adevar.", st),
        _H2("De ce lipseste 'Flow Load' din raportul pooled?", st),
        _P("Flow Load grupeaza dupa etapa curenta. Peste workflow-uri diferite nu este "
           "comparabil, deci apare doar in modul comparison per ART.", st),
        _H2("De ce este procentul Target-CT mic sau apare o liniuta?", st),
        _P("O liniuta inseamna ca nu exista probleme finalizate cu cycle time valid in "
           "perioada. Un procent mic inseamna ca multe probleme dureaza mai mult decat "
           "tinta.", st),
        _H2("Cum creez un portofoliu?", st),
        _P("Salvati mai intai fiecare solutie. Apoi creati o configuratie noua cu Tip = "
           "portfolio si indicati fiecare membru catre un fisier de solutie salvat.", st),
        _SP(6),

        _H1("8. Glosar", st), _hr(st),
        tbl([
            ["Termen", "Explicatie"],
            ["ART", "Agile Release Train — structura multi-echipa in SAFe."],
            ["CFD", "Cumulative Flow Diagram — numarul cumulat de probleme per etapa."],
            ["Cycle Time", "Timpul de la prima etapa activa pana la finalizare."],
            ["PI", "Program Increment — perioada fixa de planificare (8-12 saptamani)."],
            ["Pooling", "Unirea mai multor seturi de date la nivel de problema."],
            ["WIP", "Work in Progress — probleme deschise, nefinalizate."],
        ], col_widths=[3.0*cm, 12.5*cm]),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – Portuguese
# ---------------------------------------------------------------------------

def content_pt(st: dict) -> list:
    story = [NextPageTemplate("normal"), PageBreak()]
    story += [
        _H1("1. O que e 'Solutions &amp; Portfolios'?", st), _hr(st),
        _P("Ate agora o SituationReport analisava sempre <b>um</b> grupo de equipas ou "
           "ART. O modulo <b>Solutions &amp; Portfolios</b> (tecnicamente: "
           "<font name='Courier'>portfolio</font>) combina varios ARTs ja configurados "
           "num relatorio comum — ao nivel de <b>Large Solution</b> ou <b>portefolio</b>.", st),
        _P("Configura cada ART uma vez, como habitual (em build_reports, como template de "
           "projeto). Depois indica apenas quais ARTs pertencem a uma solucao — e obtem "
           "um relatorio agregado de todos.", st),
        _box("Em resumo: uma <b>solucao</b> = varios ARTs combinados. Um "
             "<b>portefolio</b> = varias solucoes combinadas. Os relatorios ART nao "
             "mudam; sao apenas referenciados.", st),
        _SP(6),

        _H1("2. Conceitos-chave", st), _hr(st),
        tbl([
            ["Termo", "Significado"],
            ["ART", "Agile Release Train / grupo de equipas — o nivel que ja analisa hoje "
                    "em build_reports."],
            ["Solucao", "Um agrupamento de varios ARTs. Refere os templates deles."],
            ["Portefolio", "Um agrupamento de varias solucoes (aninhado: portefolio &gt; "
                           "solucoes &gt; ARTs)."],
            ["Template", "Uma configuracao guardada. Os ARTs sao incluidos pelo seu "
                         "template build_reports; uma solucao pode ser guardada como "
                         "template e referenciada por um portefolio."],
            ["Pooled", "Modo: todos os itens sao unidos num <b>unico</b> conjunto — a "
                       "solucao vista como um sistema."],
            ["Comparison", "Modo: cada unidade (ART ou solucao) e mostrada em separado, "
                           "lado a lado."],
        ], col_widths=[3.2*cm, 12.3*cm]),
        _SP(6),

        _H1("3. Iniciar", st), _hr(st),
        _H2("3.1  A partir do launcher", st),
        _P("Inicie o SituationReport. O ecra inicial esta dividido: <b>a esquerda</b> "
           "'Large Solutions &amp; Portfolios', <b>a direita</b> as ferramentas ART "
           "conhecidas. Clique no cartao <b>Solutions &amp; Portfolios</b> a esquerda.", st),
        _H2("3.2  Diretamente", st),
        _P("Em alternativa, sem o launcher:", st),
        _CD("python -m portfolio", st),
        _HI("Sem argumentos abre a interface grafica. Com argumentos corre a interface "
            "de linha de comandos (ver seccao 6).", st),
        _SP(6),

        _H1("4. A interface passo a passo", st), _hr(st),
        *_gui_figure(st, "Fig. 1: A interface Solutions &amp; Portfolios."),
        tbl([
            ["Campo / acao", "Descricao"],
            ["Nome", "Nome da solucao ou portefolio (aparece no relatorio)."],
            ["Terminologia", "SAFe ou Global — rotulagem das metricas do relatorio."],
            ["Tipo", "<b>solution</b> (membros sao ARTs) ou <b>portfolio</b> (membros "
                     "sao solucoes)."],
            ["De / Ate", "Periodo de relatorio opcional (AAAA-MM-DD)."],
            ["Adicionar ART", "Uma linha por membro: nome + origem. Em 'solution' a "
                              "origem e um template ART (.json) ou diretamente um "
                              "IssueTimes.xlsx; em 'portfolio' um template de solucao (.json)."],
            ["Procurar", "Escolher o ficheiro de origem."],
            ["Modo de relatorio", "Pooled ou Comparison (ver seccao 5)."],
            ["Guardar", "Guardar a configuracao como JSON (= template reutilizavel)."],
            ["Carregar", "Abrir uma configuracao guardada."],
            ["Gerar relatorio", "Cria o relatorio. Extensao <b>.html</b> = pagina web, "
                                "<b>.pdf</b> = PDF. Abre de seguida."],
        ], col_widths=[3.6*cm, 11.9*cm]),
        _SP(4),
        _box("Dica: um ficheiro de solucao guardado e o seu <b>template de solucao</b>. "
             "Para um portefolio, escolha Tipo = portfolio e aponte cada membro para um "
             "ficheiro de solucao guardado.", st),
        _SP(6),

        _H1("5. O relatorio", st), _hr(st),
        _H2("5.1  Resumo de gestao", st),
        _P("No topo esta uma tabela compacta de indicadores — uma linha por unidade (no "
           "modo pooled, uma unica linha para toda a solucao/portefolio):", st),
        tbl([
            ["Indicador", "Significado"],
            ["Items", "Numero de itens no periodo."],
            ["Completed", "Destes, os concluidos."],
            ["Open (WIP)", "Itens abertos (ainda em curso)."],
            ["Median / 85th / 95th CT", "Cycle time em dias — mediana e percentis 85 e 95."],
            ["&lt;= Nd", "Percentagem de itens concluidos dentro do alvo (Target CT, "
                         "predefinicao 90 dias)."],
            ["Median / 85th LT", "Lead time end-to-end (Created ate Closed) em dias — no "
                                 "modo pooled, o lead time da solucao em todos os ARTs."],
        ], col_widths=[4.2*cm, 11.3*cm]),
        _SP(6),
        _H2("5.2  Pooled vs. comparison", st),
        _P("<b>Pooled</b> responde: Como esta a solucao no conjunto? Todos os itens "
           "sao unidos e analisados em conjunto.", st),
        _P("<b>Comparison</b> responde: Que unidade e a excecao? Numa solucao cada "
           "ART e mostrado em separado, num portefolio cada solucao. Os graficos ficam "
           "lado a lado por metrica.", st),
        _SP(4),
        _H2("5.3  As metricas", st),
        tbl([
            ["Metrica", "O que mostra"],
            ["Flow Velocity", "Throughput: itens concluidos por periodo/PI."],
            ["Flow Time", "Distribuicao do cycle time (boxplot, scatter com tendencia)."],
            ["Flow Distribution", "Distribuicao por tipo de item e etapas."],
            ["CFD", "Cumulative Flow Diagram (ver 5.4)."],
            ["Flow Load", "Aging WIP — so no modo comparison por ART, por depender do "
                          "workflow."],
        ], col_widths=[3.4*cm, 12.1*cm]),
        _SP(6),
        _H2("5.4  CFD em workflows diferentes", st),
        _P("ARTs diferentes tem muitas vezes etapas de workflow diferentes. Para um CFD "
           "comum, o modulo mapeia automaticamente cada etapa para um de tres "
           "<b>grupos canonicos</b> — <b>To Do</b>, <b>In Progress</b>, <b>Done</b> — e "
           "soma os valores por grupo. Assim o CFD permanece comparavel entre ARTs com "
           "workflows diferentes.", st),
        _SP(6),

        _H2("5.5  Qualidade dos dados e confianca", st),
        _P("Abaixo do resumo de gestao, a tabela <b>Data Quality per Source</b> "
           "mostra uma linha por fonte de dados: numero de registos, a sua "
           "<b>quota</b> do total, a percentagem sem First Date, a percentagem "
           "aberta, se ha dados CFD, a atualidade dos dados — e uma "
           "<b>confianca</b> tipo semaforo:", st),
        tbl([
            ["Nivel", "Significado"],
            ["high", "Fonte completa e atual — numeros fiaveis."],
            ["medium", "Mais de 10 % sem First Date, sem dados CFD ou dados com "
                       "mais de 30 dias."],
            ["low", "Sem registos, ou mais de metade sem First Date — afirmacoes "
                    "sobre o tempo de ciclo assentariam numa minoria dos dados."],
        ], col_widths=[2.4*cm, 13.1*cm]),
        _P("O titulo da tabela mostra o <b>grau de cobertura</b> ('x/y sources "
           "delivered data'). No PDF a tabela e a pagina 2. No modo comparison, "
           "os <b>outliers</b> sao adicionalmente marcados: as celulas Median-CT "
           "e do percentil 95 ficam vermelhas quando excedem 1,5x a mediana da "
           "coluna (minimo tres unidades).", st),
        _SP(4),
        _H2("5.6  Stage map propria (opcional)", st),
        _P("Em vez dos tres grupos fixos, a configuracao da solucao pode definir "
           "os seus proprios stages canonicos — um bloco opcional <font "
           "name='Courier'>stage_map</font> com atribuicao ordenada dos stages "
           "dos ARTs e os marcadores <font name='Courier'>first_stage</font>/"
           "<font name='Courier'>closed_stage</font> para os limites do CFD. "
           "Stages nao atribuidos caem em first_stage com aviso; configuracoes "
           "sem o bloco comportam-se sem alteracoes.", st),
        _SP(6),

        _H2("5.7  ROAM risk board (opcional)", st),
        _P("Se a configuracao da solution referenciar um registo de riscos "
           "atraves do campo <font name='Courier'>risks</font> (JSON com id, "
           "title, roam, owner, impact, status_since), o relatorio mostra por "
           "baixo da tabela de qualidade um board ROAM: linhas na ordem R-O-A-M "
           "(Resolved / Owned / Accepted / Mitigated), com celulas coloridas de "
           "categoria e impacto. Um risco owned que fica na sua categoria mais "
           "de 30 dias recebe uma celula Since vermelha (aging) — ownership sem "
           "movimento torna-se visivel. Um portfolio agrega os registos de todas "
           "as solutions membros e acrescenta uma coluna Solution. Os owners sao "
           "equipas, nao pessoas. Um ficheiro em falta ou invalido e registado "
           "no log e ignorado; no PDF o board e uma pagina propria.", st),
        _SP(6),

        _H2("5.8  Dashboard NFR/runway (opcional)", st),
        _P("Se a configuracao da solution referenciar um registo NFR atraves do "
           "campo <font name='Courier'>nfr</font> (JSON com os blocos nfrs e "
           "runway), o relatorio mostra por baixo do board ROAM duas tabelas: os "
           "NFRs (target/actual/status met, at_risk, violated) e os elementos de "
           "architecture runway (status in_place, building, gap com data "
           "needed_by). Os status sao avaliados por pessoas no PI planning/review "
           "— a ferramenta nao calcula target vs. actual por si. NFRs violados e "
           "lacunas ordenam primeiro; um elemento runway com needed_by "
           "ultrapassado que nao esta in place aparece como atrasado (celula de "
           "data vermelha). Um portfolio agrega os registos de todas as "
           "solutions membros com uma coluna Solution. Os owners sao equipas, "
           "nao pessoas.", st),
        _SP(6),

        _H2("5.9  Capability map e health (opcional)", st),
        _P("Se a configuracao da solution referenciar uma capability map "
           "atraves do campo <font name='Courier'>capabilities</font> (JSON com "
           "id, title, health, arts, owner, assessed_on), o relatorio mostra "
           "uma tabela das capacidades de negocio: um semaforo de saude "
           "healthy/at_risk/critical (critical primeiro, avaliado por pessoas "
           "no PI planning/review) e os ARTs contribuintes. Uma capacidade sem "
           "ART contribuinte e marcada como uncovered — valor de negocio que "
           "ninguem entrega; nomes de ART desconhecidos produzem um aviso de "
           "drift no log. Um portfolio agrega os mapas de todas as solutions "
           "membros com uma coluna Solution. A capability map (capacidades de "
           "negocio) nao e a stage_map (estados de workflow) — outra dimensao, "
           "outra fonte. Os owners sao equipas, nao pessoas.", st),
        _SP(6),

        _H1("6. Linha de comandos (CLI)", st), _hr(st),
        _P("Para automacao e relatorios reproduziveis:", st),
        _CD("python -m portfolio a_minha_solucao.json --output report.html", st),
        _CD("python -m portfolio a_minha_solucao.json --mode comparison --pdf report.pdf", st),
        _SP(4),
        tbl([
            ["Opcao", "Significado"],
            ["&lt;config&gt;", "Caminho para a configuracao da solucao/portefolio (JSON)."],
            ["--output FILE", "Escrever o relatorio HTML neste ficheiro."],
            ["--pdf FILE", "Escrever um relatorio PDF com varias paginas."],
            ["--mode pooled|comparison", "Modo de agregacao (predefinicao: pooled)."],
            ["--metrics ID ...", "Metricas especificas (predefinicao depende do modo)."],
            ["--terminology SAFe|Global", "Modo de rotulagem (predefinicao: SAFe)."],
            ["--target-ct DAYS", "Alvo do cycle time em dias (predefinicao: 90)."],
            ["--browser", "Abrir o relatorio HTML gerado no browser."],
        ], col_widths=[5.0*cm, 10.5*cm]),
        _SP(6),

        _H1("7. Perguntas frequentes (FAQ)", st), _hr(st),
        _H2("Tenho de reconfigurar os ARTs?", st),
        _P("Nao. O modulo referencia os templates ART existentes. Cada template ART "
           "continua a ser a unica fonte de verdade.", st),
        _H2("Porque falta o 'Flow Load' no relatorio pooled?", st),
        _P("O Flow Load agrupa pela etapa atual. Entre workflows diferentes nao e "
           "comparavel, por isso aparece apenas no modo comparison por ART.", st),
        _H2("Porque e a percentagem Target-CT baixa ou aparece um traco?", st),
        _P("Um traco significa que nao ha itens concluidos com cycle time valido no "
           "periodo. Uma percentagem baixa significa que muitos itens demoram mais do "
           "que o alvo.", st),
        _H2("Como crio um portefolio?", st),
        _P("Guarde primeiro cada solucao. Depois crie uma configuracao nova com Tipo = "
           "portfolio e aponte cada membro para um ficheiro de solucao guardado.", st),
        _SP(6),

        _H1("8. Glossario", st), _hr(st),
        tbl([
            ["Termo", "Explicacao"],
            ["ART", "Agile Release Train — estrutura multi-equipa no SAFe."],
            ["CFD", "Cumulative Flow Diagram — contagem cumulativa de itens por etapa."],
            ["Cycle Time", "Tempo desde a primeira etapa ativa ate a conclusao."],
            ["PI", "Program Increment — periodo fixo de planeamento (8-12 semanas)."],
            ["Pooling", "Unir varios conjuntos de dados ao nivel do item."],
            ["WIP", "Work in Progress — itens abertos, ainda nao concluidos."],
        ], col_widths=[3.0*cm, 12.5*cm]),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – French
# ---------------------------------------------------------------------------

def content_fr(st: dict) -> list:
    story = [NextPageTemplate("normal"), PageBreak()]
    story += [
        _H1("1. Qu'est-ce que 'Solutions &amp; Portfolios' ?", st), _hr(st),
        _P("Jusqu'a present, SituationReport analysait toujours <b>un</b> groupe "
           "d'equipes ou ART. Le module <b>Solutions &amp; Portfolios</b> (techniquement : "
           "<font name='Courier'>portfolio</font>) combine plusieurs ARTs deja configures "
           "en un rapport commun — au niveau <b>Large Solution</b> ou <b>portefeuille</b>.", st),
        _P("Vous configurez chaque ART une fois, comme d'habitude (dans build_reports, "
           "comme template de projet). Ensuite vous indiquez seulement quels ARTs "
           "appartiennent a une solution — et obtenez un rapport agrege sur l'ensemble.", st),
        _box("En bref : une <b>solution</b> = plusieurs ARTs combines. Un "
             "<b>portefeuille</b> = plusieurs solutions combinees. Les rapports ART "
             "eux-memes ne changent pas ; ils sont seulement references.", st),
        _SP(6),

        _H1("2. Notions cles", st), _hr(st),
        tbl([
            ["Terme", "Signification"],
            ["ART", "Agile Release Train / groupe d'equipes — le niveau que vous "
                    "analysez deja dans build_reports."],
            ["Solution", "Un regroupement de plusieurs ARTs. Reference leurs templates."],
            ["Portefeuille", "Un regroupement de plusieurs solutions (imbrique : "
                             "portefeuille &gt; solutions &gt; ARTs)."],
            ["Template", "Une configuration enregistree. Les ARTs sont inclus via leur "
                         "template build_reports ; une solution peut elle-meme etre "
                         "enregistree comme template et referencee par un portefeuille."],
            ["Pooled", "Mode : tous les tickets sont fusionnes en <b>un seul</b> jeu — la "
                       "solution vue comme un systeme."],
            ["Comparison", "Mode : chaque unite (ART ou solution) est affichee separement, "
                           "cote a cote."],
        ], col_widths=[3.2*cm, 12.3*cm]),
        _SP(6),

        _H1("3. Demarrage", st), _hr(st),
        _H2("3.1  Depuis le launcher", st),
        _P("Demarrez SituationReport. L'ecran d'accueil est divise : <b>a gauche</b> "
           "'Large Solutions &amp; Portfolios', <b>a droite</b> les outils ART connus. "
           "Cliquez sur la carte <b>Solutions &amp; Portfolios</b> a gauche.", st),
        _H2("3.2  Directement", st),
        _P("Sinon, sans le launcher :", st),
        _CD("python -m portfolio", st),
        _HI("Sans argument, l'interface graphique s'ouvre. Avec des arguments, "
            "l'interface en ligne de commande s'execute (voir section 6).", st),
        _SP(6),

        _H1("4. L'interface pas a pas", st), _hr(st),
        *_gui_figure(st, "Fig. 1 : L'interface Solutions &amp; Portfolios."),
        tbl([
            ["Champ / action", "Description"],
            ["Nom", "Nom de la solution ou du portefeuille (apparait dans le rapport)."],
            ["Terminologie", "SAFe ou Global — etiquetage des metriques du rapport."],
            ["Type", "<b>solution</b> (les membres sont des ARTs) ou <b>portfolio</b> "
                     "(les membres sont des solutions)."],
            ["De / A", "Periode de rapport optionnelle (AAAA-MM-JJ)."],
            ["Ajouter un ART", "Une ligne par membre : nom + source. En 'solution' la "
                               "source est un template ART (.json) ou directement un "
                               "IssueTimes.xlsx ; en 'portfolio' un template de solution (.json)."],
            ["Parcourir", "Choisir le fichier source."],
            ["Mode de rapport", "Pooled ou Comparison (voir section 5)."],
            ["Enregistrer", "Enregistrer la configuration en JSON (= template reutilisable)."],
            ["Charger", "Ouvrir une configuration enregistree."],
            ["Generer le rapport", "Construit le rapport. Extension <b>.html</b> = page "
                                   "web, <b>.pdf</b> = PDF. Il s'ouvre ensuite."],
        ], col_widths=[3.6*cm, 11.9*cm]),
        _SP(4),
        _box("Astuce : un fichier de solution enregistre est votre <b>template de "
             "solution</b>. Pour un portefeuille, choisissez Type = portfolio et pointez "
             "chaque membre vers un tel fichier de solution enregistre.", st),
        _SP(6),

        _H1("5. Le rapport", st), _hr(st),
        _H2("5.1  Synthese de management", st),
        _P("Tout en haut figure un tableau d'indicateurs compact — une ligne par unite "
           "(en mode pooled, une seule ligne pour toute la solution/portefeuille) :", st),
        tbl([
            ["Indicateur", "Signification"],
            ["Items", "Nombre de tickets sur la periode."],
            ["Completed", "Parmi eux, les termines."],
            ["Open (WIP)", "Tickets ouverts (encore en cours)."],
            ["Median / 85th / 95th CT", "Cycle time en jours — mediane plus 85e et 95e "
                                        "percentile."],
            ["&lt;= Nd", "Part des tickets termines dans la cible (Target CT, defaut "
                         "90 jours)."],
            ["Median / 85th LT", "Lead time de bout en bout (Created a Closed) en jours — en "
                                 "mode pooled, le lead time de la solution sur tous les ARTs."],
        ], col_widths=[4.2*cm, 11.3*cm]),
        _SP(6),
        _H2("5.2  Pooled vs. comparison", st),
        _P("<b>Pooled</b> repond : Comment va la solution dans son ensemble ? Tous "
           "les tickets sont fusionnes et analyses ensemble.", st),
        _P("<b>Comparison</b> repond : Quelle unite est l'exception ? Pour une "
           "solution chaque ART est montre separement, pour un portefeuille chaque "
           "solution. Les graphiques sont cote a cote par metrique.", st),
        _SP(4),
        _H2("5.3  Les metriques", st),
        tbl([
            ["Metrique", "Ce qu'elle montre"],
            ["Flow Velocity", "Debit : items termines par periode/PI."],
            ["Flow Time", "Distribution du cycle time (boxplot, scatter avec tendance)."],
            ["Flow Distribution", "Repartition par type de ticket et par etape."],
            ["CFD", "Cumulative Flow Diagram (voir 5.4)."],
            ["Flow Load", "Aging WIP — uniquement en mode comparison par ART, car "
                          "dependant du workflow."],
        ], col_widths=[3.4*cm, 12.1*cm]),
        _SP(6),
        _H2("5.4  CFD sur des workflows differents", st),
        _P("Des ARTs differents ont souvent des etapes de workflow differentes. Pour "
           "permettre un CFD commun, le module mappe automatiquement chaque etape vers "
           "l'un de trois <b>groupes canoniques</b> — <b>To Do</b>, <b>In Progress</b>, "
           "<b>Done</b> — et additionne les valeurs par groupe. Le CFD reste ainsi "
           "comparable entre ARTs aux workflows differents.", st),
        _SP(6),

        _H2("5.5  Qualite des donnees et confiance", st),
        _P("Sous le resume de gestion, le tableau <b>Data Quality per Source</b> "
           "montre une ligne par source de donnees : nombre d'enregistrements, sa "
           "<b>part</b> du total, la part sans First Date, la part ouverte, la "
           "presence de donnees CFD, la fraicheur des donnees — et une "
           "<b>confiance</b> de type feu tricolore :", st),
        tbl([
            ["Niveau", "Signification"],
            ["high", "Source complete et a jour — chiffres fiables."],
            ["medium", "Plus de 10 % sans First Date, pas de donnees CFD ou "
                       "donnees de plus de 30 jours."],
            ["low", "Aucun enregistrement, ou plus de la moitie sans First Date — "
                    "les enonces de duree reposeraient sur une minorite des donnees."],
        ], col_widths=[2.4*cm, 13.1*cm]),
        _P("Le titre du tableau indique le <b>taux de couverture</b> ('x/y sources "
           "delivered data'). Dans le PDF, le tableau est la page 2. En mode "
           "comparison, les <b>valeurs aberrantes</b> sont en outre marquees : les "
           "cellules Median-CT et 95e percentile passent au rouge quand elles "
           "depassent 1,5x la mediane de la colonne (trois unites minimum).", st),
        _SP(4),
        _H2("5.6  Stage map personnalisee (optionnelle)", st),
        _P("Au lieu des trois groupes fixes, la configuration de la solution peut "
           "definir ses propres stages canoniques — un bloc optionnel <font "
           "name='Courier'>stage_map</font> avec une attribution ordonnee des "
           "stages ART et les marqueurs <font name='Courier'>first_stage</font>/"
           "<font name='Courier'>closed_stage</font> pour les limites du CFD. Les "
           "stages non attribues tombent dans first_stage avec un avertissement ; "
           "les configurations sans le bloc se comportent sans changement.", st),
        _SP(6),

        _H2("5.7  ROAM risk board (optionnel)", st),
        _P("Si la configuration de la solution reference un registre de risques "
           "via le champ <font name='Courier'>risks</font> (JSON avec id, title, "
           "roam, owner, impact, status_since), le rapport affiche sous le "
           "tableau de qualite un board ROAM : lignes dans l'ordre R-O-A-M "
           "(Resolved / Owned / Accepted / Mitigated), avec cellules colorees "
           "pour la categorie et l'impact. Un risque owned qui reste dans sa "
           "categorie plus de 30 jours recoit une cellule Since rouge (aging) — "
           "l'ownership sans mouvement devient visible. Un portefeuille agrege "
           "les registres de toutes les solutions membres et ajoute une colonne "
           "Solution. Les owners sont des equipes, pas des personnes. Un fichier "
           "manquant ou invalide est journalise et ignore ; dans le PDF, le "
           "board est une page a part.", st),
        _SP(6),

        _H2("5.8  Dashboard NFR/runway (optionnel)", st),
        _P("Si la configuration de la solution reference un registre NFR via le "
           "champ <font name='Courier'>nfr</font> (JSON avec les blocs nfrs et "
           "runway), le rapport affiche sous le board ROAM deux tableaux : les "
           "NFR (target/actual/status met, at_risk, violated) et les elements de "
           "l'architecture runway (status in_place, building, gap avec une date "
           "needed_by). Les statuts sont evalues par des personnes en PI "
           "planning/review — l'outil ne calcule pas lui-meme target vs. actual. "
           "Les NFR violes et les lacunes se classent en premier ; un element "
           "runway dont needed_by est depasse sans etre in place apparait en "
           "retard (cellule de date rouge). Un portefeuille agrege les registres "
           "de toutes les solutions membres avec une colonne Solution. Les "
           "owners sont des equipes, pas des personnes.", st),
        _SP(6),

        _H2("5.9  Capability map et health (optionnel)", st),
        _P("Si la configuration de la solution reference une capability map via "
           "le champ <font name='Courier'>capabilities</font> (JSON avec id, "
           "title, health, arts, owner, assessed_on), le rapport affiche un "
           "tableau des capacites metier : un feu de sante "
           "healthy/at_risk/critical (critical en premier, evalue par des "
           "personnes en PI planning/review) et les ARTs contributeurs. Une "
           "capacite sans ART contributeur est marquee uncovered — de la valeur "
           "metier que personne ne livre ; des noms d'ART inconnus produisent "
           "un avertissement de derive dans le log. Un portefeuille agrege les "
           "cartes de toutes les solutions membres avec une colonne Solution. "
           "La capability map (capacites metier) n'est pas la stage_map "
           "(statuts de workflow) — autre dimension, autre source. Les owners "
           "sont des equipes, pas des personnes.", st),
        _SP(6),

        _H1("6. Ligne de commande (CLI)", st), _hr(st),
        _P("Pour l'automatisation et des rapports reproductibles :", st),
        _CD("python -m portfolio ma_solution.json --output report.html", st),
        _CD("python -m portfolio ma_solution.json --mode comparison --pdf report.pdf", st),
        _SP(4),
        tbl([
            ["Option", "Signification"],
            ["&lt;config&gt;", "Chemin vers la configuration solution/portefeuille (JSON)."],
            ["--output FILE", "Ecrire le rapport HTML dans ce fichier."],
            ["--pdf FILE", "Ecrire un rapport PDF multi-pages."],
            ["--mode pooled|comparison", "Mode d'agregation (defaut : pooled)."],
            ["--metrics ID ...", "Metriques specifiques (defaut selon le mode)."],
            ["--terminology SAFe|Global", "Mode d'etiquetage (defaut : SAFe)."],
            ["--target-ct DAYS", "Cible du cycle time en jours (defaut : 90)."],
            ["--browser", "Ouvrir le rapport HTML genere dans le navigateur."],
        ], col_widths=[5.0*cm, 10.5*cm]),
        _SP(6),

        _H1("7. Questions frequentes (FAQ)", st), _hr(st),
        _H2("Dois-je reconfigurer les ARTs ?", st),
        _P("Non. Le module reference les templates ART existants. Chaque template ART "
           "reste la source unique de verite.", st),
        _H2("Pourquoi 'Flow Load' manque-t-il dans le rapport pooled ?", st),
        _P("Flow Load regroupe par etape actuelle. Entre workflows differents ce n'est "
           "pas comparable, il n'apparait donc qu'en mode comparison par ART.", st),
        _H2("Pourquoi la part Target-CT est-elle faible ou affiche un tiret ?", st),
        _P("Un tiret signifie qu'il n'y a pas de tickets termines avec un cycle time "
           "valide sur la periode. Un pourcentage faible signifie que beaucoup de tickets "
           "depassent la cible.", st),
        _H2("Comment creer un portefeuille ?", st),
        _P("Enregistrez d'abord chaque solution. Creez ensuite une nouvelle configuration "
           "avec Type = portfolio et pointez chaque membre vers un fichier de solution "
           "enregistre.", st),
        _SP(6),

        _H1("8. Glossaire", st), _hr(st),
        tbl([
            ["Terme", "Explication"],
            ["ART", "Agile Release Train — structure multi-equipes dans SAFe."],
            ["CFD", "Cumulative Flow Diagram — nombre cumule de tickets par etape."],
            ["Cycle Time", "Temps de la premiere etape active jusqu'a l'achevement."],
            ["PI", "Program Increment — periode de planification fixe (8-12 semaines)."],
            ["Pooling", "Fusion de plusieurs jeux de donnees au niveau du ticket."],
            ["WIP", "Work in Progress — tickets ouverts, non termines."],
        ], col_widths=[3.0*cm, 12.5*cm]),
    ]
    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate the portfolio (Solutions & Portfolios) user manual PDFs in all 5 languages."""
    st = make_styles()
    for lang, output, content_fn in [
        (LANG_DE, OUTPUT_DE, content_de),
        (LANG_EN, OUTPUT_EN, content_en),
        (LANG_RO, OUTPUT_RO, content_ro),
        (LANG_PT, OUTPUT_PT, content_pt),
        (LANG_FR, OUTPUT_FR, content_fr),
    ]:
        doc = _PortfolioDoc(str(output), lang=lang)
        story = content_fn(st)
        doc.multiBuild(story)
        print(f"PDF erstellt: {output}")


if __name__ == "__main__":
    main()
