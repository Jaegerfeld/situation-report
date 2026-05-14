# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       13.05.2026
# Geaendert:      13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer das helper-Modul (JSON Merger) als PDF
#   in allen fuenf unterstuetzten Sprachen (DE, EN, RO, PT, FR). Beschreibt
#   Installation, GUI-Bedienung, CLI-Modus, Ausgabeformat und FAQ.
# =============================================================================

import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _font_config import setup as _setup_fonts
_FN, _FB, _FI, _FBI = _setup_fonts()  # normal, bold, italic, bold_italic
from version import __version__ as _VERSION

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    ActionFlowable, BaseDocTemplate, Frame, HRFlowable, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

OUTPUT_DE = Path(__file__).parent / "helper_Benutzerhandbuch.pdf"
OUTPUT_EN = Path(__file__).parent / "helper_UserManual.pdf"
OUTPUT_RO = Path(__file__).parent / "helper_ManualUtilizator.pdf"
OUTPUT_PT = Path(__file__).parent / "helper_ManualUtilizador.pdf"
OUTPUT_FR = Path(__file__).parent / "helper_ManuelUtilisateur.pdf"

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
    LANG_DE: "helper (JSON Merger)  --  Benutzerhandbuch",
    LANG_EN: "helper (JSON Merger)  --  User Manual",
    LANG_RO: "helper (JSON Merger)  --  Manual de Utilizator",
    LANG_PT: "helper (JSON Merger)  --  Manual do Utilizador",
    LANG_FR: "helper (JSON Merger)  --  Manuel d'utilisation",
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
    LANG_DE: "Mehrere Jira-JSON-Dateien zu einer zusammenfuehren",
    LANG_EN: "Merge multiple Jira JSON files into one",
    LANG_RO: "Combinati mai multe fisiere Jira JSON intr-unul singur",
    LANG_PT: "Combinar varios ficheiros Jira JSON num so",
    LANG_FR: "Fusionner plusieurs fichiers Jira JSON en un seul",
}
_COVER_AUDIENCE = {
    LANG_DE: "Fuer Agile Coaches und PI Manager",
    LANG_EN: "For Agile Coaches and PI Managers",
    LANG_RO: "Pentru Agile Coaches si Manageri PI",
    LANG_PT: "Para Agile Coaches e Gestores de PI",
    LANG_FR: "Pour les Agile Coaches et les PI Managers",
}


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def make_styles() -> dict:
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return dict(
        h1=s("H1h", fontName=_FB, fontSize=18, textColor=C_BLUE,
              spaceBefore=24, spaceAfter=8),
        h2=s("H2h", fontName=_FB, fontSize=13, textColor=C_ACCENT,
              spaceBefore=14, spaceAfter=5),
        body=s("Bodyh", fontName=_FN, fontSize=10, leading=15,
               alignment=TA_JUSTIFY, spaceAfter=6),
        bullet=s("Bulleth", fontName=_FN, fontSize=10, leading=14,
                 leftIndent=16, spaceAfter=3),
        code=s("Codeh", fontName="Courier", fontSize=9, leading=13,
               leftIndent=12, spaceBefore=4, spaceAfter=4,
               backColor=colors.HexColor("#f4f4f4"), textColor=C_BLUE),
        hint=s("Hinth", fontName=_FI, fontSize=9,
               textColor=C_HINT, leading=13, leftIndent=12, spaceAfter=4),
        center=s("Centerh", fontName=_FN, fontSize=10, leading=15,
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
    "TblHdr_helper",
    fontName=_FB, fontSize=10, textColor=C_WHITE, leading=13,
)
_TBL_CELL_STYLE = ParagraphStyle(
    "TblCell_helper",
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


class _HelperDoc(BaseDocTemplate):

    def __init__(self, filename: str, lang: str = LANG_DE, **kw):
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


def _build_cover(canvas, doc, lang: str = LANG_DE):
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont(_FB, 32)
    canvas.drawCentredString(w/2, h*0.62, "helper")
    canvas.setFont(_FB, 20)
    canvas.drawCentredString(w/2, h*0.57, "JSON Merger")
    canvas.setFont(_FB, 16)
    canvas.drawCentredString(w/2, h*0.515, _COVER_SUBTITLE[lang])
    canvas.setFont(_FN, 11)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.47, _COVER_TAGLINE[lang])
    canvas.setStrokeColor(C_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(w*0.2, h*0.44, w*0.8, h*0.44)
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


# ---------------------------------------------------------------------------
# Content – German
# ---------------------------------------------------------------------------

def content_de(st: dict) -> list:
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        _H1("1. Was ist helper?", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Das Modul <b>helper</b> ist ein Hilfswerkzeug, das mehrere Jira-REST-API-"
            "JSON-Dateien zu einer einzigen zusammenfuehrt. Es wird benoetigt, wenn "
            "ein Jira-Export aufgrund von API-Limits auf mehrere Dateien aufgeteilt "
            "wurde und <b>transform_data</b> eine einzelne Datei erwartet.", st),
        _P(
            "helper dedupliziert die Issues automatisch nach ihrer eindeutigen "
            "Issue-ID und erzeugt einen korrekten Jira-API-Envelope "
            "(startAt, total, maxResults). Die Ausgabedatei kann direkt von "
            "transform_data verarbeitet werden.", st),
        _SP(8),

        _H1("2. Starten", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _H2("2.1  Als GUI (grafische Oberflaeche)", st),
        _P("Im entpackten Ordner die passende Startdatei doppelklicken:", st),
        tbl(
            [
                ["Betriebssystem", "Startdatei"],
                ["Windows",  "Helper.bat  (Doppelklick)"],
                ["macOS",    "Helper.command  (Rechtsklick → Oeffnen)"],
                ["Linux",    "./Helper.sh"],
            ],
            col_widths=[4*cm, w - 4*cm],
        ),
        _SP(6),
        _H2("2.2  Aus dem Quellcode", st),
        _CD("python -m helper", st),
        _SP(8),

        _H1("3. GUI-Bedienung", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Das Hauptfenster besteht aus drei Bereichen: der Dateiliste (oben), "
            "der Ausgabedatei (Mitte) und dem Log-Bereich (unten).", st),

        _H2("3.1  Eingabedateien hinzufuegen", st),
        _P(
            "Im Bereich <b>Eingabedateien</b> koennen eine oder mehrere Jira-JSON-"
            "Dateien hinzugefuegt werden:", st),
        _BL(
            "<b>Hinzufuegen…</b> — Oeffnet einen Dateidialog, in dem mehrere Dateien "
            "gleichzeitig ausgewaehlt werden koennen (Strg+Klick oder Shift+Klick).", st),
        _BL(
            "<b>Entfernen</b> — Loescht die markierten Eintraege aus der Liste "
            "(die Dateien auf der Festplatte bleiben unveraendert).", st),
        _SP(4),
        _box(
            "<b>Tipp:</b> Die Reihenfolge in der Liste beeinflusst nicht das Ergebnis — "
            "alle Issues werden unabhaengig von der Dateireihenfolge zusammengefuehrt "
            "und dedupliziert.", st, "#e8f8f0"),

        _H2("3.2  Ausgabedatei waehlen", st),
        _P(
            "Im Feld <b>Ausgabedatei (JSON)</b> den Speicherpfad der Ergebnisdatei "
            "eingeben oder per <b>Durchsuchen…</b>-Button auswaehlen. Die Datei "
            "wird beim Zusammenfuehren neu erzeugt (falls vorhanden: ueberschrieben).", st),

        _H2("3.3  Duplikate entfernen", st),
        _P(
            "Die Checkbox <b>Duplikate entfernen (nach Issue-ID)</b> ist standardmaessig "
            "aktiviert. Issues, die in mehreren Eingabedateien mit derselben ID vorkommen, "
            "werden nur einmal in die Ausgabe geschrieben. Im Log erscheint fuer jeden "
            "entfernten Duplikat eine Meldung.", st),
        _SP(4),
        _box(
            "<b>Hinweis:</b> Die Deduplizierung basiert auf dem Feld <b>id</b> im "
            "Jira-JSON (numerische Issue-ID). Das Feld <b>key</b> (z.B. ARTA-123) "
            "wird zur Anzeige im Log verwendet.", st, "#fff8e1"),

        _H2("3.4  Zusammenfuehren starten", st),
        _P(
            "Auf den Button <b>Zusammenfuehren</b> klicken. Der Fortschritt wird "
            "im Log-Bereich angezeigt. Bei laengeren Operationen erscheint ein "
            "Ladebalken. Nach Abschluss zeigt der Log die Anzahl der zusammengefuehrten "
            "und deduplizierten Issues sowie den Pfad der Ausgabedatei.", st),
        _SP(8),

        _H1("4. CLI-Modus", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "helper kann auch ohne GUI direkt auf der Kommandozeile aufgerufen werden:", st),
        _CD("python -m helper datei1.json datei2.json --output merged.json", st),
        _SP(4),
        tbl(
            [
                ["Parameter", "Beschreibung"],
                ["FILE …",        "Mindestens eine Eingabe-JSON-Datei (Pflicht)"],
                ["--output FILE", "Pfad der Ausgabedatei (Pflicht)"],
                ["--no-dedup",    "Deduplizierung deaktivieren (alle Issues behalten)"],
            ],
            col_widths=[4.5*cm, w - 4.5*cm],
        ),
        _SP(8),

        _H1("5. Ausgabeformat", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Die Ausgabedatei ist eine valide Jira-REST-API-JSON-Datei im Format der "
            "Jira Cloud API v2 / v3. Der Envelope wird automatisch korrekt gesetzt:", st),
        _SP(4),
        tbl(
            [
                ["Feld", "Wert"],
                ["expand",     "Aus der ersten Eingabedatei uebernommen"],
                ["startAt",    "Immer 0"],
                ["maxResults", "Anzahl der zusammengefuehrten Issues"],
                ["total",      "Anzahl der zusammengefuehrten Issues"],
                ["issues",     "Alle Issues aus allen Eingabedateien (nach Dedup)"],
            ],
            col_widths=[3.5*cm, w - 3.5*cm],
        ),
        _SP(4),
        _box(
            "<b>Kompatibilitaet:</b> Die Ausgabedatei kann direkt als Eingabe fuer "
            "<b>transform_data</b> verwendet werden — ohne weitere Bearbeitung.", st, "#e8f8f0"),
        _SP(8),

        _H1("6. Haeufige Fragen (FAQ)", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
    ]

    faqs_de = [
        (
            "Wie viele Dateien kann ich zusammenfuehren?",
            "Es gibt keine technische Obergrenze. In der Praxis sind 2–10 Dateien "
            "typisch (entspricht 200–10.000 Issues je nach Paginierungsgroesse)."
        ),
        (
            "Was passiert, wenn eine Eingabedatei kein 'issues'-Feld enthaelt?",
            "helper bricht mit einer Fehlermeldung ab und schreibt keine Ausgabedatei. "
            "Pruefen Sie, ob die Datei wirklich eine Jira-REST-API-Antwort ist."
        ),
        (
            "Kann ich die Ausgabe direkt in transform_data laden?",
            "Ja. Die Ausgabedatei enthaelt denselben Envelope wie eine regulaere "
            "Jira-API-Antwort und wird von transform_data akzeptiert."
        ),
        (
            "Was bedeutet 'Duplikat' in diesem Kontext?",
            "Ein Issue gilt als Duplikat, wenn zwei Eintraege dieselbe numerische "
            "'id' haben. Das kann vorkommen, wenn dasselbe Issue in mehreren "
            "paginierten Abfragen zurueckgegeben wurde."
        ),
        (
            "Kann ich auch JSON-Dateien aus Jira Cloud API v3 verwenden?",
            "Ja. helper unterstuetzt sowohl Jira API v2 als auch v3 — der 'issues'-"
            "Schlussel ist in beiden Versionen vorhanden."
        ),
    ]
    for q, a in faqs_de:
        story.append(_H2("F: " + q, st))
        story.append(_P("A: " + a, st))
        story.append(_SP(4))

    story += [
        PageBreak(),
        _H1("7. Glossar", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        tbl(
            [
                ["Begriff", "Erklaerung"],
                ["Deduplizierung", "Entfernen von doppelten Issues anhand der numerischen Issue-ID."],
                ["Envelope",       "Der aeussere Rahmen der Jira-API-JSON-Antwort mit Feldern wie startAt, total und maxResults."],
                ["Issue-ID",       "Eindeutige numerische ID eines Jira-Issues (Feld 'id'). Unterscheidet sich vom Issue-Key (z.B. ARTA-123)."],
                ["Jira Cloud API", "REST-API von Jira Cloud; liefert Issues als JSON mit 'issues'-Array."],
                ["JSON",           "JavaScript Object Notation — leichtgewichtiges Textformat fuer strukturierte Daten."],
                ["Paginierung",    "Aufteilen grosser API-Ergebnisse auf mehrere Abfragen (Seiten) aufgrund von API-Limits."],
                ["transform_data", "SituationReport-Modul, das Jira-JSON-Daten in eine XLSX-Datei (IssueTimes) umwandelt."],
            ],
            col_widths=[4*cm, 12*cm],
        ),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – English
# ---------------------------------------------------------------------------

def content_en(st: dict) -> list:
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        _H1("1. What is helper?", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "The <b>helper</b> module is a utility tool that merges multiple Jira REST API "
            "JSON files into a single file. It is needed when a Jira export was split across "
            "multiple files due to API limits and <b>transform_data</b> expects a single file.", st),
        _P(
            "helper automatically deduplicates issues by their unique issue ID and generates "
            "a correct Jira API envelope (startAt, total, maxResults). The output file can be "
            "processed directly by transform_data.", st),
        _SP(8),

        _H1("2. Starting", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _H2("2.1  As GUI (graphical interface)", st),
        _P("Double-click the appropriate launcher in the extracted folder:", st),
        tbl(
            [
                ["Operating system", "Start file"],
                ["Windows",  "Helper.bat  (double-click)"],
                ["macOS",    "Helper.command  (right-click -> Open)"],
                ["Linux",    "./Helper.sh"],
            ],
            col_widths=[4*cm, w - 4*cm],
        ),
        _SP(6),
        _H2("2.2  From source code", st),
        _CD("python -m helper", st),
        _SP(8),

        _H1("3. GUI Usage", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "The main window consists of three areas: the file list (top), "
            "the output file (middle), and the log area (bottom).", st),

        _H2("3.1  Adding input files", st),
        _P(
            "In the <b>Input files</b> area, one or more Jira JSON files can be added:", st),
        _BL(
            "<b>Add…</b> — Opens a file dialog where multiple files can be selected "
            "at once (Ctrl+click or Shift+click).", st),
        _BL(
            "<b>Remove</b> — Deletes the selected entries from the list "
            "(the files on disk are not affected).", st),
        _SP(4),
        _box(
            "<b>Tip:</b> The order in the list does not affect the result — all issues "
            "are merged and deduplicated independently of file order.", st, "#e8f8f0"),

        _H2("3.2  Choosing the output file", st),
        _P(
            "Enter the output file path in the <b>Output file (JSON)</b> field or "
            "select it using the <b>Browse…</b> button. The file is created when merging "
            "(overwritten if it already exists).", st),

        _H2("3.3  Remove duplicates", st),
        _P(
            "The checkbox <b>Remove duplicates (by issue id)</b> is enabled by default. "
            "Issues appearing in multiple input files with the same ID are written to the "
            "output only once. Each removed duplicate is logged.", st),
        _SP(4),
        _box(
            "<b>Note:</b> Deduplication is based on the <b>id</b> field in the Jira JSON "
            "(numeric issue ID). The <b>key</b> field (e.g. ARTA-123) is used for log "
            "display only.", st, "#fff8e1"),

        _H2("3.4  Starting the merge", st),
        _P(
            "Click the <b>Merge</b> button. Progress is shown in the log area. For longer "
            "operations a progress bar appears. After completion the log shows the number "
            "of merged and deduplicated issues along with the output file path.", st),
        _SP(8),

        _H1("4. CLI Mode", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "helper can also be called directly from the command line without a GUI:", st),
        _CD("python -m helper file1.json file2.json --output merged.json", st),
        _SP(4),
        tbl(
            [
                ["Parameter", "Description"],
                ["FILE …",        "At least one input JSON file (required)"],
                ["--output FILE", "Output file path (required)"],
                ["--no-dedup",    "Disable deduplication (keep all issues including duplicates)"],
            ],
            col_widths=[4.5*cm, w - 4.5*cm],
        ),
        _SP(8),

        _H1("5. Output Format", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "The output file is a valid Jira REST API JSON in the format of Jira Cloud "
            "API v2 / v3. The envelope is set automatically:", st),
        _SP(4),
        tbl(
            [
                ["Field", "Value"],
                ["expand",     "Taken from the first input file"],
                ["startAt",    "Always 0"],
                ["maxResults", "Number of merged issues"],
                ["total",      "Number of merged issues"],
                ["issues",     "All issues from all input files (after dedup)"],
            ],
            col_widths=[3.5*cm, w - 3.5*cm],
        ),
        _SP(4),
        _box(
            "<b>Compatibility:</b> The output file can be used directly as input for "
            "<b>transform_data</b> — no further processing required.", st, "#e8f8f0"),
        _SP(8),

        _H1("6. Frequently Asked Questions (FAQ)", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
    ]

    faqs_en = [
        (
            "How many files can I merge?",
            "There is no technical limit. In practice 2-10 files are typical "
            "(corresponding to 200-10,000 issues depending on pagination size)."
        ),
        (
            "What happens if an input file has no 'issues' field?",
            "helper aborts with an error message and writes no output file. "
            "Check that the file is a valid Jira REST API response."
        ),
        (
            "Can I load the output directly into transform_data?",
            "Yes. The output file contains the same envelope as a regular Jira API "
            "response and is accepted by transform_data."
        ),
        (
            "What does 'duplicate' mean in this context?",
            "An issue is a duplicate if two entries share the same numeric 'id'. "
            "This can happen when the same issue was returned in multiple paginated "
            "API queries."
        ),
        (
            "Can I use JSON files from Jira Cloud API v3?",
            "Yes. helper supports both Jira API v2 and v3 — the 'issues' key is "
            "present in both versions."
        ),
    ]
    for q, a in faqs_en:
        story.append(_H2("Q: " + q, st))
        story.append(_P("A: " + a, st))
        story.append(_SP(4))

    story += [
        PageBreak(),
        _H1("7. Glossary", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        tbl(
            [
                ["Term", "Explanation"],
                ["Deduplication", "Removing duplicate issues based on the numeric issue ID."],
                ["Envelope",      "The outer wrapper of the Jira API JSON response containing fields like startAt, total, and maxResults."],
                ["Issue ID",      "Unique numeric ID of a Jira issue (field 'id'). Different from the issue key (e.g. ARTA-123)."],
                ["Jira Cloud API","REST API of Jira Cloud; returns issues as JSON with an 'issues' array."],
                ["JSON",          "JavaScript Object Notation — lightweight text format for structured data."],
                ["Pagination",    "Splitting large API results across multiple requests (pages) due to API limits."],
                ["transform_data","SituationReport module that converts Jira JSON data into an XLSX file (IssueTimes)."],
            ],
            col_widths=[4*cm, 12*cm],
        ),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – Romanian
# ---------------------------------------------------------------------------

def content_ro(st: dict) -> list:
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        _H1("1. Ce este helper?", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Modulul <b>helper</b> este un instrument utilitар care combina mai multe "
            "fisiere Jira REST API JSON intr-un singur fisier. Este necesar atunci cand "
            "un export Jira a fost impartit in mai multe fisiere din cauza limitelor API "
            "si <b>transform_data</b> asteapta un singur fisier.", st),
        _P(
            "helper deduplica automat problemele dupa ID-ul lor unic si genereaza un "
            "envelope Jira API corect (startAt, total, maxResults). Fisierul de iesire "
            "poate fi procesat direct de transform_data.", st),
        _SP(8),

        _H1("2. Pornire", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _H2("2.1  Ca GUI (interfata grafica)", st),
        _P("Faceti dublu-clic pe fisierul de pornire corespunzator din folderul extras:", st),
        tbl(
            [
                ["Sistem de operare", "Fisier de pornire"],
                ["Windows",  "Helper.bat  (dublu-clic)"],
                ["macOS",    "Helper.command  (clic dreapta -> Deschidere)"],
                ["Linux",    "./Helper.sh"],
            ],
            col_widths=[4*cm, w - 4*cm],
        ),
        _SP(6),
        _H2("2.2  Din codul sursa", st),
        _CD("python -m helper", st),
        _SP(8),

        _H1("3. Utilizarea GUI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Fereastra principala consta din trei zone: lista de fisiere (sus), "
            "fisierul de iesire (mijloc) si zona de log (jos).", st),

        _H2("3.1  Adaugarea fisierelor de intrare", st),
        _P(
            "In zona <b>Fisiere de intrare</b>, pot fi adaugate unul sau mai multe "
            "fisiere Jira JSON:", st),
        _BL(
            "<b>Adaugare…</b> — Deschide un dialog de fisiere unde pot fi selectate "
            "mai multe fisiere simultan (Ctrl+clic sau Shift+clic).", st),
        _BL(
            "<b>Eliminare</b> — Sterge intrarile selectate din lista "
            "(fisierele de pe disc nu sunt afectate).", st),
        _SP(4),
        _box(
            "<b>Sfat:</b> Ordinea din lista nu afecteaza rezultatul — toate "
            "problemele sunt combinate si deduplicate indiferent de ordinea fisierelor.", st, "#e8f8f0"),

        _H2("3.2  Alegerea fisierului de iesire", st),
        _P(
            "Introduceti calea fisierului de iesire in campul <b>Fisier de iesire (JSON)</b> "
            "sau selectati-l folosind butonul <b>Navigare…</b>. Fisierul este creat la "
            "combinare (suprascris daca exista deja).", st),

        _H2("3.3  Eliminarea duplicatelor", st),
        _P(
            "Caseta de selectie <b>Eliminare duplicate (dupa ID issue)</b> este activata "
            "implicit. Problemele care apar in mai multe fisiere de intrare cu acelasi ID "
            "sunt scrise in iesire o singura data. Fiecare duplicat eliminat este inregistrat.", st),
        _SP(4),
        _box(
            "<b>Nota:</b> Deduplicarea se bazeaza pe campul <b>id</b> din JSON-ul Jira "
            "(ID numeric). Campul <b>key</b> (ex. ARTA-123) este folosit doar pentru "
            "afisarea in log.", st, "#fff8e1"),

        _H2("3.4  Pornirea combinarii", st),
        _P(
            "Faceti clic pe butonul <b>Combinare</b>. Progresul este afisat in zona de log. "
            "Pentru operatii mai lungi apare o bara de progres. Dupa finalizare, log-ul "
            "arata numarul de probleme combinate si deduplicate, impreuna cu calea "
            "fisierului de iesire.", st),
        _SP(8),

        _H1("4. Modul CLI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "helper poate fi apelat si direct din linia de comanda fara GUI:", st),
        _CD("python -m helper fisier1.json fisier2.json --output combinat.json", st),
        _SP(4),
        tbl(
            [
                ["Parametru", "Descriere"],
                ["FISIER …",      "Cel putin un fisier JSON de intrare (obligatoriu)"],
                ["--output FILE", "Calea fisierului de iesire (obligatoriu)"],
                ["--no-dedup",    "Dezactivare deduplicare (pastreaza toate problemele inclusiv duplicatele)"],
            ],
            col_widths=[4.5*cm, w - 4.5*cm],
        ),
        _SP(8),

        _H1("5. Formatul de iesire", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Fisierul de iesire este un JSON valid Jira REST API in formatul Jira Cloud "
            "API v2 / v3. Envelope-ul este setat automat corect:", st),
        _SP(4),
        tbl(
            [
                ["Camp", "Valoare"],
                ["expand",     "Preluat din primul fisier de intrare"],
                ["startAt",    "Intotdeauna 0"],
                ["maxResults", "Numarul de probleme combinate"],
                ["total",      "Numarul de probleme combinate"],
                ["issues",     "Toate problemele din toate fisierele de intrare (dupa dedup)"],
            ],
            col_widths=[3.5*cm, w - 3.5*cm],
        ),
        _SP(4),
        _box(
            "<b>Compatibilitate:</b> Fisierul de iesire poate fi folosit direct ca "
            "intrare pentru <b>transform_data</b> — fara procesare suplimentara.", st, "#e8f8f0"),
        _SP(8),

        _H1("6. Intrebari frecvente (FAQ)", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
    ]

    faqs_ro = [
        (
            "Cate fisiere pot combina?",
            "Nu exista o limita tehnica. In practica sunt tipice 2-10 fisiere "
            "(corespunzand la 200-10.000 de probleme in functie de dimensiunea paginarii)."
        ),
        (
            "Ce se intampla daca un fisier de intrare nu are campul 'issues'?",
            "helper se opreste cu un mesaj de eroare si nu scrie niciun fisier de iesire. "
            "Verificati daca fisierul este un raspuns valid Jira REST API."
        ),
        (
            "Pot incarca direct iesirea in transform_data?",
            "Da. Fisierul de iesire contine acelasi envelope ca un raspuns Jira API "
            "obisnuit si este acceptat de transform_data."
        ),
        (
            "Ce inseamna 'duplicat' in acest context?",
            "O problema este un duplicat daca doua intrari au acelasi 'id' numeric. "
            "Acest lucru poate aparea cand aceeasi problema a fost returnata in mai "
            "multe interogari API paginate."
        ),
        (
            "Pot folosi fisiere JSON din Jira Cloud API v3?",
            "Da. helper suporta atat Jira API v2 cat si v3 — cheia 'issues' este "
            "prezenta in ambele versiuni."
        ),
    ]
    for q, a in faqs_ro:
        story.append(_H2("I: " + q, st))
        story.append(_P("R: " + a, st))
        story.append(_SP(4))

    story += [
        PageBreak(),
        _H1("7. Glosar", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        tbl(
            [
                ["Termen", "Explicatie"],
                ["Deduplicare",   "Eliminarea problemelor duplicate pe baza ID-ului numeric."],
                ["Envelope",      "Structura exterioara a raspunsului JSON Jira API cu campuri precum startAt, total si maxResults."],
                ["ID Issue",      "ID numeric unic al unui issue Jira (campul 'id'). Diferit de cheia issue (ex. ARTA-123)."],
                ["Jira Cloud API","REST API al Jira Cloud; returneaza issues ca JSON cu un array 'issues'."],
                ["JSON",          "JavaScript Object Notation — format text usor pentru date structurate."],
                ["Paginare",      "Impartirea rezultatelor mari ale API in mai multe cereri (pagini) din cauza limitelor API."],
                ["transform_data","Modul SituationReport care converteste datele Jira JSON intr-un fisier XLSX (IssueTimes)."],
            ],
            col_widths=[4*cm, 12*cm],
        ),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – Portuguese
# ---------------------------------------------------------------------------

def content_pt(st: dict) -> list:
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        _H1("1. O que e o helper?", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "O modulo <b>helper</b> e uma ferramenta utilitaria que combina varios "
            "ficheiros Jira REST API JSON num unico ficheiro. E necessario quando uma "
            "exportacao Jira foi dividida em varios ficheiros devido a limites da API "
            "e o <b>transform_data</b> espera um unico ficheiro.", st),
        _P(
            "O helper deduplica automaticamente os issues pelo seu ID unico e gera um "
            "envelope Jira API correto (startAt, total, maxResults). O ficheiro de saida "
            "pode ser processado diretamente pelo transform_data.", st),
        _SP(8),

        _H1("2. Iniciar", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _H2("2.1  Como GUI (interface grafica)", st),
        _P("Faca duplo clique no ficheiro de inicio adequado na pasta extraida:", st),
        tbl(
            [
                ["Sistema operativo", "Ficheiro de inicio"],
                ["Windows",  "Helper.bat  (duplo clique)"],
                ["macOS",    "Helper.command  (clique direito -> Abrir)"],
                ["Linux",    "./Helper.sh"],
            ],
            col_widths=[4*cm, w - 4*cm],
        ),
        _SP(6),
        _H2("2.2  A partir do codigo fonte", st),
        _CD("python -m helper", st),
        _SP(8),

        _H1("3. Utilizacao da GUI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "A janela principal consiste em tres areas: a lista de ficheiros (cima), "
            "o ficheiro de saida (meio) e a area de log (baixo).", st),

        _H2("3.1  Adicionar ficheiros de entrada", st),
        _P(
            "Na area <b>Ficheiros de entrada</b>, podem ser adicionados um ou mais "
            "ficheiros Jira JSON:", st),
        _BL(
            "<b>Adicionar…</b> — Abre um dialogo de ficheiros onde varios ficheiros "
            "podem ser selecionados de uma vez (Ctrl+clique ou Shift+clique).", st),
        _BL(
            "<b>Remover</b> — Remove as entradas selecionadas da lista "
            "(os ficheiros no disco nao sao afetados).", st),
        _SP(4),
        _box(
            "<b>Dica:</b> A ordem na lista nao afeta o resultado — todos os issues "
            "sao combinados e desduplicados independentemente da ordem dos ficheiros.", st, "#e8f8f0"),

        _H2("3.2  Escolher o ficheiro de saida", st),
        _P(
            "Introduza o caminho do ficheiro de saida no campo <b>Ficheiro de saida (JSON)</b> "
            "ou selecione-o usando o botao <b>Procurar…</b>. O ficheiro e criado ao combinar "
            "(substituido se ja existir).", st),

        _H2("3.3  Remover duplicados", st),
        _P(
            "A caixa de verificacao <b>Remover duplicados (por ID do issue)</b> esta ativada "
            "por defeito. Issues que aparecem em varios ficheiros de entrada com o mesmo ID "
            "sao escritos na saida apenas uma vez. Cada duplicado removido e registado no log.", st),
        _SP(4),
        _box(
            "<b>Nota:</b> A desduplicacao baseia-se no campo <b>id</b> no JSON do Jira "
            "(ID numerico). O campo <b>key</b> (ex. ARTA-123) e usado apenas para "
            "visualizacao no log.", st, "#fff8e1"),

        _H2("3.4  Iniciar a combinacao", st),
        _P(
            "Clique no botao <b>Combinar</b>. O progresso e mostrado na area de log. "
            "Para operacoes mais longas aparece uma barra de progresso. Apos a conclusao, "
            "o log mostra o numero de issues combinados e desduplicados, juntamente com "
            "o caminho do ficheiro de saida.", st),
        _SP(8),

        _H1("4. Modo CLI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "O helper tambem pode ser chamado diretamente a partir da linha de comandos "
            "sem GUI:", st),
        _CD("python -m helper ficheiro1.json ficheiro2.json --output combinado.json", st),
        _SP(4),
        tbl(
            [
                ["Parametro", "Descricao"],
                ["FICHEIRO …",    "Pelo menos um ficheiro JSON de entrada (obrigatorio)"],
                ["--output FILE", "Caminho do ficheiro de saida (obrigatorio)"],
                ["--no-dedup",    "Desativar desduplicacao (manter todos os issues incluindo duplicados)"],
            ],
            col_widths=[4.5*cm, w - 4.5*cm],
        ),
        _SP(8),

        _H1("5. Formato de Saida", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "O ficheiro de saida e um JSON Jira REST API valido no formato da Jira Cloud "
            "API v2 / v3. O envelope e definido automaticamente:", st),
        _SP(4),
        tbl(
            [
                ["Campo", "Valor"],
                ["expand",     "Retirado do primeiro ficheiro de entrada"],
                ["startAt",    "Sempre 0"],
                ["maxResults", "Numero de issues combinados"],
                ["total",      "Numero de issues combinados"],
                ["issues",     "Todos os issues de todos os ficheiros de entrada (apos dedup)"],
            ],
            col_widths=[3.5*cm, w - 3.5*cm],
        ),
        _SP(4),
        _box(
            "<b>Compatibilidade:</b> O ficheiro de saida pode ser usado diretamente "
            "como entrada para <b>transform_data</b> — sem processamento adicional.", st, "#e8f8f0"),
        _SP(8),

        _H1("6. Perguntas Frequentes (FAQ)", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
    ]

    faqs_pt = [
        (
            "Quantos ficheiros posso combinar?",
            "Nao ha limite tecnico. Na pratica sao tipicos 2-10 ficheiros "
            "(correspondendo a 200-10.000 issues dependendo do tamanho da paginacao)."
        ),
        (
            "O que acontece se um ficheiro de entrada nao tiver o campo 'issues'?",
            "O helper para com uma mensagem de erro e nao escreve nenhum ficheiro de "
            "saida. Verifique se o ficheiro e uma resposta valida da Jira REST API."
        ),
        (
            "Posso carregar diretamente a saida no transform_data?",
            "Sim. O ficheiro de saida contem o mesmo envelope que uma resposta Jira API "
            "normal e e aceite pelo transform_data."
        ),
        (
            "O que significa 'duplicado' neste contexto?",
            "Um issue e um duplicado se duas entradas partilham o mesmo 'id' numerico. "
            "Isto pode acontecer quando o mesmo issue foi devolvido em multiplas "
            "consultas API paginadas."
        ),
        (
            "Posso usar ficheiros JSON da Jira Cloud API v3?",
            "Sim. O helper suporta tanto Jira API v2 como v3 — a chave 'issues' esta "
            "presente em ambas as versoes."
        ),
    ]
    for q, a in faqs_pt:
        story.append(_H2("P: " + q, st))
        story.append(_P("R: " + a, st))
        story.append(_SP(4))

    story += [
        PageBreak(),
        _H1("7. Glossario", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        tbl(
            [
                ["Termo", "Explicacao"],
                ["Desduplicacao",  "Remocao de issues duplicados com base no ID numerico do issue."],
                ["Envelope",       "O contentor exterior da resposta JSON Jira API com campos como startAt, total e maxResults."],
                ["ID do Issue",    "ID numerico unico de um issue Jira (campo 'id'). Diferente da chave do issue (ex. ARTA-123)."],
                ["Jira Cloud API", "REST API do Jira Cloud; devolve issues como JSON com um array 'issues'."],
                ["JSON",           "JavaScript Object Notation — formato de texto leve para dados estruturados."],
                ["Paginacao",      "Divisao de grandes resultados de API em multiplos pedidos (paginas) devido a limites da API."],
                ["transform_data", "Modulo SituationReport que converte dados Jira JSON num ficheiro XLSX (IssueTimes)."],
            ],
            col_widths=[4*cm, 12*cm],
        ),
    ]
    return story


# ---------------------------------------------------------------------------
# Content – French
# ---------------------------------------------------------------------------

def content_fr(st: dict) -> list:
    w = CONTENT_WIDTH_CM * cm
    story = [NextPageTemplate("normal"), PageBreak()]

    story += [
        _H1("1. Qu'est-ce que helper ?", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Le module <b>helper</b> est un outil utilitaire qui fusionne plusieurs "
            "fichiers Jira REST API JSON en un seul fichier. Il est necessaire lorsqu'un "
            "export Jira a ete divise en plusieurs fichiers en raison des limites de l'API "
            "et que <b>transform_data</b> attend un seul fichier.", st),
        _P(
            "helper deduplique automatiquement les issues par leur ID unique et genere "
            "une enveloppe Jira API correcte (startAt, total, maxResults). Le fichier de "
            "sortie peut etre traite directement par transform_data.", st),
        _SP(8),

        _H1("2. Demarrage", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _H2("2.1  Comme GUI (interface graphique)", st),
        _P("Double-cliquez sur le fichier de demarrage approprie dans le dossier extrait :", st),
        tbl(
            [
                ["Systeme d'exploitation", "Fichier de demarrage"],
                ["Windows",  "Helper.bat  (double-clic)"],
                ["macOS",    "Helper.command  (clic droit -> Ouvrir)"],
                ["Linux",    "./Helper.sh"],
            ],
            col_widths=[4*cm, w - 4*cm],
        ),
        _SP(6),
        _H2("2.2  Depuis le code source", st),
        _CD("python -m helper", st),
        _SP(8),

        _H1("3. Utilisation de la GUI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "La fenetre principale se compose de trois zones : la liste des fichiers "
            "(haut), le fichier de sortie (milieu) et la zone de log (bas).", st),

        _H2("3.1  Ajout des fichiers d'entree", st),
        _P(
            "Dans la zone <b>Fichiers d'entree</b>, un ou plusieurs fichiers Jira JSON "
            "peuvent etre ajoutes :", st),
        _BL(
            "<b>Ajouter…</b> — Ouvre une boite de dialogue ou plusieurs fichiers peuvent "
            "etre selectionnes a la fois (Ctrl+clic ou Shift+clic).", st),
        _BL(
            "<b>Supprimer</b> — Supprime les entrees selectionnees de la liste "
            "(les fichiers sur le disque ne sont pas affectes).", st),
        _SP(4),
        _box(
            "<b>Conseil :</b> L'ordre dans la liste n'affecte pas le resultat — tous "
            "les issues sont fusionnes et dedupliques independamment de l'ordre des "
            "fichiers.", st, "#e8f8f0"),

        _H2("3.2  Choix du fichier de sortie", st),
        _P(
            "Saisissez le chemin du fichier de sortie dans le champ "
            "<b>Fichier de sortie (JSON)</b> ou selectionnez-le avec le bouton "
            "<b>Parcourir…</b>. Le fichier est cree lors de la fusion "
            "(ecrase s'il existe deja).", st),

        _H2("3.3  Suppression des doublons", st),
        _P(
            "La case a cocher <b>Supprimer les doublons (par ID d'issue)</b> est activee "
            "par defaut. Les issues apparaissant dans plusieurs fichiers d'entree avec le "
            "meme ID ne sont ecrits dans la sortie qu'une seule fois. Chaque doublon "
            "supprime est consigne dans le log.", st),
        _SP(4),
        _box(
            "<b>Remarque :</b> La deduplication est basee sur le champ <b>id</b> dans "
            "le JSON Jira (ID numerique). Le champ <b>key</b> (ex. ARTA-123) est "
            "utilise uniquement pour l'affichage dans le log.", st, "#fff8e1"),

        _H2("3.4  Demarrage de la fusion", st),
        _P(
            "Cliquez sur le bouton <b>Fusionner</b>. La progression est affichee dans "
            "la zone de log. Pour les operations plus longues, une barre de progression "
            "apparait. Apres l'achevement, le log affiche le nombre d'issues fusionnes "
            "et dedupliques ainsi que le chemin du fichier de sortie.", st),
        _SP(8),

        _H1("4. Mode CLI", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "helper peut aussi etre appele directement depuis la ligne de commande "
            "sans GUI :", st),
        _CD("python -m helper fichier1.json fichier2.json --output fusionne.json", st),
        _SP(4),
        tbl(
            [
                ["Parametre", "Description"],
                ["FICHIER …",     "Au moins un fichier JSON d'entree (obligatoire)"],
                ["--output FILE", "Chemin du fichier de sortie (obligatoire)"],
                ["--no-dedup",    "Desactiver la deduplication (conserver tous les issues y compris les doublons)"],
            ],
            col_widths=[4.5*cm, w - 4.5*cm],
        ),
        _SP(8),

        _H1("5. Format de Sortie", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        _P(
            "Le fichier de sortie est un JSON Jira REST API valide au format Jira Cloud "
            "API v2 / v3. L'enveloppe est definie automatiquement :", st),
        _SP(4),
        tbl(
            [
                ["Champ", "Valeur"],
                ["expand",     "Recupere depuis le premier fichier d'entree"],
                ["startAt",    "Toujours 0"],
                ["maxResults", "Nombre d'issues fusionnes"],
                ["total",      "Nombre d'issues fusionnes"],
                ["issues",     "Tous les issues de tous les fichiers d'entree (apres dedup)"],
            ],
            col_widths=[3.5*cm, w - 3.5*cm],
        ),
        _SP(4),
        _box(
            "<b>Compatibilite :</b> Le fichier de sortie peut etre utilise directement "
            "comme entree pour <b>transform_data</b> — sans traitement supplementaire.", st, "#e8f8f0"),
        _SP(8),

        _H1("6. Questions Frequentes (FAQ)", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
    ]

    faqs_fr = [
        (
            "Combien de fichiers puis-je fusionner ?",
            "Il n'y a pas de limite technique. En pratique 2-10 fichiers sont typiques "
            "(correspondant a 200-10 000 issues selon la taille de la pagination)."
        ),
        (
            "Que se passe-t-il si un fichier d'entree n'a pas de champ 'issues' ?",
            "helper s'arrete avec un message d'erreur et n'ecrit aucun fichier de sortie. "
            "Verifiez que le fichier est bien une reponse Jira REST API valide."
        ),
        (
            "Puis-je charger directement la sortie dans transform_data ?",
            "Oui. Le fichier de sortie contient la meme enveloppe qu'une reponse Jira API "
            "standard et est accepte par transform_data."
        ),
        (
            "Que signifie 'doublon' dans ce contexte ?",
            "Un issue est un doublon si deux entrees partagent le meme 'id' numerique. "
            "Cela peut se produire lorsque le meme issue a ete retourne dans plusieurs "
            "requetes API paginées."
        ),
        (
            "Puis-je utiliser des fichiers JSON de Jira Cloud API v3 ?",
            "Oui. helper prend en charge Jira API v2 et v3 — la cle 'issues' est "
            "presente dans les deux versions."
        ),
    ]
    for q, a in faqs_fr:
        story.append(_H2("Q : " + q, st))
        story.append(_P("R : " + a, st))
        story.append(_SP(4))

    story += [
        PageBreak(),
        _H1("7. Glossaire", st),
        HRFlowable(width=w, thickness=1, color=C_ACCENT, spaceAfter=8),
        tbl(
            [
                ["Terme", "Explication"],
                ["Deduplication",  "Suppression des issues en double basee sur l'ID numerique."],
                ["Enveloppe",      "L'encadrement exterieur de la reponse JSON Jira API avec des champs comme startAt, total et maxResults."],
                ["ID d'Issue",     "ID numerique unique d'un issue Jira (champ 'id'). Different de la cle d'issue (ex. ARTA-123)."],
                ["Jira Cloud API", "REST API de Jira Cloud ; retourne les issues en JSON avec un tableau 'issues'."],
                ["JSON",           "JavaScript Object Notation — format texte leger pour les donnees structurees."],
                ["Pagination",     "Division des grands resultats d'API en plusieurs requetes (pages) en raison des limites de l'API."],
                ["transform_data", "Module SituationReport qui convertit les donnees Jira JSON en fichier XLSX (IssueTimes)."],
            ],
            col_widths=[4*cm, 12*cm],
        ),
    ]
    return story


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate helper (JSON Merger) user manual PDFs in all 5 languages."""
    st = make_styles()
    for lang, output, content_fn in [
        (LANG_DE, OUTPUT_DE, content_de),
        (LANG_EN, OUTPUT_EN, content_en),
        (LANG_RO, OUTPUT_RO, content_ro),
        (LANG_PT, OUTPUT_PT, content_pt),
        (LANG_FR, OUTPUT_FR, content_fr),
    ]:
        doc = _HelperDoc(str(output), lang=lang)
        story = content_fn(st)
        doc.multiBuild(story)
        print(f"PDF erstellt: {output}")


if __name__ == "__main__":
    main()
