# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für testdata_generator als PDF in fünf
#   Sprachen: DE, EN, RO, PT, FR. Beschreibt Start, Workflow-Datei,
#   Parameter, Flow-Antipattern-Muster und vollständiges ART_A-Beispiel.
# =============================================================================

import sys
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
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

from version import __version__ as _VERSION

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
OUTPUT_RO = Path(__file__).parent / "testdata_generator_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "testdata_generator_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "testdata_generator_ManuelUtilisateur.pdf"

_ASSETS = Path(__file__).parent / "assets"
CONTENT_WIDTH = 15.5 * cm

C_BLUE   = colors.HexColor("#2c3e50")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")
_TBL_HDR_STYLE = ParagraphStyle(
    "TblHdr_testdata",
    fontName=_FB, fontSize=9, textColor=C_WHITE, leading=12,
)
_TBL_CELL_STYLE = ParagraphStyle(
    "TblCell_testdata",
    fontName=_FN, fontSize=9, leading=12,
)


_HEADER = {
    "de": "testdata_generator  --  Benutzerhandbuch",
    "en": "testdata_generator  --  User Manual",
    "ro": "testdata_generator  --  Manual de Utilizator",
    "pt": "testdata_generator  --  Manual do Utilizador",
    "fr": "testdata_generator  --  Manuel d'utilisation",
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
    "de": "Synthetische Jira-Issue-Daten für SituationReport erzeugen",
    "en": "Generate synthetic Jira issue data for SituationReport",
    "ro": "Generați date sintetice de probleme Jira pentru SituationReport",
    "pt": "Gerar dados sintéticos de issues Jira para SituationReport",
    "fr": "Générer des données de tickets Jira synthétiques pour SituationReport",
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
        h1=s("TDG_H1", fontName=_FB, fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8, keepWithNext=1),
        h2=s("TDG_H2", fontName=_FB, fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5, keepWithNext=1),
        h3=s("TDG_H3", fontName=_FBI, fontSize=11, textColor=C_BLUE,
              spaceBefore=10, spaceAfter=4, keepWithNext=1),
        body=s("TDG_Body", fontName=_FN, fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("TDG_Bullet", fontName=_FN, fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3, bulletIndent=4),
        code=s("TDG_Code", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("TDG_Hint", fontName=_FI, fontSize=9, textColor=C_HINT,
               leading=13, leftIndent=12, spaceAfter=4),
        caption=s("TDG_Caption", fontName=_FI, fontSize=8,
                  textColor=C_HINT, leading=11, alignment=TA_CENTER, spaceAfter=8),
    )


# ---------------------------------------------------------------------------
# Page template
# ---------------------------------------------------------------------------

class _TDGDoc(BaseDocTemplate):

    def __init__(self, filename: str, lang: str = "en", **kw):
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
        canvas.setFont(_FB, 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2 * cm, h - 0.7 * cm, self._header_text)
        canvas.drawRightString(w - 2.2 * cm, h - 0.7 * cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont(_FN, 8)
        canvas.drawCentredString(w / 2, 1.0 * cm, _PAGE_LABEL[self._lang] % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2 * cm, 1.4 * cm, w - 2.2 * cm, 1.4 * cm)
        canvas.restoreState()


def _build_cover(canvas, doc, lang: str = "en"):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h * 0.35, w, h * 0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont(_FB, 28)
    canvas.drawCentredString(w / 2, h * 0.62, "SituationReport")
    canvas.setFont(_FB, 20)
    canvas.drawCentredString(w / 2, h * 0.57, "testdata_generator")
    canvas.setFont(_FB, 16)
    canvas.drawCentredString(w / 2, h * 0.515, _COVER_SUBTITLE[lang])
    canvas.setFont(_FN, 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w / 2, h * 0.47, _COVER_TAGLINE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w * 0.2, h * 0.44, w * 0.8, h * 0.44)
    canvas.setFont(_FN, 9)
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


def img(filename: str, width_cm: float, caption_text: str | None = None,
        st: dict | None = None) -> list:
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


def tbl(headers, rows, col_widths=None):
    def _w(val, sty):
        return Paragraph(str(val), sty) if not isinstance(val, Paragraph) else val
    data = (
        [[_w(h, _TBL_HDR_STYLE) for h in headers]]
        + [[_w(c, _TBL_CELL_STYLE) for c in row] for row in rows]
    )
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  C_BLUE),
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
                "Entwicklung), das echte Daten direkt aus Jira lädt. Für den manuellen "
                "Export echter Jira-Daten steht das <b>Benutzerhandbuch Get Data</b> "
                "zur Verfügung.", st)]

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
                    "Seed für reproduzierbare Ausgabe (optional)"],
                   ["--mean-cycle-days FLOAT",  "(keiner)",
                    "Mittlere Cycle-Time in Tagen (lognormal); aktiviert CT-Steuerung"],
                   ["--std-cycle-days FLOAT",   "(30 % des Mittels)",
                    "Standardabweichung der Cycle-Time in Tagen"],
                   ["--pattern MUSTER",         "none",
                    "Flow-Antipattern: none / triangle / flat_triangle / cluster / batch"],
                   ["--pi-duration-weeks INT",  "12",
                    "PI-Zyklus-Länge in Wochen (für cluster/batch)"],
                   ["--pattern-strength 0-100", "50",
                    "Muster-Intensität 0–100 (0=subtil, 50=Standard, 100=stark)"]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm]),
              SP(8),
              box("<b>Tipp: Reproduzierbare Ergebnisse</b><br/>"
                  "Mit einem festen Seed (z. B. <font name='Courier'>--seed 42</font>) "
                  "erzeugt der Generator bei gleichen Parametern immer dieselbe "
                  "JSON-Datei — ideal für Demos, bei denen alle Teilnehmer "
                  "dieselben Ergebnisse sehen sollen.", st)]

    story += [PageBreak(),
              H1("4b  Flow-Antipattern-Muster", st), HR(),
              P("Ab Version 0.9.9 kann der Testdata Generator typische Flow-Antipatterns "
                "aus der Literatur von Vacanti und Singh simulieren. Dazu wird "
                "<b>--mean-cycle-days</b> mit <b>--pattern</b> kombiniert. In der GUI "
                "stehen Radiobuttons und Schieberegler zur Verfügung.", st),
              SP(4),
              tbl(["Muster", "Scatterplot-Erscheinung", "Beschreibung"],
                  [["none",
                    "Gleichmäßige Punktwolke",
                    "Zufällige Cycle-Time ohne Trend — Standard-Verhalten"],
                   ["triangle",
                    "Dreieck: rechter Winkel unten rechts",
                    "Cycle-Time steigt linear über die Zeit (Multiplikator ~1–4× bei "
                    "Standard-Stärke, höher mit --pattern-strength). "
                    "Zeigt einen Prozess, der zunehmend langsamer wird."],
                   ["flat_triangle",
                    "Dreieck, Anstieg flacht am Ende ab",
                    "Wie triangle, aber der Anstieg verflacht durch tanh(2.5×t). "
                    "Zeigt eine Prozessverschlechterung, die sich stabilisiert."],
                   ["cluster",
                    "Senkrechte Punkthäufungen am PI-Ende",
                    "Cycle-Time bleibt stabil (lognormal), aber die meisten Issues "
                    "werden in den letzten 2 Wochen vor PI-Ende abgeschlossen. "
                    "Deadline-getriebenes Verhalten."],
                   ["batch",
                    "Säulen variabler Höhe am PI-Ende",
                    "Wie cluster, aber mit stark unterschiedlicher Cycle-Time "
                    "(0.1× bis 3× Mittelwert). Zeigt, dass kurze und sehr lange "
                    "Aufgaben gemeinsam ans PI-Ende geschoben werden."]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(8),
              H2("Cycle-Time-Steuerung", st),
              P("Wenn <b>--mean-cycle-days</b> angegeben ist, wird die Cycle-Time "
                "lognormalverteilt mit dem angegebenen Mittelwert erzeugt.", st),
              tbl(["Parameter", "Bedeutung"],
                  [["--mean-cycle-days",
                    "Mittelwert der Cycle-Time in Tagen (z. B. 20). "
                    "Pflicht für alle Muster außer none."],
                   ["--std-cycle-days",
                    "Standardabweichung in Tagen (Standard: 30 % des Mittelwerts). "
                    "Höhere Werte erzeugen breitere Streuung im Scatterplot."],
                   ["--pi-duration-weeks",
                    "Länge eines PI-Zyklus in Wochen (Standard 12). "
                    "Nur relevant für cluster und batch."]],
                  col_widths=[4.5 * cm, 11.0 * cm]),
              SP(8),
              H2("Beispiele", st),
              PRE("# Triangle-Muster: CT steigt von 20d auf 80d\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern triangle \\\n"
                  "    --mean-cycle-days 20 --std-cycle-days 6 \\\n"
                  "    --completion-rate 0.8 --seed 1 \\\n"
                  "    --output triangle.json\n\n"
                  "# Cluster of Dots: Lieferungen am PI-Ende (12 Wochen)\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern cluster \\\n"
                  "    --mean-cycle-days 30 --pi-duration-weeks 12 \\\n"
                  "    --completion-rate 0.8 --seed 2 \\\n"
                  "    --output cluster.json\n\n"
                  "# Batch Transfers: PI-Ende + hohe CT-Varianz\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern batch \\\n"
                  "    --mean-cycle-days 30 --pi-duration-weeks 12 \\\n"
                  "    --completion-rate 0.8 --seed 3 \\\n"
                  "    --output batch.json", st),
              SP(6),
              box("<b>Hinweis:</b> --pattern erfordert --mean-cycle-days. "
                  "Ohne --mean-cycle-days wird das Muster ignoriert.", st)]

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
                "Issues, ca. 150 abgeschlossen. Dank Seed 42 jederzeit reproduzierbar.", st),
              H2("Schritt 2: Mit transform_data verarbeiten", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H2("Schritt 3: Report mit build_reports erstellen", st),
              PRE("python -m build_reports", st),
              SP(6),
              box("<b>Was zu erwarten ist (Seed 42, 200 Issues):</b><br/>"
                  "- Issue-Keys: ART_A-0001 bis ART_A-0200<br/>"
                  "- Issue-Typen: ~120 Feature, ~40 Bug, ~40 Enabler<br/>"
                  "- Ca. 150 Issues im Status 'Releasing' oder 'Done'<br/>"
                  "- Erstellungsdaten verteilt über das Jahr 2025<br/>"
                  "- Gelegentliche Rückschritte (backflow-prob 0.08 = ca. 8 %)", st)]

    story += [PageBreak(),
              H1("5b  Das Portfolio-Szenario", st), HR(),
              P("Mit <font name='Courier'>--scenario portfolio</font> erzeugt der Generator "
                "in einem Schritt ein komplettes Demo-Portfolio: zwei Solutions mit je drei "
                "ARTs, inklusive aller Artefakte der Verarbeitungskette.", st),
              P("<b>In der GUI:</b> Der Bereich „Demo-Portfolio\" unten im Fenster erzeugt "
                "das Szenario per Knopfdruck in einen Ordner deiner Wahl (das Seed-Feld "
                "wird übernommen, Standard 42); „Portfolio-Report öffnen\" rendert den "
                "Portfolio-Report, „Delta-Briefing öffnen\" das „Was hat sich "
                "geändert?\"-Briefing aus snapshot_prev/now.json — ganz ohne "
                "Kommandozeile.", st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --output demo/ --seed 42", st),
              P("Der Zielordner enthält danach:", st),
              tbl(["Artefakt", "Inhalt"],
                  [["workflows/", "zwei Workflow-Dateien (Alpha- und Beta-Stages)"],
                   ["raw/", "sechs Jira-JSON-Exporte (ein Generatorlauf je ART)"],
                   ["arts/", "IssueTimes-, CFD- und Transitions-Dateien je ART"],
                   ["solution_alpha.json", "Solution-Config ohne stage_map (Default-Pfad)"],
                   ["solution_beta.json", "Solution-Config mit eigener stage_map (Schema 2)"],
                   ["risks_*.json", "ROAM-Risiko-Register je Solution"],
                   ["nfr_*.json", "NFR-/Runway-Register je Solution"],
                   ["capabilities_*.json", "Capability-Map je Solution"],
                   ["dependencies_*.json", "Dependency-Register je Solution"],
                   ["decisions_*.json", "Decision-/Assumption-Log je Solution"],
                   ["snapshot_*.json", "Report-Snapshots fürs Delta-Briefing (prev/now)"],
                   ["slo_*.json / dora_*.json", "SLO- und DORA-/Qualitäts-Register je Solution"],
                   ["flow_problems_*.json", "Flussproblem-Backlog der VSC je Solution"],
                   ["portfolio.json", "Portfolio-Config über beide Solutions"],
                   ["pi_config.json", "PI-Intervalle über den Datenzeitraum"],
                   ["README.md", "Beschreibung der eingebauten Geschichten"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(6),
              P("Die Daten liegen relativ zum Erzeugungsdatum, damit die Qualitäts-Ampel "
                "des Portfolio-Reports sie als aktuell einstuft. Drei Geschichten sind "
                "fest eingebaut:", st),
              box("<b>Eingebaute Geschichten:</b><br/>"
                  "- <b>ART Alpha-3</b> ist der Ausreißer (ca. dreifache Cycle Time) — im "
                  "Comparison-Report der Solution Alpha rot hervorgehoben.<br/>"
                  "- <b>ART Beta-3</b> liefert schwache Daten (kein CFD, kaum begonnene "
                  "Issues, Datenstand 60 Tage alt) — Konfidenz 'low' in der "
                  "Qualitätstabelle.<br/>"
                  "- <b>Solution Beta</b> poolt über eine eigene stage_map "
                  "(Vorlauf/Umsetzung/Fertig); Solution Alpha nutzt den Default-Pfad.<br/>"
                  "- <b>ROAM-Board</b>: zwei Owned-Risiken sind bewusst alt "
                  "(45/50 Tage) — die Aging-Hervorhebung springt an.<br/>"
                  "- <b>NFR &amp; Runway</b>: Betas API-NFR ist verletzt, ein "
                  "Runway-Element eine überfällige Lücke — das Dashboard zeigt Rot.<br/>"
                  "- <b>Capability-Map</b>: Betas Data-Insights-Capability ist "
                  "kritisch, eine Alpha-Capability ohne ART (uncovered).<br/>"
                  "- <b>Dependency-Heatmap</b>: Alpha-1 → Alpha-3 blockiert und "
                  "überfällig; Beta-1 → Alpha-1 als Cross-Solution-Integration.<br/>"
                  "- <b>Decision-Log</b>: Betas offene Annahme hat ihr Prüfdatum "
                  "überschritten — rot als „review due\" markiert.<br/>"
                  "- <b>Delta-Briefing</b>: snapshot_prev/now.json liegen bei — "
                  "--delta zeigt Durchsatz, Beta-3-Konfidenzverfall, AD-1-Eskalation, "
                  "neues Risiko BR-2, frisch Überfälliges.<br/>"
                  "- <b>SLO & DORA</b>: Betas Sync-API reißt ihr SLO (breached), "
                  "ART Beta-3 ist auch im Delivery-Bild low (CFR 38 %, Coverage 31 %).<br/>"
                  "- <b>Flussproblem-Backlog (VSC)</b>: FP-A1/FP-B1 überleben 3 bzw. 4 "
                  "Konferenzen (rot); --conference rendert die Konferenzmappe.", st),
              SP(6),
              P("Der Ordner ist direkt verwendbar: "
                "<font name='Courier'>python -m portfolio demo/portfolio.json</font> erzeugt "
                "den Portfolio-Report; die Solution-Configs funktionieren auch einzeln. "
                "Gleicher Seed ergibt am selben Tag identische Daten.", st)]

    story += [PageBreak(),
              H1("6  Häufige Fragen (FAQ)", st), HR(),
              H2("Unterschied zwischen Testdaten und echten Daten?", st),
              P("Für Demos, Schulungen und Installationstests sind Testdaten die bessere "
                "Wahl. Für echte Flow-Analysen und Entscheidungen spiegeln echte Daten "
                "den tatsächlichen Workflow-Zustand wider.", st),
              HI("Für den manuellen Export echter Jira-Daten: Siehe Benutzerhandbuch "
                 "Get Data.", st)]

    story += [PageBreak(),
              H1("7  Glossar", st), HR(),
              tbl(["Begriff", "Erklärung"],
                  [["ART",       "Agile Release Train — ein Team aus mehreren Scrum-Teams in SAFe"],
                   ["API",       "Application Programming Interface — Programmierschnittstelle"],
                   ["CFD",       "Cumulative Flow Diagram — zeigt den Issuebestand je Stage kumuliert"],
                   ["Cycle Time", "Zeit von der ersten aktiven Stage bis zur Closed-Stage"],
                   ["Helper",    "SituationReport-Modul zum Zusammenführen mehrerer JSON-Dateien"],
                   ["Issue",     "Arbeitselement in Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JSON",      "JavaScript Object Notation — Format der Jira-API-Exporte"],
                   ["Seed",      "Startwert für den Zufallsgenerator — gleicher Seed = gleiche Ausgabe"],
                   ["Stage",     "Ein Schritt im Workflow (entspricht einer Jira-Spalte)"],
                   ["Workflow",  "Geordnete Abfolge von Stages, die ein Issue durchläuft"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — English
# ---------------------------------------------------------------------------

def content_en(st: dict) -> list:
    story = []

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
                "in development), which loads real data directly from Jira. For the "
                "manual export of real Jira data, see the <b>Get Data User Manual</b>.", st)]

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
                 "time begins here). Releasing is the closed stage.", st)]

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
                    "Seed for reproducible output (optional)"],
                   ["--mean-cycle-days FLOAT",  "(none)",
                    "Target mean cycle time in days (lognormal); enables CT control"],
                   ["--std-cycle-days FLOAT",   "(30 % of mean)",
                    "Standard deviation of cycle time in days"],
                   ["--pattern PATTERN",        "none",
                    "Flow anti-pattern: none / triangle / flat_triangle / cluster / batch"],
                   ["--pi-duration-weeks INT",  "12",
                    "PI cycle length in weeks (for cluster/batch)"],
                   ["--pattern-strength 0-100", "50",
                    "Pattern intensity 0–100 (0=subtle, 50=default, 100=strong)"]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm]),
              SP(8),
              box("<b>Tip: Reproducible results</b><br/>"
                  "With a fixed seed (e.g. <font name='Courier'>--seed 42</font>), the "
                  "generator always produces the same JSON file for the same parameters "
                  "— ideal for demos where all participants should see identical results.",
                  st)]

    story += [PageBreak(),
              H1("4b  Flow Anti-Pattern Modes", st), HR(),
              P("Since version 0.9.9 the Testdata Generator can simulate typical flow "
                "anti-patterns from Vacanti and Singh. Combine <b>--mean-cycle-days</b> "
                "with <b>--pattern</b>. The GUI provides radio buttons and sliders for "
                "all pattern settings.", st),
              SP(4),
              tbl(["Pattern", "Scatter plot appearance", "Description"],
                  [["none",
                    "Even point cloud",
                    "Random cycle time without trend — default behaviour"],
                   ["triangle",
                    "Triangle: right angle bottom right",
                    "Cycle time rises linearly over time (multiplier ~1–4× at default "
                    "strength, higher with --pattern-strength). "
                    "Indicates a process that is becoming progressively slower."],
                   ["flat_triangle",
                    "Triangle, rise flattens at the end",
                    "Like triangle but the increase is damped by tanh(2.5×t). "
                    "Shows a process deterioration that is levelling off."],
                   ["cluster",
                    "Vertical clusters of points at PI end",
                    "Cycle time stays stable (lognormal), but most issues are "
                    "delivered in the last 2 weeks before the PI end. "
                    "Deadline-driven behaviour."],
                   ["batch",
                    "Columns of variable height at PI end",
                    "Like cluster but with highly variable cycle time "
                    "(0.1× to 3× mean). Shows that both short and very long "
                    "issues are pushed to the PI end together."]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(8),
              H2("Cycle time control", st),
              P("When <b>--mean-cycle-days</b> is provided, cycle times are sampled "
                "from a lognormal distribution with the given mean.", st),
              tbl(["Parameter", "Meaning"],
                  [["--mean-cycle-days",
                    "Mean cycle time in days (e.g. 20). Required for all patterns except none."],
                   ["--std-cycle-days",
                    "Standard deviation in days (default: 30 % of mean). "
                    "Higher values produce a wider spread in the scatter plot."],
                   ["--pi-duration-weeks",
                    "Length of one PI cycle in weeks (default 12). "
                    "Only relevant for cluster and batch."]],
                  col_widths=[4.5 * cm, 11.0 * cm]),
              SP(8),
              H2("Examples", st),
              PRE("# Triangle pattern: CT rises from 20d to 80d\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern triangle \\\n"
                  "    --mean-cycle-days 20 --std-cycle-days 6 \\\n"
                  "    --completion-rate 0.8 --seed 1 \\\n"
                  "    --output triangle.json\n\n"
                  "# Cluster of Dots: deliveries at PI end (12-week PI)\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern cluster \\\n"
                  "    --mean-cycle-days 30 --pi-duration-weeks 12 \\\n"
                  "    --completion-rate 0.8 --seed 2 \\\n"
                  "    --output cluster.json\n\n"
                  "# Batch Transfers: PI end + high CT variance\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern batch \\\n"
                  "    --mean-cycle-days 30 --pi-duration-weeks 12 \\\n"
                  "    --completion-rate 0.8 --seed 3 \\\n"
                  "    --output batch.json", st),
              SP(6),
              box("<b>Note:</b> --pattern requires --mean-cycle-days. "
                  "Without --mean-cycle-days the pattern is ignored.", st)]

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
              P("Result: <font name='Courier'>ART_A_generated.json</font> with 200 issues "
                "— approximately 150 closed and 50 open. Reproducible with seed 42.", st),
              H2("Step 2: Process with transform_data", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H2("Step 3: Create report with build_reports", st),
              PRE("python -m build_reports", st),
              SP(6),
              box("<b>Expected output (seed 42, 200 issues):</b><br/>"
                  "- Issue keys: ART_A-0001 to ART_A-0200<br/>"
                  "- Issue types: ~120 Feature, ~40 Bug, ~40 Enabler<br/>"
                  "- ~150 issues with status 'Releasing' or 'Done'<br/>"
                  "- Creation dates distributed across 2025<br/>"
                  "- Occasional backward transitions (~8 %)", st)]

    story += [PageBreak(),
              H1("5b  The Portfolio Scenario", st), HR(),
              P("With <font name='Courier'>--scenario portfolio</font> the generator "
                "creates a complete demo portfolio in one step: two solutions with three "
                "ARTs each, including every artifact of the processing chain.", st),
              P("<b>In the GUI:</b> the 'Demo portfolio' section at the bottom of the "
                "window generates the scenario into a folder of your choice at the click "
                "of a button (the seed field is honoured, default 42); 'Open Portfolio "
                "Report' renders the portfolio report, 'Open Delta Briefing' the "
                "'what changed?' briefing from snapshot_prev/now.json — no command "
                "line needed.", st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --output demo/ --seed 42", st),
              P("The target folder then contains:", st),
              tbl(["Artifact", "Content"],
                  [["workflows/", "two workflow files (Alpha and Beta stages)"],
                   ["raw/", "six Jira JSON exports (one generator run per ART)"],
                   ["arts/", "IssueTimes, CFD, and Transitions files per ART"],
                   ["solution_alpha.json", "solution config without stage_map (default path)"],
                   ["solution_beta.json", "solution config with its own stage_map (schema 2)"],
                   ["risks_*.json", "ROAM risk register per solution"],
                   ["nfr_*.json", "NFR/runway register per solution"],
                   ["capabilities_*.json", "capability map per solution"],
                   ["dependencies_*.json", "dependency register per solution"],
                   ["decisions_*.json", "decision/assumption log per solution"],
                   ["snapshot_*.json", "report snapshots for the delta briefing (prev/now)"],
                   ["slo_*.json / dora_*.json", "SLO and DORA/quality registers per solution"],
                   ["flow_problems_*.json", "VSC flow-problem backlog per solution"],
                   ["portfolio.json", "portfolio config covering both solutions"],
                   ["pi_config.json", "PI intervals across the data window"],
                   ["README.md", "description of the built-in stories"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(6),
              P("The data is placed relative to the generation date so the portfolio "
                "report's quality traffic light rates it as current. Three stories are "
                "built in:", st),
              box("<b>Built-in stories:</b><br/>"
                  "- <b>ART Alpha-3</b> is the outlier (about three times the cycle "
                  "time) — highlighted red in Solution Alpha's comparison report.<br/>"
                  "- <b>ART Beta-3</b> delivers weak data (no CFD, few started issues, "
                  "data 60 days old) — confidence 'low' in the quality table.<br/>"
                  "- <b>Solution Beta</b> pools via its own stage_map "
                  "(Vorlauf/Umsetzung/Fertig); Solution Alpha uses the default path.<br/>"
                  "- <b>ROAM board</b>: two owned risks are deliberately old "
                  "(45/50 days) — the aging highlight fires.<br/>"
                  "- <b>NFR &amp; runway</b>: Beta's API NFR is violated and one "
                  "runway element is an overdue gap — the dashboard shows red.<br/>"
                  "- <b>Capability map</b>: Beta's data-insights capability is "
                  "critical, one Alpha capability has no ART (uncovered).<br/>"
                  "- <b>Dependency heatmap</b>: Alpha-1 → Alpha-3 blocked and "
                  "overdue; Beta-1 → Alpha-1 as a cross-solution integration.<br/>"
                  "- <b>Decision log</b>: Beta's open assumption has passed its "
                  "review date — flagged red as 'review due'.<br/>"
                  "- <b>Delta briefing</b>: snapshot_prev/now.json ship along — "
                  "--delta shows throughput, Beta-3's confidence decay, AD-1's "
                  "escalation, new risk BR-2, newly overdue items.<br/>"
                  "- <b>SLO & DORA</b>: Beta's sync API breaches its SLO, and ART "
                  "Beta-3 is low tier in the delivery picture too (CFR 38 %, "
                  "coverage 31 %).<br/>"
                  "- <b>Flow-problem backlog (VSC)</b>: FP-A1/FP-B1 survive 3 resp. 4 "
                  "conferences (red); --conference renders the pre-read.", st),
              SP(6),
              P("The folder is directly usable: "
                "<font name='Courier'>python -m portfolio demo/portfolio.json</font> builds "
                "the portfolio report; the solution configs also work individually. "
                "The same seed yields identical data on the same day.", st)]

    story += [PageBreak(),
              H1("6  Frequently Asked Questions (FAQ)", st), HR(),
              H2("Difference between test data and real data?", st),
              P("For demos, training, and installation tests, test data is the better "
                "choice — no privacy concerns, reproducible, and fully controlled. "
                "For real flow analyses and decisions, actual data reflects the true "
                "workflow state.", st),
              HI("For the manual export of real Jira data: See the Get Data User Manual.", st)]

    story += [PageBreak(),
              H1("7  Glossary", st), HR(),
              tbl(["Term", "Explanation"],
                  [["ART",       "Agile Release Train — a team-of-teams structure in SAFe"],
                   ["API",       "Application Programming Interface — programming interface"],
                   ["CFD",       "Cumulative Flow Diagram — cumulative issue count per stage over time"],
                   ["Cycle time", "Time from the first active stage to the closed stage"],
                   ["Helper",    "SituationReport module for merging multiple Jira JSON files"],
                   ["Issue",     "A work item in Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JSON",      "JavaScript Object Notation — format of Jira API exports"],
                   ["Seed",      "Starting value for the random generator — same seed = same output"],
                   ["Stage",     "One step in the workflow (corresponds to a Jira column)"],
                   ["Workflow",  "Ordered sequence of stages that an issue passes through"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — Romanian
# ---------------------------------------------------------------------------

def content_ro(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  Ce este Generatorul de Date de Test?", st), HR(),
              P("Generatorul de Date de Test (<b>Testdata Generator</b>) creează date "
                "sintetice de probleme Jira în formatul Jira REST API. Fișierele generate "
                "pot fi procesate direct de modulul <b>transform_data</b> — fără o "
                "instanță Jira reală.", st),
              P("Generatorul simulează istorii realiste de flux de lucru: problemele "
                "parcurg etapele definite, petrec perioade variabile în fiecare etapă, "
                "revin ocazional și se închid la o rată configurabilă.", st),
              SP(6),
              box("<b>Cazuri de utilizare tipice:</b><br/>"
                  "- <b>Testarea unei instalări noi:</b> Verificați dacă transform_data și "
                  "build_reports funcționează corect<br/>"
                  "- <b>Demo-uri și prezentări:</b> Date realiste fără preocupări de "
                  "confidențialitate<br/>"
                  "- <b>Training:</b> Mediu de învățare controlat cu date cunoscute<br/>"
                  "- <b>Dezvoltare:</b> Date de test reproductibile prin parametrul seed",
                  st),
              SP(8),
              P("Generatorul completează modulul <b>Get Data</b> (în curs de dezvoltare), "
                "care încarcă date reale direct din Jira. Pentru exportul manual al datelor "
                "reale Jira, consultați <b>Manualul de Utilizator Get Data</b>.", st)]

    story += [PageBreak(),
              H1("2  Cerințe prealabile și pornire", st), HR(),
              H2("2.1  Pachet portabil (recomandat)", st),
              P("Pachetul portabil include deja Python integrat — nu este necesară o "
                "instalare separată.", st),
              tbl(["Sistem de operare", "Fișier de pornire"],
                  [["Windows",  "TestdataGenerator.bat  (dublu-clic)"],
                   ["macOS",    "TestdataGenerator.command  (clic dreapta → Deschide)"],
                   ["Linux",    "./TestdataGenerator.sh"]],
                  col_widths=[4 * cm, 11.5 * cm]),
              SP(6),
              HI("Notă pentru Windows: Dacă la pornire apare o eroare privind Python, "
                 "fișierul ZIP a fost probabil blocat de Windows. Soluție: clic dreapta "
                 "pe ZIP → Proprietăți → Securitate → Deblocare → OK → reextragere.", st),
              SP(6),
              H2("2.2  Din codul sursă (necesită Python)", st),
              CD("python -m testdata_generator", st),
              SP(6),
              H2("2.3  Interfața utilizator", st),
              P("La pornire se deschide fereastra principală cu câmpuri de intrare pentru "
                "toți parametrii. Singurul câmp obligatoriu este fișierul de flux de "
                "lucru — toate celelalte au valori implicite sensibile.", st)]
    story += img("Testdata-Generator-GUI.png", 13.0,
                 "Fig. 1: Interfața utilizator a Generatorului de Date de Test", st)

    story += [PageBreak(),
              H1("3  Fișierul de flux de lucru", st), HR(),
              P("Fișierul de flux de lucru definește etapele tablei Jira și este singurul "
                "parametru obligatoriu. Folosește același format ca transform_data — un "
                "singur fișier funcționează pentru ambele module.", st),
              H2("3.1  Format", st),
              P("Fiecare linie descrie o etapă. Aliasurile (denumiri alternative de stare "
                "în exportul Jira) sunt separate prin două puncte. Două linii speciale "
                "marchează începutul și sfârșitul lucrului activ:", st),
              PRE("NumeCanonic:Alias1:Alias2\n"
                  "<First>PrimaEtapaActiva\n"
                  "<Closed>EtapaInchisa", st),
              tbl(["Linie", "Semnificație"],
                  [["NumeCanonic:Alias1:Alias2",
                    "Etapă cu unul sau mai multe denumiri alternative Jira"],
                   ["NumeEtapa (fără :)", "Etapă fără aliasuri"],
                   ["<First>NumeEtapa",
                    "Prima etapă activă — unde începe prelucrarea (start cycle time)"],
                   ["<Closed>NumeEtapa",
                    "Etapă închisă — marchează o problemă ca finalizată"]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(8),
              H2("3.2  Exemplu de flux ART_A", st),
              P("Exemplul inclus "
                "<font name='Courier'>workflow_ART_A.txt</font> "
                "modelează un flux SAFe ART tipic.", st),
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
                  "<Closed>Releasing", st)]

    story += [PageBreak(),
              H1("4  Referință parametri", st), HR(),
              P("Toți parametrii sunt disponibili atât în interfața grafică, cât și "
                "în linia de comandă.", st),
              tbl(["Parametru", "Implicit", "Descriere"],
                  [["--workflow FILE",         "(obligatoriu)",
                    "Fișier de definiție a fluxului de lucru (.txt)"],
                   ["--output FILE.json",       "<proiect>_generated.json",
                    "Calea fișierului de ieșire"],
                   ["--project KEY",            "TEST",
                    "Cheia proiectului Jira pentru problemele generate"],
                   ["--issues N",               "100",
                    "Numărul de probleme de generat"],
                   ["--from-date YYYY-MM-DD",   "2025-01-01",
                    "Data de creare cea mai timpurie"],
                   ["--to-date YYYY-MM-DD",     "2025-12-31",
                    "Data de tranziție cea mai târzie"],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1",
                    "Tipuri de probleme cu ponderi"],
                   ["--completion-rate FLOAT",  "0.7",
                    "Proporția problemelor care ajung la etapa închisă (0–1)"],
                   ["--todo-rate FLOAT",         "0.15",
                    "Proporția problemelor deschise care rămân în etapele timpurii (0–1)"],
                   ["--backflow-prob FLOAT",     "0.1",
                    "Probabilitatea unei tranziții înapoi la fiecare pas (0–1)"],
                   ["--seed INT",               "(aleatoriu)",
                    "Seed pentru rezultate reproductibile (opțional)"],
                   ["--mean-cycle-days FLOAT",  "(niciunul)",
                    "Cycle time mediu în zile (lognormal); activează controlul CT"],
                   ["--std-cycle-days FLOAT",   "(30 % din medie)",
                    "Abaterea standard a cycle time în zile"],
                   ["--pattern TIPAR",          "none",
                    "Anti-pattern: none / triangle / flat_triangle / cluster / batch"],
                   ["--pi-duration-weeks INT",  "12",
                    "Durata ciclului PI în săptămâni (pentru cluster/batch)"],
                   ["--pattern-strength 0-100", "50",
                    "Intensitatea modelului 0–100 (0=subtil, 50=implicit, 100=puternic)"]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm])]

    story += [PageBreak(),
              H1("4b  Modele de Anti-Pattern de flux", st), HR(),
              P("Începând cu versiunea 0.9.9, Generatorul de Date de Test poate simula "
                "anti-pattern-uri tipice de flux din literatura lui Vacanti și Singh. "
                "Combinați <b>--mean-cycle-days</b> cu <b>--pattern</b>.", st),
              SP(4),
              tbl(["Tipar", "Aspect scatter plot", "Descriere"],
                  [["none",
                    "Nor de puncte uniform",
                    "Cycle time aleatoriu fără tendință — comportament implicit"],
                   ["triangle",
                    "Triunghi: unghi drept jos-dreapta",
                    "Cycle time crește liniar în timp (multiplicator ~1–4× la intensitate "
                    "implicită, mai mare cu --pattern-strength). "
                    "Indică un proces care devine progresiv mai lent."],
                   ["flat_triangle",
                    "Triunghi, creștere atenuată la final",
                    "Ca triangle, dar creșterea este atenuată prin tanh(2.5×t). "
                    "Arată o deteriorare a procesului care se stabilizează."],
                   ["cluster",
                    "Grupuri verticale de puncte la finalul PI",
                    "Cycle time rămâne stabil, dar majoritatea problemelor sunt "
                    "livrate în ultimele 2 săptămâni înainte de finalul PI. "
                    "Comportament determinat de termen limită."],
                   ["batch",
                    "Coloane de înălțime variabilă la finalul PI",
                    "Ca cluster, dar cu cycle time foarte variabilă (0.1–3× medie). "
                    "Arată că problemele scurte și lungi sunt amânate împreună."]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(8),
              H2("Controlul cycle time", st),
              PRE("# Tipar triunghi: CT crește de la 20z la 80z\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern triangle \\\n"
                  "    --mean-cycle-days 20 --std-cycle-days 6 \\\n"
                  "    --completion-rate 0.8 --seed 1 \\\n"
                  "    --output triangle.json", st)]

    story += [PageBreak(),
              H1("5  ART_A – Exemplu complet", st), HR(),
              P("Acest exemplu arată întregul pipeline de la generator la raportul "
                "final, folosind proiectul fictiv ART_A.", st),
              H2("Pasul 1: Generare date de test", st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A --issues 200 \\\n"
                  "    --from-date 2025-01-01 --to-date 2025-12-31 \\\n"
                  "    --completion-rate 0.75 --seed 42 \\\n"
                  "    --output ART_A_generated.json", st),
              H2("Pasul 2: Procesare cu transform_data", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H2("Pasul 3: Creare raport cu build_reports", st),
              PRE("python -m build_reports", st)]

    story += [PageBreak(),
              H1("5b  Scenariul de portofoliu", st), HR(),
              P("Cu <font name='Courier'>--scenario portfolio</font> generatorul creează "
                "într-un singur pas un portofoliu demo complet: două soluții cu câte trei "
                "ART-uri, inclusiv toate artefactele lanțului de procesare.", st),
              P("<b>În GUI:</b> secțiunea 'Demo portfolio' din partea de jos a ferestrei "
                "generează scenariul într-un director la alegere printr-un clic (câmpul "
                "seed este preluat, implicit 42); 'Open Portfolio Report' redă raportul "
                "de portofoliu, 'Open Delta Briefing' briefingul 'ce s-a schimbat?' din "
                "snapshot_prev/now.json — fără linie de comandă.", st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --output demo/ --seed 42", st),
              P("Directorul țintă conține apoi:", st),
              tbl(["Artefact", "Conținut"],
                  [["workflows/", "două fișiere de flux de lucru (etape Alpha și Beta)"],
                   ["raw/", "șase exporturi JSON Jira (o rulare de generator per ART)"],
                   ["arts/", "fișiere IssueTimes, CFD și Transitions per ART"],
                   ["solution_alpha.json", "config de soluție fără stage_map (cale implicită)"],
                   ["solution_beta.json", "config de soluție cu stage_map propriu (schema 2)"],
                   ["risks_*.json", "registru de riscuri ROAM per soluție"],
                   ["nfr_*.json", "registru NFR/runway per soluție"],
                   ["capabilities_*.json", "capability map per soluție"],
                   ["dependencies_*.json", "registru de dependențe per soluție"],
                   ["decisions_*.json", "log de decizii/presupuneri per soluție"],
                   ["snapshot_*.json", "snapshot-uri de raport pentru delta briefing (prev/now)"],
                   ["slo_*.json / dora_*.json", "registre SLO și DORA/calitate per soluție"],
                   ["flow_problems_*.json", "backlog de probleme de flux (VSC) per soluție"],
                   ["portfolio.json", "config de portofoliu peste ambele soluții"],
                   ["pi_config.json", "intervale PI pe fereastra de date"],
                   ["README.md", "descrierea poveștilor încorporate"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(6),
              P("Datele sunt plasate relativ la data generării, astfel încât semaforul "
                "de calitate al raportului de portofoliu să le evalueze ca actuale. Trei "
                "povești sunt încorporate:", st),
              box("<b>Povești încorporate:</b><br/>"
                  "- <b>ART Alpha-3</b> este valoarea aberantă (cycle time de circa trei "
                  "ori mai mare) — evidențiat cu roșu în raportul de comparație al "
                  "Solution Alpha.<br/>"
                  "- <b>ART Beta-3</b> livrează date slabe (fără CFD, puține issue-uri "
                  "începute, date vechi de 60 de zile) — încredere 'low' în tabelul de "
                  "calitate.<br/>"
                  "- <b>Solution Beta</b> agregă printr-un stage_map propriu "
                  "(Vorlauf/Umsetzung/Fertig); Solution Alpha folosește calea implicită.<br/>"
                  "- <b>Board ROAM</b>: două riscuri owned sunt intenționat vechi "
                  "(45/50 de zile) — evidențierea aging se activează.<br/>"
                  "- <b>NFR &amp; runway</b>: NFR-ul API al soluției Beta este "
                  "încălcat, iar un element runway este o lacună întârziată — "
                  "dashboard-ul arată roșu.<br/>"
                  "- <b>Capability map</b>: capabilitatea data-insights a "
                  "soluției Beta este critică, o capabilitate Alpha nu are ART "
                  "(uncovered).<br/>"
                  "- <b>Heatmap de dependențe</b>: Alpha-1 → Alpha-3 blocată și "
                  "întârziată; Beta-1 → Alpha-1 ca integrare cross-solution.<br/>"
                  "- <b>Log de decizii</b>: presupunerea deschisă a soluției Beta "
                  "și-a depășit data de revizuire — marcată roșu 'review due'.<br/>"
                  "- <b>Delta briefing</b>: snapshot_prev/now.json sunt incluse — "
                  "--delta arată debitul, declinul încrederii Beta-3, escaladarea "
                  "AD-1, riscul nou BR-2, intrările proaspăt întârziate.<br/>"
                  "- <b>SLO & DORA</b>: API-ul de sincronizare al Beta își încalcă "
                  "SLO-ul, iar ART Beta-3 este low și în imaginea de livrare "
                  "(CFR 38 %, coverage 31 %).<br/>"
                  "- <b>Backlog probleme de flux (VSC)</b>: FP-A1/FP-B1 supraviețuiesc "
                  "3 resp. 4 conferințe (roșu); --conference redă mapa.", st),
              SP(6),
              P("Directorul este direct utilizabil: "
                "<font name='Courier'>python -m portfolio demo/portfolio.json</font> "
                "construiește raportul de portofoliu; configurile de soluție funcționează "
                "și individual. Același seed produce date identice în aceeași zi.", st)]

    story += [PageBreak(),
              H1("6  Întrebări frecvente (FAQ)", st), HR(),
              H2("Diferența dintre datele de test și datele reale?", st),
              P("Pentru demo-uri, training și teste de instalare, datele de test sunt "
                "alegerea mai bună — fără preocupări de confidențialitate, reproductibile "
                "și complet controlate. Pentru analize reale de flux, datele reale "
                "reflectă starea actuală a fluxului de lucru.", st),
              HI("Pentru exportul manual al datelor reale Jira: Consultați Manualul "
                 "de Utilizator Get Data.", st)]

    story += [PageBreak(),
              H1("7  Glosar", st), HR(),
              tbl(["Termen", "Explicație"],
                  [["ART",       "Agile Release Train — structură de echipă multiplă în SAFe"],
                   ["API",       "Application Programming Interface — interfață de programare"],
                   ["CFD",       "Cumulative Flow Diagram — număr cumulat de probleme per etapă"],
                   ["Cycle Time", "Timp de la prima etapă activă până la etapa închisă"],
                   ["Issue",     "Element de lucru în Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JSON",      "JavaScript Object Notation — format exporturi API Jira"],
                   ["Seed",      "Valoare de start pentru generatorul aleatoriu — același seed = același rezultat"],
                   ["Stage",     "Un pas în fluxul de lucru (corespunde unei coloane Jira)"],
                   ["Workflow",  "Secvență ordonată de etape prin care trece o problemă"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — Portuguese
# ---------------------------------------------------------------------------

def content_pt(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  O que é o Gerador de Dados de Teste?", st), HR(),
              P("O <b>Gerador de Dados de Teste</b> (Testdata Generator) cria dados "
                "sintéticos de issues Jira no formato Jira REST API. Os ficheiros "
                "gerados podem ser processados diretamente pelo módulo "
                "<b>transform_data</b> — sem necessidade de uma instância Jira real.", st),
              P("O gerador simula históricos de fluxo de trabalho realistas: as issues "
                "percorrem as etapas definidas, permanecem períodos variáveis em cada "
                "etapa, ocasionalmente regridem e fecham a uma taxa configurável.", st),
              SP(6),
              box("<b>Casos de uso típicos:</b><br/>"
                  "- <b>Testar uma nova instalação:</b> Verificar se transform_data e "
                  "build_reports funcionam corretamente<br/>"
                  "- <b>Demos e apresentações:</b> Dados realistas sem preocupações de "
                  "privacidade<br/>"
                  "- <b>Formação:</b> Ambiente de aprendizagem controlado com dados "
                  "conhecidos<br/>"
                  "- <b>Desenvolvimento:</b> Dados de teste reprodutíveis via parâmetro seed",
                  st),
              SP(8),
              P("O Gerador complementa o módulo <b>Get Data</b> (em desenvolvimento), "
                "que carrega dados reais diretamente do Jira. Para exportar dados reais "
                "do Jira manualmente, consulte o <b>Manual do Utilizador Get Data</b>.", st)]

    story += [PageBreak(),
              H1("2  Pré-requisitos e início", st), HR(),
              H2("2.1  Pacote portátil (recomendado)", st),
              P("O pacote portátil inclui o Python integrado — não é necessária "
                "instalação separada.", st),
              tbl(["Sistema operativo", "Ficheiro de início"],
                  [["Windows",  "TestdataGenerator.bat  (duplo clique)"],
                   ["macOS",    "TestdataGenerator.command  (clique direito → Abrir)"],
                   ["Linux",    "./TestdataGenerator.sh"]],
                  col_widths=[4 * cm, 11.5 * cm]),
              SP(6),
              HI("Nota para Windows: Se aparecer um erro sobre Python não encontrado, "
                 "o ficheiro ZIP foi bloqueado pelo Windows. Solução: clique direito "
                 "no ZIP → Propriedades → Segurança → Desbloquear → OK → "
                 "extrair novamente.", st),
              SP(6),
              H2("2.2  A partir do código fonte (requer Python)", st),
              CD("python -m testdata_generator", st),
              SP(6),
              H2("2.3  A interface do utilizador", st),
              P("Após o arranque, a janela principal apresenta campos de entrada para "
                "todos os parâmetros. Apenas o ficheiro de fluxo de trabalho é "
                "obrigatório — todos os outros campos têm valores predefinidos sensatos.", st)]
    story += img("Testdata-Generator-GUI.png", 13.0,
                 "Fig. 1: Interface do utilizador do Gerador de Dados de Teste", st)

    story += [PageBreak(),
              H1("3  O ficheiro de fluxo de trabalho", st), HR(),
              P("O ficheiro de fluxo de trabalho define as etapas do quadro Jira e é o "
                "único parâmetro obrigatório. Usa o mesmo formato que o transform_data — "
                "um ficheiro funciona para ambos os módulos.", st),
              H2("3.1  Formato", st),
              P("Cada linha descreve uma etapa. Os aliases (nomes de estado alternativos "
                "no export Jira) são separados por dois pontos. Duas linhas especiais "
                "marcam o início e o fim do trabalho ativo:", st),
              PRE("NomeCanónico:Alias1:Alias2\n"
                  "<First>PrimeiraEtapaAtiva\n"
                  "<Closed>EtapaFechada", st),
              tbl(["Linha", "Significado"],
                  [["NomeCanónico:Alias1:Alias2",
                    "Etapa com um ou mais nomes de estado Jira alternativos"],
                   ["NomeEtapa (sem :)", "Etapa sem aliases"],
                   ["<First>NomeEtapa",
                    "Primeira etapa ativa — onde o processamento começa (início do cycle time)"],
                   ["<Closed>NomeEtapa",
                    "Etapa fechada — marca uma issue como concluída"]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(8),
              H2("3.2  Exemplo de fluxo ART_A", st),
              P("O exemplo incluído "
                "<font name='Courier'>workflow_ART_A.txt</font> "
                "modela um fluxo SAFe ART típico.", st),
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
                  "<Closed>Releasing", st)]

    story += [PageBreak(),
              H1("4  Referência de parâmetros", st), HR(),
              P("Todos os parâmetros estão disponíveis tanto na interface gráfica como "
                "na linha de comandos.", st),
              tbl(["Parâmetro", "Predefinição", "Descrição"],
                  [["--workflow FILE",         "(obrigatório)",
                    "Ficheiro de definição do fluxo de trabalho (.txt)"],
                   ["--output FILE.json",       "<projeto>_generated.json",
                    "Caminho do ficheiro de saída"],
                   ["--project KEY",            "TEST",
                    "Chave do projeto Jira para as issues geradas"],
                   ["--issues N",               "100",
                    "Número de issues a gerar"],
                   ["--from-date YYYY-MM-DD",   "2025-01-01",
                    "Data de criação mais antiga"],
                   ["--to-date YYYY-MM-DD",     "2025-12-31",
                    "Data de transição mais recente"],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1",
                    "Tipos de issues com pesos"],
                   ["--completion-rate FLOAT",  "0.7",
                    "Fração de issues que atingem a etapa fechada (0–1)"],
                   ["--todo-rate FLOAT",         "0.15",
                    "Fração de issues abertas que ficam em etapas iniciais (0–1)"],
                   ["--backflow-prob FLOAT",     "0.1",
                    "Probabilidade de transição regressiva em cada passo (0–1)"],
                   ["--seed INT",               "(aleatório)",
                    "Seed para resultado reprodutível (opcional)"],
                   ["--mean-cycle-days FLOAT",  "(nenhum)",
                    "Cycle time médio em dias (lognormal); ativa controlo CT"],
                   ["--std-cycle-days FLOAT",   "(30 % da média)",
                    "Desvio padrão do cycle time em dias"],
                   ["--pattern PADRÃO",         "none",
                    "Anti-padrão: none / triangle / flat_triangle / cluster / batch"],
                   ["--pi-duration-weeks INT",  "12",
                    "Duração do ciclo PI em semanas (para cluster/batch)"],
                   ["--pattern-strength 0-100", "50",
                    "Intensidade do padrão 0–100 (0=subtil, 50=padrão, 100=forte)"]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm])]

    story += [PageBreak(),
              H1("4b  Modos de Anti-Padrão de fluxo", st), HR(),
              P("Desde a versão 0.9.9, o Gerador de Dados de Teste pode simular "
                "anti-padrões de fluxo típicos da literatura de Vacanti e Singh. "
                "Combine <b>--mean-cycle-days</b> com <b>--pattern</b>.", st),
              SP(4),
              tbl(["Padrão", "Aparência scatter plot", "Descrição"],
                  [["none",
                    "Nuvem de pontos uniforme",
                    "Cycle time aleatório sem tendência — comportamento predefinido"],
                   ["triangle",
                    "Triângulo: ângulo reto em baixo à direita",
                    "Cycle time aumenta linearmente ao longo do tempo (multiplicador ~1–4× "
                    "na intensidade padrão, maior com --pattern-strength). "
                    "Indica um processo que está a tornar-se progressivamente mais lento."],
                   ["flat_triangle",
                    "Triângulo, aumento atenua no final",
                    "Como triangle mas o aumento é atenuado por tanh(2.5×t). "
                    "Mostra uma deterioração do processo que está a estabilizar."],
                   ["cluster",
                    "Grupos verticais de pontos no final do PI",
                    "Cycle time mantém-se estável, mas a maioria das issues é "
                    "entregue nas últimas 2 semanas antes do final do PI. "
                    "Comportamento orientado por prazo."],
                   ["batch",
                    "Colunas de altura variável no final do PI",
                    "Como cluster mas com cycle time muito variável (0.1–3× média). "
                    "Mostra que issues curtas e longas são empurradas juntas para o PI."]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(8),
              H2("Controlo do cycle time", st),
              PRE("# Padrão triângulo: CT aumenta de 20d para 80d\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern triangle \\\n"
                  "    --mean-cycle-days 20 --std-cycle-days 6 \\\n"
                  "    --completion-rate 0.8 --seed 1 \\\n"
                  "    --output triangle.json", st)]

    story += [PageBreak(),
              H1("5  ART_A – Exemplo completo", st), HR(),
              P("Este exemplo mostra o pipeline completo do gerador ao relatório "
                "final, usando o projeto fictício ART_A.", st),
              H2("Passo 1: Gerar dados de teste", st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A --issues 200 \\\n"
                  "    --from-date 2025-01-01 --to-date 2025-12-31 \\\n"
                  "    --completion-rate 0.75 --seed 42 \\\n"
                  "    --output ART_A_generated.json", st),
              H2("Passo 2: Processar com transform_data", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H2("Passo 3: Criar relatório com build_reports", st),
              PRE("python -m build_reports", st)]

    story += [PageBreak(),
              H1("5b  O cenário de portfólio", st), HR(),
              P("Com <font name='Courier'>--scenario portfolio</font> o gerador cria num "
                "único passo um portfólio de demonstração completo: duas solutions com "
                "três ARTs cada, incluindo todos os artefactos da cadeia de "
                "processamento.", st),
              P("<b>Na GUI:</b> a secção 'Demo portfolio' na parte inferior da janela "
                "gera o cenário numa pasta à escolha com um clique (o campo seed é "
                "respeitado, padrão 42); 'Open Portfolio Report' gera o relatório de "
                "portfólio, 'Open Delta Briefing' o briefing 'o que mudou?' a partir de "
                "snapshot_prev/now.json — sem linha de comandos.", st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --output demo/ --seed 42", st),
              P("A pasta de destino contém depois:", st),
              tbl(["Artefacto", "Conteúdo"],
                  [["workflows/", "dois ficheiros de fluxo de trabalho (etapas Alpha e Beta)"],
                   ["raw/", "seis exports JSON do Jira (uma execução do gerador por ART)"],
                   ["arts/", "ficheiros IssueTimes, CFD e Transitions por ART"],
                   ["solution_alpha.json", "config de solution sem stage_map (caminho padrão)"],
                   ["solution_beta.json", "config de solution com stage_map próprio (schema 2)"],
                   ["risks_*.json", "registo de riscos ROAM por solution"],
                   ["nfr_*.json", "registo NFR/runway por solution"],
                   ["capabilities_*.json", "capability map por solution"],
                   ["dependencies_*.json", "registo de dependências por solution"],
                   ["decisions_*.json", "log de decisões/suposições por solution"],
                   ["snapshot_*.json", "snapshots do relatório para o delta briefing (prev/now)"],
                   ["slo_*.json / dora_*.json", "registos SLO e DORA/qualidade por solution"],
                   ["flow_problems_*.json", "backlog de problemas de fluxo (VSC) por solution"],
                   ["portfolio.json", "config de portfólio sobre ambas as solutions"],
                   ["pi_config.json", "intervalos PI sobre a janela de dados"],
                   ["README.md", "descrição das histórias incorporadas"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(6),
              P("Os dados são colocados relativamente à data de geração, para que o "
                "semáforo de qualidade do relatório de portfólio os avalie como atuais. "
                "Três histórias estão incorporadas:", st),
              box("<b>Histórias incorporadas:</b><br/>"
                  "- <b>ART Alpha-3</b> é o outlier (cycle time cerca de três vezes "
                  "maior) — destacado a vermelho no relatório de comparação da Solution "
                  "Alpha.<br/>"
                  "- <b>ART Beta-3</b> fornece dados fracos (sem CFD, poucos issues "
                  "iniciados, dados com 60 dias) — confiança 'low' na tabela de "
                  "qualidade.<br/>"
                  "- <b>Solution Beta</b> agrega através de um stage_map próprio "
                  "(Vorlauf/Umsetzung/Fertig); a Solution Alpha usa o caminho padrão.<br/>"
                  "- <b>Board ROAM</b>: dois riscos owned são deliberadamente antigos "
                  "(45/50 dias) — o realce de aging dispara.<br/>"
                  "- <b>NFR &amp; runway</b>: o NFR de API da Beta está violado e um "
                  "elemento runway é uma lacuna atrasada — o dashboard mostra "
                  "vermelho.<br/>"
                  "- <b>Capability map</b>: a capacidade data-insights da Beta é "
                  "crítica, uma capacidade Alpha não tem ART (uncovered).<br/>"
                  "- <b>Heatmap de dependências</b>: Alpha-1 → Alpha-3 bloqueada "
                  "e atrasada; Beta-1 → Alpha-1 como integração cross-solution.<br/>"
                  "- <b>Log de decisões</b>: a suposição aberta da Beta passou a "
                  "data de revisão — marcada a vermelho 'review due'.<br/>"
                  "- <b>Delta briefing</b>: snapshot_prev/now.json vêm incluídos — "
                  "--delta mostra o débito, o declínio da confiança da Beta-3, a "
                  "escalada de AD-1, o risco novo BR-2, itens recém-atrasados.<br/>"
                  "- <b>SLO & DORA</b>: a API de sincronização da Beta viola o seu "
                  "SLO, e o ART Beta-3 é low também na imagem de entrega "
                  "(CFR 38 %, coverage 31 %).<br/>"
                  "- <b>Backlog de problemas de fluxo (VSC)</b>: FP-A1/FP-B1 sobrevivem "
                  "a 3 resp. 4 conferências (vermelho); --conference gera o dossier.", st),
              SP(6),
              P("A pasta é diretamente utilizável: "
                "<font name='Courier'>python -m portfolio demo/portfolio.json</font> gera "
                "o relatório de portfólio; as configs de solution também funcionam "
                "individualmente. A mesma seed produz dados idênticos no mesmo dia.", st)]

    story += [PageBreak(),
              H1("6  Perguntas frequentes (FAQ)", st), HR(),
              H2("Diferença entre dados de teste e dados reais?", st),
              P("Para demos, formação e testes de instalação, os dados de teste são a "
                "melhor escolha — sem preocupações de privacidade, reprodutíveis e "
                "totalmente controlados. Para análises reais de fluxo, os dados reais "
                "refletem o verdadeiro estado do fluxo de trabalho.", st),
              HI("Para exportar dados reais do Jira manualmente: Consulte o Manual "
                 "do Utilizador Get Data.", st)]

    story += [PageBreak(),
              H1("7  Glossário", st), HR(),
              tbl(["Termo", "Explicação"],
                  [["ART",       "Agile Release Train — estrutura de múltiplas equipas em SAFe"],
                   ["API",       "Application Programming Interface — interface de programação"],
                   ["CFD",       "Cumulative Flow Diagram — contagem cumulativa de issues por etapa"],
                   ["Cycle Time", "Tempo desde a primeira etapa ativa até à etapa fechada"],
                   ["Issue",     "Elemento de trabalho no Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JSON",      "JavaScript Object Notation — formato dos exports da API Jira"],
                   ["Seed",      "Valor inicial para o gerador aleatório — mesmo seed = mesmo resultado"],
                   ["Stage",     "Um passo no fluxo de trabalho (corresponde a uma coluna Jira)"],
                   ["Workflow",  "Sequência ordenada de etapas que uma issue percorre"]],
                  col_widths=[3.5 * cm, 12 * cm])]

    return story


# ---------------------------------------------------------------------------
# Content — French
# ---------------------------------------------------------------------------

def content_fr(st: dict) -> list:
    story = []

    story += [PageBreak(),
              H1("1  Qu'est-ce que le Générateur de données de test ?", st), HR(),
              P("Le <b>Générateur de données de test</b> (Testdata Generator) crée des "
                "données synthétiques de tickets Jira au format Jira REST API. Les "
                "fichiers générés peuvent être traités directement par le module "
                "<b>transform_data</b> — sans instance Jira réelle.", st),
              P("Le générateur simule des historiques de flux de travail réalistes : "
                "les tickets parcourent les étapes définies, passent des durées variables "
                "dans chaque étape, régressent occasionnellement et se ferment à un "
                "taux configurable.", st),
              SP(6),
              box("<b>Cas d'utilisation typiques :</b><br/>"
                  "- <b>Tester une nouvelle installation :</b> Vérifier que transform_data "
                  "et build_reports fonctionnent correctement<br/>"
                  "- <b>Démos et présentations :</b> Données réalistes sans "
                  "problèmes de confidentialité<br/>"
                  "- <b>Formation :</b> Environnement d'apprentissage contrôlé avec "
                  "des données connues<br/>"
                  "- <b>Développement :</b> Données de test reproductibles via le "
                  "paramètre seed",
                  st),
              SP(8),
              P("Le Générateur complète le module <b>Get Data</b> (en cours de "
                "développement), qui charge des données réelles directement depuis "
                "Jira. Pour l'export manuel de données Jira réelles, consultez le "
                "<b>Manuel d'utilisation Get Data</b>.", st)]

    story += [PageBreak(),
              H1("2  Prérequis et démarrage", st), HR(),
              H2("2.1  Package portable (recommandé)", st),
              P("Le package portable inclut Python déjà intégré — aucune installation "
                "séparée requise.", st),
              tbl(["Système d'exploitation", "Fichier de démarrage"],
                  [["Windows",  "TestdataGenerator.bat  (double-clic)"],
                   ["macOS",    "TestdataGenerator.command  (clic droit → Ouvrir)"],
                   ["Linux",    "./TestdataGenerator.sh"]],
                  col_widths=[4 * cm, 11.5 * cm]),
              SP(6),
              HI("Note Windows : Si un message d'erreur concernant Python apparaît, "
                 "le fichier ZIP a peut-être été bloqué par Windows. Solution : "
                 "clic droit sur le ZIP → Propriétés → Sécurité → Débloquer → "
                 "OK → extraire à nouveau.", st),
              SP(6),
              H2("2.2  Depuis le code source (Python requis)", st),
              CD("python -m testdata_generator", st),
              SP(6),
              H2("2.3  L'interface utilisateur", st),
              P("Au démarrage, la fenêtre principale affiche des champs de saisie pour "
                "tous les paramètres. Seul le fichier de flux de travail est obligatoire "
                "— tous les autres champs ont des valeurs par défaut sensées.", st)]
    story += img("Testdata-Generator-GUI.png", 13.0,
                 "Fig. 1 : Interface utilisateur du Générateur de données de test", st)

    story += [PageBreak(),
              H1("3  Le fichier de flux de travail", st), HR(),
              P("Le fichier de flux de travail définit les étapes de votre tableau Jira "
                "et est le seul paramètre obligatoire. Il utilise le même format que "
                "transform_data — un seul fichier fonctionne pour les deux modules.", st),
              H2("3.1  Format", st),
              P("Chaque ligne décrit une étape. Les alias (noms de statut alternatifs "
                "dans l'export Jira) sont séparés par des deux-points. Deux lignes "
                "spéciales marquent le début et la fin du travail actif :", st),
              PRE("NomCanonique:Alias1:Alias2\n"
                  "<First>PremiereEtapeActive\n"
                  "<Closed>EtapeFermee", st),
              tbl(["Ligne", "Signification"],
                  [["NomCanonique:Alias1:Alias2",
                    "Étape avec un ou plusieurs noms de statut Jira alternatifs"],
                   ["NomEtape (sans :)", "Étape sans alias"],
                   ["<First>NomEtape",
                    "Première étape active — où commence le traitement (début du cycle time)"],
                   ["<Closed>NomEtape",
                    "Étape fermée — marque un ticket comme terminé"]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(8),
              H2("3.2  Exemple de flux ART_A", st),
              P("L'exemple fourni "
                "<font name='Courier'>workflow_ART_A.txt</font> "
                "modélise un flux SAFe ART typique.", st),
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
                  "<Closed>Releasing", st)]

    story += [PageBreak(),
              H1("4  Référence des paramètres", st), HR(),
              P("Tous les paramètres sont disponibles dans l'interface graphique et "
                "en ligne de commande.", st),
              tbl(["Paramètre", "Défaut", "Description"],
                  [["--workflow FILE",         "(obligatoire)",
                    "Fichier de définition du flux de travail (.txt)"],
                   ["--output FILE.json",       "<projet>_generated.json",
                    "Chemin du fichier de sortie"],
                   ["--project KEY",            "TEST",
                    "Clé de projet Jira pour les tickets générés"],
                   ["--issues N",               "100",
                    "Nombre de tickets à générer"],
                   ["--from-date YYYY-MM-DD",   "2025-01-01",
                    "Date de création la plus ancienne"],
                   ["--to-date YYYY-MM-DD",     "2025-12-31",
                    "Date de transition la plus récente"],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1",
                    "Types de tickets avec pondérations"],
                   ["--completion-rate FLOAT",  "0.7",
                    "Fraction de tickets atteignant l'étape fermée (0–1)"],
                   ["--todo-rate FLOAT",         "0.15",
                    "Fraction de tickets ouverts restant dans les étapes initiales (0–1)"],
                   ["--backflow-prob FLOAT",     "0.1",
                    "Probabilité d'une transition en arrière à chaque pas (0–1)"],
                   ["--seed INT",               "(aléatoire)",
                    "Seed pour résultat reproductible (optionnel)"],
                   ["--mean-cycle-days FLOAT",  "(aucun)",
                    "Cycle time moyen en jours (lognormal) ; active le contrôle CT"],
                   ["--std-cycle-days FLOAT",   "(30 % de la moyenne)",
                    "Écart type du cycle time en jours"],
                   ["--pattern MOTIF",          "none",
                    "Anti-pattern : none / triangle / flat_triangle / cluster / batch"],
                   ["--pi-duration-weeks INT",  "12",
                    "Durée du cycle PI en semaines (pour cluster/batch)"],
                   ["--pattern-strength 0-100", "50",
                    "Intensité du motif 0–100 (0=subtil, 50=défaut, 100=fort)"]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm])]

    story += [PageBreak(),
              H1("4b  Modes d'anti-pattern de flux", st), HR(),
              P("Depuis la version 0.9.9, le Générateur peut simuler des anti-patterns "
                "de flux typiques de la littérature de Vacanti et Singh. Combinez "
                "<b>--mean-cycle-days</b> avec <b>--pattern</b>.", st),
              SP(4),
              tbl(["Motif", "Apparence scatter plot", "Description"],
                  [["none",
                    "Nuage de points uniforme",
                    "Cycle time aléatoire sans tendance — comportement par défaut"],
                   ["triangle",
                    "Triangle : angle droit en bas à droite",
                    "Le cycle time augmente linéairement dans le temps (multiplicateur ~1–4× "
                    "à l'intensité par défaut, plus élevé avec --pattern-strength). "
                    "Indique un processus qui devient progressivement plus lent."],
                   ["flat_triangle",
                    "Triangle, augmentation s'atténue à la fin",
                    "Comme triangle mais l'augmentation est atténuée par tanh(2.5×t). "
                    "Montre une détérioration du processus qui se stabilise."],
                   ["cluster",
                    "Groupes verticaux de points en fin de PI",
                    "Le cycle time reste stable, mais la plupart des tickets sont "
                    "livrés dans les 2 dernières semaines avant la fin du PI. "
                    "Comportement orienté par délai."],
                   ["batch",
                    "Colonnes de hauteur variable en fin de PI",
                    "Comme cluster mais avec cycle time très variable (0.1–3× moyenne). "
                    "Montre que tickets courts et longs sont tous poussés en fin de PI."]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(8),
              H2("Contrôle du cycle time", st),
              PRE("# Motif triangle : CT augmente de 20j à 80j\n"
                  "python -m testdata_generator \\\n"
                  "    --workflow workflow.txt --issues 300 \\\n"
                  "    --pattern triangle \\\n"
                  "    --mean-cycle-days 20 --std-cycle-days 6 \\\n"
                  "    --completion-rate 0.8 --seed 1 \\\n"
                  "    --output triangle.json", st)]

    story += [PageBreak(),
              H1("5  ART_A – Exemple complet", st), HR(),
              P("Cet exemple montre le pipeline complet du générateur au rapport "
                "final, en utilisant le projet fictif ART_A.", st),
              H2("Étape 1 : Générer les données de test", st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A --issues 200 \\\n"
                  "    --from-date 2025-01-01 --to-date 2025-12-31 \\\n"
                  "    --completion-rate 0.75 --seed 42 \\\n"
                  "    --output ART_A_generated.json", st),
              H2("Étape 2 : Traiter avec transform_data", st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H2("Étape 3 : Créer le rapport avec build_reports", st),
              PRE("python -m build_reports", st)]

    story += [PageBreak(),
              H1("5b  Le scénario de portefeuille", st), HR(),
              P("Avec <font name='Courier'>--scenario portfolio</font>, le générateur "
                "crée en une seule étape un portefeuille de démonstration complet : deux "
                "solutions de trois ARTs chacune, avec tous les artefacts de la chaîne "
                "de traitement.", st),
              P("<b>Dans la GUI :</b> la section 'Demo portfolio' en bas de la fenêtre "
                "génère le scénario dans un dossier de votre choix en un clic (le champ "
                "seed est repris, 42 par défaut) ; 'Open Portfolio Report' génère le "
                "rapport de portefeuille, 'Open Delta Briefing' le briefing « qu'est-ce "
                "qui a changé ? » à partir de snapshot_prev/now.json — sans ligne de "
                "commande.", st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --output demo/ --seed 42", st),
              P("Le dossier cible contient ensuite :", st),
              tbl(["Artefact", "Contenu"],
                  [["workflows/", "deux fichiers de flux de travail (étapes Alpha et Beta)"],
                   ["raw/", "six exports JSON Jira (une exécution du générateur par ART)"],
                   ["arts/", "fichiers IssueTimes, CFD et Transitions par ART"],
                   ["solution_alpha.json", "config de solution sans stage_map (chemin par défaut)"],
                   ["solution_beta.json", "config de solution avec stage_map propre (schéma 2)"],
                   ["risks_*.json", "registre de risques ROAM par solution"],
                   ["nfr_*.json", "registre NFR/runway par solution"],
                   ["capabilities_*.json", "capability map par solution"],
                   ["dependencies_*.json", "registre de dependances par solution"],
                   ["decisions_*.json", "log de decisions/hypotheses par solution"],
                   ["snapshot_*.json", "snapshots du rapport pour le delta briefing (prev/now)"],
                   ["slo_*.json / dora_*.json", "registres SLO et DORA/qualite par solution"],
                   ["flow_problems_*.json", "backlog des problemes de flux (VSC) par solution"],
                   ["portfolio.json", "config de portefeuille couvrant les deux solutions"],
                   ["pi_config.json", "intervalles PI sur la fenêtre de données"],
                   ["README.md", "description des histoires intégrées"]],
                  col_widths=[4.5 * cm, 11 * cm]),
              SP(6),
              P("Les données sont placées relativement à la date de génération, afin que "
                "le feu de qualité du rapport de portefeuille les évalue comme actuelles. "
                "Trois histoires sont intégrées :", st),
              box("<b>Histoires intégrées :</b><br/>"
                  "- <b>ART Alpha-3</b> est la valeur aberrante (cycle time environ "
                  "triplé) — surligné en rouge dans le rapport de comparaison de la "
                  "Solution Alpha.<br/>"
                  "- <b>ART Beta-3</b> fournit des données faibles (pas de CFD, peu "
                  "d'issues commencées, données vieilles de 60 jours) — confiance 'low' "
                  "dans le tableau de qualité.<br/>"
                  "- <b>Solution Beta</b> agrège via son propre stage_map "
                  "(Vorlauf/Umsetzung/Fertig) ; la Solution Alpha utilise le chemin par "
                  "défaut.<br/>"
                  "- <b>Board ROAM</b> : deux risques owned sont volontairement "
                  "anciens (45/50 jours) — le surlignage aging se déclenche.<br/>"
                  "- <b>NFR &amp; runway</b> : le NFR d'API de Beta est viole et un "
                  "element runway est une lacune en retard — le dashboard montre "
                  "du rouge.<br/>"
                  "- <b>Capability map</b> : la capacite data-insights de Beta "
                  "est critique, une capacite Alpha n'a pas d'ART (uncovered).<br/>"
                  "- <b>Heatmap des dependances</b> : Alpha-1 → Alpha-3 bloquee "
                  "et en retard ; Beta-1 → Alpha-1 en integration cross-solution.<br/>"
                  "- <b>Log de decisions</b> : l'hypothese ouverte de Beta a "
                  "depasse sa date de revision — marquee en rouge 'review due'.<br/>"
                  "- <b>Delta briefing</b> : snapshot_prev/now.json sont fournis — "
                  "--delta montre le debit, le declin de confiance de Beta-3, "
                  "l'escalade d'AD-1, le nouveau risque BR-2, le fraichement en retard.<br/>"
                  "- <b>SLO & DORA</b> : l'API de synchronisation de Beta viole son "
                  "SLO, et l'ART Beta-3 est low aussi dans l'image de livraison "
                  "(CFR 38 %, coverage 31 %).<br/>"
                  "- <b>Backlog des problemes de flux (VSC)</b> : FP-A1/FP-B1 survivent "
                  "a 3 resp. 4 conferences (rouge) ; --conference genere le dossier.", st),
              SP(6),
              P("Le dossier est directement utilisable : "
                "<font name='Courier'>python -m portfolio demo/portfolio.json</font> "
                "génère le rapport de portefeuille ; les configs de solution "
                "fonctionnent aussi individuellement. La même graine produit des données "
                "identiques le même jour.", st)]

    story += [PageBreak(),
              H1("6  Foire aux questions (FAQ)", st), HR(),
              H2("Différence entre données de test et données réelles ?", st),
              P("Pour les démos, la formation et les tests d'installation, les données "
                "de test sont le meilleur choix — sans problèmes de confidentialité, "
                "reproductibles et entièrement contrôlées. Pour les analyses de flux "
                "réelles, les données réelles reflètent l'état réel du flux de travail.", st),
              HI("Pour l'export manuel de données Jira réelles : Consultez le Manuel "
                 "d'utilisation Get Data.", st)]

    story += [PageBreak(),
              H1("7  Glossaire", st), HR(),
              tbl(["Terme", "Explication"],
                  [["ART",       "Agile Release Train — structure multi-équipes dans SAFe"],
                   ["API",       "Application Programming Interface — interface de programmation"],
                   ["CFD",       "Cumulative Flow Diagram — comptage cumulé des tickets par étape"],
                   ["Cycle Time", "Temps depuis la première étape active jusqu'à l'étape fermée"],
                   ["Issue",     "Élément de travail dans Jira (Feature, Bug, Enabler, Story, …)"],
                   ["JSON",      "JavaScript Object Notation — format des exports API Jira"],
                   ["Seed",      "Valeur initiale pour le générateur aléatoire — même seed = même résultat"],
                   ["Stage",     "Une étape dans le flux de travail (correspond à une colonne Jira)"],
                   ["Workflow",  "Séquence ordonnée d'étapes que parcourt un ticket"]],
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
        doc = _TDGDoc(str(output), lang=lang)
        doc.multiBuild(story)
        print(f"PDF erstellt: {output}")


if __name__ == "__main__":
    main()
