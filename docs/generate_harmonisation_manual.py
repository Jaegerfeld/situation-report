# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geaendert:      12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer das Modul harmonisation als PDF
#   (5 Sprachen: DE, EN, RO, PT, FR). Einleitung, Start, Arbeitsbereich,
#   Oberflaeche, Antworten und Rechnung, die Matrix lesen, bewusste
#   Grenzen. Datengetriebener Ansatz wie bei simulate: ein Renderer, fuenf
#   Uebersetzungs-Dictionaries. Keine Bilder — die Matrix ist eine Tabelle
#   und wird als Tabelle erklaert.
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
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

from version import __version__ as _VERSION

C_BLUE   = colors.HexColor("#14304a")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR = "de", "en", "ro", "pt", "fr"
LANGS = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_OUTNAME = {
    LANG_DE: "harmonisation_Benutzerhandbuch.pdf",
    LANG_EN: "harmonisation_UserManual.pdf",
    LANG_RO: "harmonisation_ManualUtilizator.pdf",
    LANG_PT: "harmonisation_ManualUtilizador.pdf",
    LANG_FR: "harmonisation_ManuelUtilisateur.pdf",
}

_TBL_HDR = ParagraphStyle("H", fontName=_FB, fontSize=9, textColor=C_WHITE, leading=12)
_TBL_CELL = ParagraphStyle("C", fontName=_FN, fontSize=9, leading=12)


def make_styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)
    return dict(
        h1=s("H1", fontName=_FB, fontSize=18, textColor=C_BLUE, spaceBefore=22,
             spaceAfter=8, keepWithNext=1),
        h2=s("H2", fontName=_FB, fontSize=13, textColor=C_ACCENT, spaceBefore=13,
             spaceAfter=5, keepWithNext=1),
        body=s("Body", fontName=_FN, fontSize=10, leading=15, alignment=TA_JUSTIFY,
               spaceAfter=6),
        bullet=s("Bullet", fontName=_FN, fontSize=10, leading=14, leftIndent=16,
                 spaceAfter=3),
        caption=s("Cap", fontName=_FI, fontSize=8, textColor=C_HINT, leading=11,
                  alignment=TA_CENTER, spaceAfter=8),
        code=s("Code", fontName="Courier", fontSize=9, leading=13, leftIndent=12,
               spaceBefore=4, spaceAfter=4, backColor=colors.HexColor("#f4f4f4"),
               textColor=C_BLUE),
    )


# ---------------------------------------------------------------------------
# Document template + cover
# ---------------------------------------------------------------------------

class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, lang=LANG_EN, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._lang = lang
        m = 2.2 * cm
        w, h = A4
        self.addPageTemplates([
            PageTemplate(id="cover",
                         frames=[Frame(0, 0, w, h, id="cover", showBoundary=0)],
                         onPage=partial(build_cover, lang=lang)),
            PageTemplate(id="normal",
                         frames=[Frame(m, m, w - 2*m, h - 2*m - 1.2*cm,
                                       id="normal", showBoundary=0)],
                         onPage=self._hf),
        ])

    def _hf(self, canvas, doc):
        w, h = A4
        canvas.saveState()
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, h - 1.1*cm, w, 1.1*cm, fill=1, stroke=0)
        canvas.setFont(_FB, 9)
        canvas.setFillColor(C_WHITE)
        canvas.drawString(2.2*cm, h - 0.7*cm, f"harmonisation -- {T[self._lang]['header']}")
        canvas.drawRightString(w - 2.2*cm, h - 0.7*cm, "situation-report")
        canvas.setFillColor(C_HINT)
        canvas.setFont(_FN, 8)
        canvas.drawCentredString(w/2, 1.0*cm, T[self._lang]["page"] % doc.page)
        canvas.setStrokeColor(C_MID)
        canvas.line(2.2*cm, 1.4*cm, w - 2.2*cm, 1.4*cm)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if hasattr(flowable, "toc_level"):
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page))


def build_cover(canvas, doc, lang=LANG_EN):
    w, h = A4
    t = T[lang]
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont(_FB, 34)
    canvas.drawCentredString(w/2, h*0.60, "harmonisation")
    canvas.setFont(_FB, 18)
    canvas.drawCentredString(w/2, h*0.545, t["cover_sub"])
    canvas.setFont(_FN, 12)
    canvas.setFillColor(C_LIGHT)
    canvas.drawCentredString(w/2, h*0.49, t["cover_tag"])
    canvas.setStrokeColor(C_LIGHT)
    canvas.line(w*0.2, h*0.455, w*0.8, h*0.455)
    canvas.setFont(_FN, 9)
    canvas.setFillColor(C_MID)
    canvas.drawCentredString(w/2, h*0.12,
                             "situation-report - github.com/Jaegerfeld/situation-report")
    canvas.drawCentredString(w/2, h*0.09, f"{t['cover_aud']} — Version {_VERSION}")
    canvas.restoreState()


class _TocH(Paragraph):
    def __init__(self, text, style, level):
        super().__init__(text, style)
        self.toc_level = level


def H1(t, st): return _TocH(t, st["h1"], 0)
def H2(t, st): return _TocH(t, st["h2"], 1)
def P(t, st):  return Paragraph(t, st["body"])
def BL(t, st): return Paragraph("- " + t, st["bullet"])
def CD(t, st): return Paragraph(t, st["code"])
def SP(n=6):   return Spacer(1, n)


def box(text, st, bg="#eaf4fb"):
    tb = Table([[Paragraph(text, st["body"])]], colWidths=[16*cm])
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
        ("BOX", (0, 0), (-1, -1), 0.5, C_ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tb


def tbl(headers, rows, col_widths):
    def w(v, s):
        return Paragraph(str(v), s)
    data = ([[w(h, _TBL_HDR) for h in headers]]
            + [[w(c, _TBL_CELL) for c in row] for row in rows])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, C_MID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


# ---------------------------------------------------------------------------
# Texts
# ---------------------------------------------------------------------------

T = {
    LANG_DE: {
        "header": "Benutzerhandbuch", "page": "Seite %d",
        "cover_sub": "Harmonisierungs-Score", "cover_tag": "Benutzerhandbuch",
        "cover_aud": "Für Portfolio- und Prozessverantwortliche",
        "toc": "Inhalt",
        "s1_t": "1  Worum es geht",
        "s1_p": "Ein Konzern mit mehreren Marken oder Einheiten betreibt denselben End-to-End-Prozess "
                "oft in mehreren Varianten. Harmonisieren oder nicht – und wie tief? Ein "
                "Harmonisierungs-Score beantwortet das strukturiert: drei Dimensionen "
                "(Business Value, Transparenz, IT und Betrieb) mit acht Fragen je Prozess, dessen "
                "Ausgabe ein Lagebild auf Vorstandsebene speist. Das Modul harmonisation setzt diese "
                "Struktur um.",
        "s1_b1": "Fragenkatalog als Daten – der mitgelieferte Beispielkatalog ist eine Illustration; "
                 "Ihre eigenen Fragen kommen in dieselbe Datei.",
        "s1_b2": "Bewertungen je Prozess, versioniert als eine Datei je Bewertung, mit Antwort und "
                 "Beleggrad je Frage.",
        "s1_b3": "Entscheider-Matrix fürs Board: Score, Konfidenz und Spanne je Dimension – daneben "
                 "die Spalten, die das Board ausfüllt.",
        "s1_box": "<b>Befund, kein Urteil.</b> Das Werkzeug empfiehlt weder, was harmonisiert wird, "
                  "noch in welcher Tiefe. Es rechnet den Befund und hält fest, was das Board "
                  "entschieden hat. Es gibt keinen Harmonisierungs-Vorschlag, keine Rangliste und "
                  "keinen Gesamtscore – die Urteilszeile bleibt beim Menschen.",
        "s2_t": "2  Start",
        "s2_gui": "<b>Oberfläche:</b> <font face='Courier'>python -m harmonisation</font> – ohne "
                  "Argumente öffnet sich das Fenster.",
        "s2_cli": "<b>Kommandozeile:</b> ein Arbeitsbereich als Ordner, die Matrix als HTML:",
        "s2_code": "python -m harmonisation C:\\Lagebild\\harmo --lang de --browser<br/>"
                   "python -m harmonisation C:\\Lagebild\\harmo --example   # Beispiel anlegen",
        "s3_t": "3  Der Arbeitsbereich",
        "s3_p": "Ein Arbeitsbereich ist ein Ordner mit vier Bestandteilen, alle als JSON mit einer "
                "schema_version. Die Oberfläche legt ihn mit „Beispiel anlegen…“ fertig gefüllt an; "
                "danach ersetzen Sie Katalog und Prozesse durch Ihre eigenen.",
        "s3_h": ["Datei", "Inhalt"],
        "s3_rows": [
            ["catalogue.json", "Fragenkatalog: Dimensionen mit ihren Fragen; Text je Sprache, Englisch als Rückfall."],
            ["processes.json", "End-to-End-Prozesse: Kürzel, Name, Owner, beteiligte Marken oder Einheiten."],
            ["assessments/*.json", "Eine Datei je Bewertung: Prozess, Befragte(r), Datum, Antworten mit Beleggrad, Anmerkung."],
            ["decisions.json", "Entscheidung des Boards je Prozess: standardisieren, markenspezifisch oder offen – und die Tiefe im Wortlaut des Boards (optional)."],
        ],
        "s3_box": "Jede Frage ist so formuliert, dass hohe Zustimmung <b>für</b> eine Harmonisierung "
                  "spricht. Nur so lassen sich die Werte einer Dimension addieren. Prüfen Sie das, "
                  "wenn Sie eigene Fragen eintragen.",
        "s4_t": "4  Die Oberfläche",
        "s4_p": "Oben der Arbeitsbereich mit den Knöpfen Durchsuchen, Beispiel anlegen und Neu laden; "
                "rechts die Flagge zum Sprachwechsel. Darunter drei Reiter, unten die Sprache der "
                "Matrix und der Knopf, der sie erzeugt und im Browser öffnet. Rechts daneben das Feld „Stand seit“ mit dem Knopf für die Veränderung; in der Zeile darunter der Haken für die KI-Lesart und die Auswahl des Providers.",
        "s4_b1": "<b>Prozesse:</b> Liste der Prozesse; neue mit Kürzel, Name, Owner und Marken anlegen.",
        "s4_b2": "<b>Bewertung:</b> Prozess, Befragte(r) und Datum wählen; je Frage einen Wert 0–4 oder "
                 "„?“ (unbekannt) anklicken und den Beleggrad setzen; speichern legt die Datei im "
                 "Ordner assessments ab.",
        "s4_b3": "<b>Entscheidung:</b> je Prozess die Entscheidung des Boards, die Tiefe im Wortlaut, "
                 "Datum und Gremium.",
        "s5_t": "5  Antworten und Rechnung",
        "s5_p": "Der Score ist absichtlich einfach, damit ihn jedes Board nachrechnen kann.",
        "s5_h": ["Größe", "Bedeutung"],
        "s5_rows": [
            ["Wert je Frage", "0 „trifft nicht zu“ bis 4 „trifft voll zu“. <b>„Unbekannt“ ist eine zulässige Antwort</b> – ein Lagebild, das Unwissen nicht ausweisen kann, täuscht Sicherheit vor."],
            ["Beleggrad", "belegt (Dokument, Messung, System) · geschätzt (Einschätzung der befragten Person) · Hörensagen."],
            ["Score je Dimension", "Mittel der beantworteten Fragen, auf 0–100 gebracht; dazu „n von 8 beantwortet“."],
            ["Konfidenz", "Anteil belegter Antworten an <b>allen</b> Fragen der Dimension: hoch ab zwei Dritteln, mittel ab einem Drittel, sonst niedrig. „Unbekannt“ senkt die Konfidenz, nicht den Score."],
            ["Mehrere Bewertungen", "Median als Score, Spanne (höchste minus niedrigste Bewertung) daneben. Zwei Befragte, die denselben Prozess völlig verschieden sehen, sind ein Befund, kein Rauschen."],
            ["Gesamtscore", "Gibt es nicht. Drei Zahlen nebeneinander sind ehrlicher als eine, die drei verschiedene Dinge verrechnet."],
        ],
        "s6_t": "6  Die Matrix lesen",
        "s6_p": "Farbschlüssel und Legende stehen vor der ersten Tabelle. Der Score ist blau abgestuft "
                "– ein Befund, keine Ampel. Ampelfarben trägt nur die Konfidenz.",
        "s6_h": ["Spalte", "Inhalt"],
        "s6_rows": [
            ["Prozess", "Name, Owner, Marken."],
            ["Je Dimension", "Score, Zahl der Bewertungen, beantwortete Fragen, Spanne, Konfidenz-Badge. „Keine Bewertung“, wenn noch nichts erfasst ist."],
            ["Entscheidung des Boards", "standardisieren · markenspezifisch · offen, mit Datum und Gremium."],
            ["Tiefe", "Der Wortlaut des Boards – bewusst Freitext, keine vorgegebene Skala."],
        ],
        "s6_p2": "Unter der Matrix folgt die zweite Lesart: jede Bewertung mit jeder Antwort und ihrem "
                 "Beleggrad. Wer eine Zahl in der Matrix anzweifelt, findet dort, woraus sie besteht.",
        "s7_t": "7  Bewusste Grenzen und Tipps",
        "s7_b1": "Kein Vorschlag, keine Rangliste, keine empfohlene Tiefe – das ist Absicht, kein Mangel.",
        "s7_b2": "Keine KI im Kern: Die Rechnung ist deterministisch und nur Standardbibliothek. Die optionale KI-Lesart formuliert nur, gekennzeichnet als Entwurf, und rechnet nichts.",
        "s7_b3": "Lassen Sie jeden Prozess von mehr als einer Person bewerten – erst die Spanne zeigt, wo das Bild geteilt ist und wo nicht.",
        "s7_b4": "Antworten Sie „unbekannt“, statt zu raten. Niedrige Konfidenz ist eine Aussage; ein geratener Wert ist eine Täuschung.",
        "s8_t": '8  Veränderung, KI-Lesart, Konferenzmappe',
        "s8_p": 'Seit Schritt 2 hat die Matrix drei Anschlüsse. Keiner ändert die Rechnung – sie zeigen sie anders oder an anderer Stelle.',
        "s8_h": ['Baustein', 'Was er tut'],
        "s8_rows": [
            ['Veränderung zweier Stände', "„Was hat sich seit der letzten Bewertung geändert?“ Bewertungen sind datiert, darum rechnet <font face='Courier'>--since JJJJ-MM-TT</font> den Stand von damals aus den heutigen Dateien zurück; <font face='Courier'>--delta ORDNER</font> vergleicht mit einem zweiten Arbeitsbereich. Je Prozess und Dimension Score, Konfidenz, Spanne und Zahl der Bewertungen alt → neu; dazu neue Bewertungen (nur Datum), Entscheidungen des Boards, hinzugekommene oder entfallene Prozesse. „Keine Änderungen“ wird ausdrücklich gesagt. Ein gesunkener Score ist keine Verschlechterung, sondern ein anderer Befund."],
            ['KI-Lesart (Entwurf)', "<font face='Courier'>--narrate</font> (Standard: ollama, lokal) oder der Haken in der Oberfläche. Das Modell sieht nur einen Contract mit allen Zahlen der Matrix oder der Veränderung – Prozesse, Dimensionen, Marken, nie Personen. Jede Zahl im Text muss im Contract stehen, sonst wird der Entwurf verworfen; der Prompt untersagt jede Empfehlung, was harmonisiert wird. Der Entwurf steht gekennzeichnet direkt unter der Tabelle und zusätzlich in <font face='Courier'>…reading.md</font> zum Redigieren; der Betreiber-Nachweis landet in llm_audit.jsonl."],
            ['Konferenzmappe', "Im Portfolio-Modul trägt eine Solution das Feld <font face='Courier'>harmonisation</font> mit dem Ordner des Arbeitsbereichs (Datenquellen-Dialog, zehntes Feld). Die Konferenzmappe zeigt die Matrix dann als Anhang nach Input 4 – eine Board-Sicht, kein fünfter Konferenz-Input."],
        ],
        "s8_code": "python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20<br/>python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20 --narrate<br/>python -m harmonisation C:\\Lagebild\\harmo --narrate mock",
        "s8_box": '<b>Scheitert die KI, steht die Seite trotzdem.</b> Die deterministische Matrix oder Veränderung wird immer geschrieben; fehlt der Entwurf, sagt es die Statuszeile bzw. der Rückgabewert 3 der Kommandozeile.',
    },
    LANG_EN: {
        "header": "User Manual", "page": "Page %d",
        "cover_sub": "Harmonisation score", "cover_tag": "User manual",
        "cover_aud": "For portfolio and process owners",
        "toc": "Contents",
        "s1_t": "1  What it is about",
        "s1_p": "A group with several brands or units often runs the same end-to-end process in "
                "several variants. Harmonise or not – and how deep? A harmonisation score answers "
                "that in a structured way: three dimensions (business value, "
                "transparency, IT and operations) with eight questions per process, feeding a "
                "board-level situational picture. The harmonisation module implements that structure.",
        "s1_b1": "Question catalogue as data – the bundled example is an illustration; your own "
                 "questions go into the same file.",
        "s1_b2": "Assessments per process, versioned as one file each, with a value and an evidence "
                 "level per question.",
        "s1_b3": "Decision matrix for the board: score, confidence and spread per dimension – next to "
                 "the columns the board fills in.",
        "s1_box": "<b>A finding, not a judgement.</b> The tool recommends neither what to harmonise "
                  "nor how deep. It computes the finding and records what the board decided. There is "
                  "no harmonisation proposal, no ranking and no overall score – the judgement line "
                  "stays with people.",
        "s2_t": "2  Getting started",
        "s2_gui": "<b>GUI:</b> <font face='Courier'>python -m harmonisation</font> – without arguments "
                  "the window opens.",
        "s2_cli": "<b>Command line:</b> a workspace folder in, the matrix as HTML out:",
        "s2_code": "python -m harmonisation C:\\Lagebild\\harmo --lang en --browser<br/>"
                   "python -m harmonisation C:\\Lagebild\\harmo --example   # create the example",
        "s3_t": "3  The workspace",
        "s3_p": "A workspace is a folder with four parts, all JSON with a schema_version. The GUI "
                "creates it ready-filled via “Create example…”; afterwards you replace catalogue and "
                "processes with your own.",
        "s3_h": ["File", "Content"],
        "s3_rows": [
            ["catalogue.json", "Question catalogue: dimensions with their questions; text per language, English as fallback."],
            ["processes.json", "End-to-end processes: id, name, owner, brands or units involved."],
            ["assessments/*.json", "One file per assessment: process, assessor, date, answers with evidence level, note."],
            ["decisions.json", "The board's decision per process: standardise, brand-specific or open – and the depth in the board's wording (optional)."],
        ],
        "s3_box": "Every question is phrased so that strong agreement speaks <b>for</b> harmonisation. "
                  "Only then can the values of a dimension be added up. Check this when you enter "
                  "your own questions.",
        "s4_t": "4  The GUI",
        "s4_p": "At the top the workspace with Browse, Create example and Reload; on the right the "
                "flag to switch languages. Below, three tabs; at the bottom the matrix language and "
                "the button that generates it and opens it in the browser. Next to it the “Since” field with the button for the change; in the row below the checkbox for the AI reading and the provider choice.",
        "s4_b1": "<b>Processes:</b> the list of processes; add new ones with id, name, owner and brands.",
        "s4_b2": "<b>Assessment:</b> choose process, assessor and date; per question click a value 0–4 "
                 "or “?” (unknown) and set the evidence level; saving writes the file into the "
                 "assessments folder.",
        "s4_b3": "<b>Decision:</b> per process the board's decision, the depth in its wording, date "
                 "and body.",
        "s5_t": "5  Answers and arithmetic",
        "s5_p": "The score is deliberately simple so that any board can recompute it.",
        "s5_h": ["Quantity", "Meaning"],
        "s5_rows": [
            ["Value per question", "0 “does not apply” to 4 “fully applies”. <b>“Unknown” is a permitted answer</b> – a situational picture that cannot show ignorance fakes certainty."],
            ["Evidence", "documented (document, measurement, system) · estimated (the assessor's judgement) · hearsay."],
            ["Score per dimension", "Mean of the answered questions, scaled to 0–100; plus “n of 8 answered”."],
            ["Confidence", "Share of documented answers over <b>all</b> questions of the dimension: high from two thirds, medium from one third, otherwise low. “Unknown” lowers the confidence, not the score."],
            ["Several assessments", "Median as the score, spread (highest minus lowest assessment) next to it. Two people who see the same process very differently are a finding, not noise."],
            ["Overall score", "There is none. Three numbers side by side are more honest than one that nets three different things."],
        ],
        "s6_t": "6  Reading the matrix",
        "s6_p": "Colour key and legend come before the first table. The score is shaded in blue – a "
                "finding, not a traffic light. Only the confidence carries traffic-light colours.",
        "s6_h": ["Column", "Content"],
        "s6_rows": [
            ["Process", "Name, owner, brands."],
            ["Per dimension", "Score, number of assessments, questions answered, spread, confidence badge. “No assessment” while nothing is recorded."],
            ["Board decision", "standardise · brand-specific · open, with date and body."],
            ["Depth", "The board's own wording – deliberately free text, no preset scale."],
        ],
        "s6_p2": "Below the matrix follows the second reading: every assessment with every answer and "
                 "its evidence level. Whoever doubts a number in the matrix finds there what it is made of.",
        "s7_t": "7  Deliberate limits and tips",
        "s7_b1": "No proposal, no ranking, no recommended depth – by design, not by omission.",
        "s7_b2": "No AI in the core: the computation is deterministic, standard library only. The optional AI reading only phrases, labeled as a draft, and computes nothing.",
        "s7_b3": "Have every process assessed by more than one person – only the spread shows where the picture is shared and where it is not.",
        "s7_b4": "Answer “unknown” instead of guessing. Low confidence is a statement; a guessed value is a deception.",
        "s8_t": '8  Change, AI reading, conference pre-read',
        "s8_p": 'Since step 2 the matrix has three connections. None of them changes the arithmetic – they show it differently or somewhere else.',
        "s8_h": ['Building block', 'What it does'],
        "s8_rows": [
            ['Change between two states', "“What has changed since the last assessment?” Assessments are dated, so <font face='Courier'>--since YYYY-MM-DD</font> recomputes the earlier state from today's files; <font face='Courier'>--delta FOLDER</font> compares against a second workspace. Per process and dimension score, confidence, spread and number of assessments old → new; plus new assessments (date only), board decisions, processes added or removed. “No changes” is said explicitly. A lower score is not a worsening but a different finding."],
            ['AI reading (draft)', "<font face='Courier'>--narrate</font> (default: ollama, local) or the checkbox in the GUI. The model sees only a contract with every number of the matrix or the change – processes, dimensions, brands, never persons. Every number in the text must appear in the contract, otherwise the draft is discarded; the prompt forbids any recommendation on what to harmonise. The draft sits labeled directly below the table and additionally in <font face='Courier'>…reading.md</font> for editing; the operator evidence goes to llm_audit.jsonl."],
            ['Conference pre-read', "In the portfolio module a solution carries the field <font face='Courier'>harmonisation</font> with the workspace folder (data-sources dialog, tenth field). The pre-read then shows the matrix as an annex after input 4 – a board view, not a fifth conference input."],
        ],
        "s8_code": "python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20<br/>python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20 --narrate<br/>python -m harmonisation C:\\Lagebild\\harmo --narrate mock",
        "s8_box": "<b>If the AI fails, the page still stands.</b> The deterministic matrix or change is always written; a missing draft is reported in the status line or by the command line's exit code 3.",
    },
    LANG_RO: {
        "header": "Manual de utilizare", "page": "Pagina %d",
        "cover_sub": "Scor de armonizare", "cover_tag": "Manual de utilizare",
        "cover_aud": "Pentru responsabilii de portofoliu și de proces",
        "toc": "Cuprins",
        "s1_t": "1  Despre ce este vorba",
        "s1_p": "Un grup cu mai multe mărci sau unități rulează adesea același proces end-to-end în mai "
                "multe variante. Armonizare sau nu – și cât de adânc? Un scor de armonizare "
                "răspunde structurat: trei dimensiuni (valoare de business, transparență, IT "
                "și operare) cu opt întrebări per proces, care alimentează un tablou de situație la nivel "
                "de board. Modulul harmonisation implementează această structură.",
        "s1_b1": "Catalog de întrebări ca date – exemplul livrat este o ilustrare; întrebările dvs. intră în același fișier.",
        "s1_b2": "Evaluări per proces, versionate câte un fișier fiecare, cu valoare și grad de dovadă per întrebare.",
        "s1_b3": "Matricea decidenților pentru board: scor, încredere și interval per dimensiune – lângă coloanele completate de board.",
        "s1_box": "<b>Constatare, nu judecată.</b> Instrumentul nu recomandă nici ce se armonizează, nici cât de adânc. "
                  "Calculează constatarea și reține ce a decis board-ul. Nu există propunere de armonizare, clasament "
                  "sau scor total – linia de judecată rămâne la oameni.",
        "s2_t": "2  Pornire",
        "s2_gui": "<b>Interfață:</b> <font face='Courier'>python -m harmonisation</font> – fără argumente se deschide fereastra.",
        "s2_cli": "<b>Linie de comandă:</b> un dosar ca spațiu de lucru, matricea ca HTML:",
        "s2_code": "python -m harmonisation C:\\Lagebild\\harmo --lang ro --browser<br/>"
                   "python -m harmonisation C:\\Lagebild\\harmo --example   # creează exemplul",
        "s3_t": "3  Spațiul de lucru",
        "s3_p": "Un spațiu de lucru este un dosar cu patru componente, toate JSON cu schema_version. Interfața îl "
                "creează gata completat prin „Creează exemplul…“; apoi înlocuiți catalogul și procesele cu ale dvs.",
        "s3_h": ["Fișier", "Conținut"],
        "s3_rows": [
            ["catalogue.json", "Catalogul de întrebări: dimensiuni cu întrebările lor; text per limbă, engleza ca rezervă."],
            ["processes.json", "Procese end-to-end: id, nume, responsabil, mărci sau unități implicate."],
            ["assessments/*.json", "Un fișier per evaluare: proces, evaluator, dată, răspunsuri cu grad de dovadă, notă."],
            ["decisions.json", "Decizia board-ului per proces: standardizare, specific mărcii sau deschis – și profunzimea în formularea board-ului (opțional)."],
        ],
        "s3_box": "Fiecare întrebare este formulată astfel încât acordul puternic pledează <b>pentru</b> armonizare. "
                  "Numai așa valorile unei dimensiuni pot fi adunate. Verificați acest lucru la întrebările proprii.",
        "s4_t": "4  Interfața",
        "s4_p": "Sus spațiul de lucru cu Răsfoire, Creează exemplul și Reîncarcă; în dreapta steagul pentru limbă. "
                "Dedesubt trei file; jos limba matricei și butonul care o generează și o deschide în browser. Alături câmpul „Stare din“ cu butonul pentru schimbare; în rândul de dedesubt bifa pentru lectura AI și alegerea furnizorului.",
        "s4_b1": "<b>Procese:</b> lista proceselor; adăugați altele cu id, nume, responsabil și mărci.",
        "s4_b2": "<b>Evaluare:</b> alegeți proces, evaluator și dată; per întrebare o valoare 0–4 sau „?“ (necunoscut) "
                 "și gradul de dovadă; salvarea scrie fișierul în dosarul assessments.",
        "s4_b3": "<b>Decizie:</b> per proces decizia board-ului, profunzimea în formularea sa, data și organul.",
        "s5_t": "5  Răspunsuri și calcul",
        "s5_p": "Scorul este intenționat simplu, ca orice board să îl poată recalcula.",
        "s5_h": ["Mărime", "Semnificație"],
        "s5_rows": [
            ["Valoare per întrebare", "0 „nu se aplică“ până la 4 „se aplică pe deplin“. <b>„Necunoscut“ este un răspuns permis</b> – un tablou care nu poate arăta necunoașterea simulează certitudine."],
            ["Grad de dovadă", "documentat (document, măsurătoare, sistem) · estimat (aprecierea evaluatorului) · din auzite."],
            ["Scor per dimensiune", "Media întrebărilor cu răspuns, adusă la 0–100; plus „n din 8 cu răspuns“."],
            ["Încredere", "Ponderea răspunsurilor documentate din <b>toate</b> întrebările dimensiunii: ridicată de la două treimi, medie de la o treime, altfel scăzută. „Necunoscut“ scade încrederea, nu scorul."],
            ["Mai multe evaluări", "Mediana ca scor, intervalul (cea mai mare minus cea mai mică) alături. Doi evaluatori care văd același proces complet diferit sunt o constatare, nu zgomot."],
            ["Scor total", "Nu există. Trei numere alăturate sunt mai oneste decât unul care amestecă trei lucruri diferite."],
        ],
        "s6_t": "6  Citirea matricei",
        "s6_p": "Legenda culorilor stă înaintea primului tabel. Scorul este în nuanțe de albastru – o constatare, nu un semafor. Doar încrederea poartă culori de semafor.",
        "s6_h": ["Coloană", "Conținut"],
        "s6_rows": [
            ["Proces", "Nume, responsabil, mărci."],
            ["Per dimensiune", "Scor, număr de evaluări, întrebări cu răspuns, interval, insigna de încredere. „Nicio evaluare“ cât timp nu s-a înregistrat nimic."],
            ["Decizia board-ului", "standardizare · specific mărcii · deschis, cu dată și organ."],
            ["Profunzime", "Formularea board-ului – intenționat text liber, fără scară prestabilită."],
        ],
        "s6_p2": "Sub matrice urmează a doua lectură: fiecare evaluare cu fiecare răspuns și gradul său de dovadă. Cine pune la îndoială un număr găsește acolo din ce este format.",
        "s7_t": "7  Limite intenționate și sfaturi",
        "s7_b1": "Nicio propunere, niciun clasament, nicio profunzime recomandată – prin design, nu din omisiune.",
        "s7_b2": "Fără AI în nucleu: calculul este determinist, doar biblioteca standard. Lectura AI opțională doar formulează, marcată ca schiță, și nu calculează nimic.",
        "s7_b3": "Lăsați fiecare proces evaluat de mai mult de o persoană – doar intervalul arată unde imaginea este împărtășită și unde nu.",
        "s7_b4": "Răspundeți „necunoscut“ în loc să ghiciți. Încrederea scăzută este o afirmație; o valoare ghicită este o înșelăciune.",
        "s8_t": '8  Schimbare, lectură AI, mapa conferinței',
        "s8_p": 'De la pasul 2 matricea are trei conexiuni. Niciuna nu schimbă calculul – îl arată altfel sau în alt loc.',
        "s8_h": ['Componentă', 'Ce face'],
        "s8_rows": [
            ['Schimbarea între două stări', "„Ce s-a schimbat de la ultima evaluare?“ Evaluările sunt datate, așa că <font face='Courier'>--since AAAA-LL-ZZ</font> recalculează starea de atunci din fișierele de azi; <font face='Courier'>--delta DOSAR</font> compară cu un al doilea spațiu de lucru. Per proces și dimensiune scor, încredere, interval și număr de evaluări vechi → nou; plus evaluări noi (doar data), deciziile board-ului, procese adăugate sau eliminate. „Nicio schimbare“ se spune explicit. Un scor mai mic nu este o înrăutățire, ci o altă constatare."],
            ['Lectură AI (schiță)', "<font face='Courier'>--narrate</font> (implicit: ollama, local) sau bifa din interfață. Modelul vede doar un contract cu toate cifrele matricei sau ale schimbării – procese, dimensiuni, mărci, niciodată persoane. Fiecare cifră din text trebuie să apară în contract, altfel schița este respinsă; promptul interzice orice recomandare despre ce să se armonizeze. Schița stă marcată direct sub tabel și în plus în <font face='Courier'>…reading.md</font> pentru redactare; dovada operatorului ajunge în llm_audit.jsonl."],
            ['Mapa conferinței', "În modulul portfolio o soluție poartă câmpul <font face='Courier'>harmonisation</font> cu dosarul spațiului de lucru (dialogul surselor de date, al zecelea câmp). Mapa arată apoi matricea ca anexă după input 4 – o imagine a board-ului, nu un al cincilea input al conferinței."],
        ],
        "s8_code": "python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20<br/>python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20 --narrate<br/>python -m harmonisation C:\\Lagebild\\harmo --narrate mock",
        "s8_box": '<b>Dacă AI eșuează, pagina rămâne.</b> Matricea sau schimbarea deterministă se scrie întotdeauna; lipsa schiței este anunțată în linia de stare sau prin codul de ieșire 3 al liniei de comandă.',
    },
    LANG_PT: {
        "header": "Manual do utilizador", "page": "Página %d",
        "cover_sub": "Score de harmonização", "cover_tag": "Manual do utilizador",
        "cover_aud": "Para responsáveis de portefólio e de processo",
        "toc": "Índice",
        "s1_t": "1  Do que se trata",
        "s1_p": "Um grupo com várias marcas ou unidades executa muitas vezes o mesmo processo end-to-end em "
                "várias variantes. Harmonizar ou não – e com que profundidade? Um score de harmonização "
                "responde de forma estruturada: três dimensões (valor de negócio, transparência, TI e "
                "operações) com oito perguntas por processo, alimentando um quadro de situação ao nível do board. "
                "O módulo harmonisation implementa essa estrutura.",
        "s1_b1": "Catálogo de perguntas como dados – o exemplo fornecido é uma ilustração; as suas perguntas entram no mesmo ficheiro.",
        "s1_b2": "Avaliações por processo, versionadas num ficheiro cada, com valor e nível de evidência por pergunta.",
        "s1_b3": "Matriz de decisão para o board: score, confiança e amplitude por dimensão – ao lado das colunas que o board preenche.",
        "s1_box": "<b>Resultado, não juízo.</b> A ferramenta não recomenda o que harmonizar nem em que profundidade. "
                  "Calcula o resultado e regista o que o board decidiu. Não há proposta de harmonização, ranking nem "
                  "score global – a linha do juízo fica com as pessoas.",
        "s2_t": "2  Início",
        "s2_gui": "<b>Interface:</b> <font face='Courier'>python -m harmonisation</font> – sem argumentos abre-se a janela.",
        "s2_cli": "<b>Linha de comandos:</b> uma pasta como área de trabalho, a matriz como HTML:",
        "s2_code": "python -m harmonisation C:\\Lagebild\\harmo --lang pt --browser<br/>"
                   "python -m harmonisation C:\\Lagebild\\harmo --example   # criar o exemplo",
        "s3_t": "3  A área de trabalho",
        "s3_p": "Uma área de trabalho é uma pasta com quatro partes, todas JSON com schema_version. A interface cria-a "
                "já preenchida com «Criar exemplo…»; depois substitui o catálogo e os processos pelos seus.",
        "s3_h": ["Ficheiro", "Conteúdo"],
        "s3_rows": [
            ["catalogue.json", "Catálogo de perguntas: dimensões com as suas perguntas; texto por idioma, inglês como recurso."],
            ["processes.json", "Processos end-to-end: id, nome, responsável, marcas ou unidades envolvidas."],
            ["assessments/*.json", "Um ficheiro por avaliação: processo, avaliador, data, respostas com nível de evidência, nota."],
            ["decisions.json", "Decisão do board por processo: padronizar, específico da marca ou em aberto – e a profundidade nas palavras do board (opcional)."],
        ],
        "s3_box": "Cada pergunta está formulada de modo que a forte concordância fala <b>a favor</b> da harmonização. "
                  "Só assim os valores de uma dimensão podem ser somados. Verifique isto ao introduzir as suas perguntas.",
        "s4_t": "4  A interface",
        "s4_p": "Em cima a área de trabalho com Procurar, Criar exemplo e Recarregar; à direita a bandeira para mudar de idioma. "
                "Por baixo três separadores; em baixo o idioma da matriz e o botão que a gera e abre no browser. Ao lado o campo «Desde» com o botão para a alteração; na linha abaixo a caixa para a leitura por IA e a escolha do fornecedor.",
        "s4_b1": "<b>Processos:</b> lista dos processos; adicionar novos com id, nome, responsável e marcas.",
        "s4_b2": "<b>Avaliação:</b> escolher processo, avaliador e data; por pergunta um valor 0–4 ou «?» (desconhecido) "
                 "e o nível de evidência; guardar escreve o ficheiro na pasta assessments.",
        "s4_b3": "<b>Decisão:</b> por processo a decisão do board, a profundidade nas suas palavras, data e órgão.",
        "s5_t": "5  Respostas e cálculo",
        "s5_p": "O score é deliberadamente simples para que qualquer board o possa recalcular.",
        "s5_h": ["Grandeza", "Significado"],
        "s5_rows": [
            ["Valor por pergunta", "0 «não se aplica» até 4 «aplica-se totalmente». <b>«Desconhecido» é uma resposta permitida</b> – um quadro que não consegue mostrar ignorância finge certeza."],
            ["Evidência", "documentado (documento, medição, sistema) · estimado (juízo do avaliador) · por ouvir dizer."],
            ["Score por dimensão", "Média das perguntas respondidas, levada a 0–100; mais «n de 8 respondidas»."],
            ["Confiança", "Proporção de respostas documentadas em <b>todas</b> as perguntas da dimensão: alta a partir de dois terços, média a partir de um terço, senão baixa. «Desconhecido» baixa a confiança, não o score."],
            ["Várias avaliações", "Mediana como score, amplitude (mais alta menos mais baixa) ao lado. Duas pessoas que veem o mesmo processo de forma muito diferente são um resultado, não ruído."],
            ["Score global", "Não existe. Três números lado a lado são mais honestos do que um que mistura três coisas diferentes."],
        ],
        "s6_t": "6  Ler a matriz",
        "s6_p": "A chave de cores e a legenda vêm antes da primeira tabela. O score está em tons de azul – um resultado, não um semáforo. Só a confiança usa cores de semáforo.",
        "s6_h": ["Coluna", "Conteúdo"],
        "s6_rows": [
            ["Processo", "Nome, responsável, marcas."],
            ["Por dimensão", "Score, número de avaliações, perguntas respondidas, amplitude, distintivo de confiança. «Sem avaliação» enquanto nada estiver registado."],
            ["Decisão do board", "padronizar · específico da marca · em aberto, com data e órgão."],
            ["Profundidade", "As palavras do board – deliberadamente texto livre, sem escala predefinida."],
        ],
        "s6_p2": "Abaixo da matriz segue a segunda leitura: cada avaliação com cada resposta e o seu nível de evidência. Quem duvida de um número encontra ali de que é feito.",
        "s7_t": "7  Limites deliberados e dicas",
        "s7_b1": "Sem proposta, sem ranking, sem profundidade recomendada – por desenho, não por omissão.",
        "s7_b2": "Sem IA no núcleo: o cálculo é determinístico, só biblioteca padrão. A leitura por IA opcional apenas formula, marcada como rascunho, e não calcula nada.",
        "s7_b3": "Faça avaliar cada processo por mais de uma pessoa – só a amplitude mostra onde a imagem é partilhada e onde não é.",
        "s7_b4": "Responda «desconhecido» em vez de adivinhar. Confiança baixa é uma afirmação; um valor adivinhado é um engano.",
        "s8_t": '8  Alteração, leitura por IA, dossier da conferência',
        "s8_p": 'Desde o passo 2 a matriz tem três ligações. Nenhuma altera o cálculo – mostram-no de outra forma ou noutro lugar.',
        "s8_h": ['Componente', 'O que faz'],
        "s8_rows": [
            ['Alteração entre dois estados', "«O que mudou desde a última avaliação?» As avaliações têm data, por isso <font face='Courier'>--since AAAA-MM-DD</font> recalcula o estado de então a partir dos ficheiros de hoje; <font face='Courier'>--delta PASTA</font> compara com uma segunda área de trabalho. Por processo e dimensão score, confiança, amplitude e número de avaliações antigo → novo; mais novas avaliações (só a data), decisões do board, processos adicionados ou removidos. «Sem alterações» é dito explicitamente. Um score mais baixo não é uma piora, mas um resultado diferente."],
            ['Leitura por IA (rascunho)', "<font face='Courier'>--narrate</font> (padrão: ollama, local) ou a caixa na interface. O modelo vê apenas um contrato com todos os números da matriz ou da alteração – processos, dimensões, marcas, nunca pessoas. Cada número no texto tem de constar do contrato, senão o rascunho é rejeitado; o prompt proíbe qualquer recomendação sobre o que harmonizar. O rascunho fica marcado diretamente sob a tabela e ainda em <font face='Courier'>…reading.md</font> para redigir; a evidência do operador vai para llm_audit.jsonl."],
            ['Dossier da conferência', "No módulo portfolio uma solução traz o campo <font face='Courier'>harmonisation</font> com a pasta da área de trabalho (diálogo das fontes de dados, décimo campo). O dossier mostra então a matriz como anexo após o input 4 – uma visão do board, não um quinto input da conferência."],
        ],
        "s8_code": "python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20<br/>python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20 --narrate<br/>python -m harmonisation C:\\Lagebild\\harmo --narrate mock",
        "s8_box": '<b>Se a IA falhar, a página fica.</b> A matriz ou alteração determinística é sempre escrita; a falta do rascunho é indicada na linha de estado ou pelo código de saída 3 da linha de comandos.',
    },
    LANG_FR: {
        "header": "Manuel utilisateur", "page": "Page %d",
        "cover_sub": "Score d'harmonisation", "cover_tag": "Manuel utilisateur",
        "cover_aud": "Pour les responsables de portefeuille et de processus",
        "toc": "Sommaire",
        "s1_t": "1  De quoi il s'agit",
        "s1_p": "Un groupe comptant plusieurs marques ou entités exploite souvent le même processus de bout en bout "
                "en plusieurs variantes. Harmoniser ou non – et à quelle profondeur ? Un score "
                "d'harmonisation y répond de façon structurée : trois dimensions (valeur métier, transparence, IT et "
                "exploitation) avec huit questions par processus, alimentant une image de situation au niveau du board. "
                "Le module harmonisation met cette structure en œuvre.",
        "s1_b1": "Catalogue de questions sous forme de données – l'exemple fourni est une illustration ; vos propres questions vont dans le même fichier.",
        "s1_b2": "Évaluations par processus, versionnées un fichier chacune, avec valeur et niveau de preuve par question.",
        "s1_b3": "Matrice de décision pour le board : score, confiance et écart par dimension – à côté des colonnes que remplit le board.",
        "s1_box": "<b>Un constat, pas un jugement.</b> L'outil ne recommande ni quoi harmoniser ni à quelle profondeur. "
                  "Il calcule le constat et consigne ce que le board a décidé. Pas de proposition d'harmonisation, pas de "
                  "classement, pas de score global – la ligne du jugement reste aux humains.",
        "s2_t": "2  Démarrage",
        "s2_gui": "<b>Interface :</b> <font face='Courier'>python -m harmonisation</font> – sans argument, la fenêtre s'ouvre.",
        "s2_cli": "<b>Ligne de commande :</b> un dossier comme espace de travail, la matrice en HTML :",
        "s2_code": "python -m harmonisation C:\\Lagebild\\harmo --lang fr --browser<br/>"
                   "python -m harmonisation C:\\Lagebild\\harmo --example   # créer l'exemple",
        "s3_t": "3  L'espace de travail",
        "s3_p": "Un espace de travail est un dossier à quatre composants, tous en JSON avec schema_version. L'interface le "
                "crée déjà rempli via « Créer l'exemple… » ; ensuite vous remplacez catalogue et processus par les vôtres.",
        "s3_h": ["Fichier", "Contenu"],
        "s3_rows": [
            ["catalogue.json", "Catalogue de questions : dimensions avec leurs questions ; texte par langue, anglais en repli."],
            ["processes.json", "Processus de bout en bout : id, nom, responsable, marques ou entités concernées."],
            ["assessments/*.json", "Un fichier par évaluation : processus, évaluateur, date, réponses avec niveau de preuve, remarque."],
            ["decisions.json", "Décision du board par processus : standardiser, propre à la marque ou ouvert – et la profondeur dans les termes du board (facultatif)."],
        ],
        "s3_box": "Chaque question est formulée de sorte qu'un fort accord plaide <b>pour</b> l'harmonisation. "
                  "C'est la seule façon d'additionner les valeurs d'une dimension. Vérifiez-le en saisissant vos propres questions.",
        "s4_t": "4  L'interface",
        "s4_p": "En haut l'espace de travail avec Parcourir, Créer l'exemple et Recharger ; à droite le drapeau pour changer de langue. "
                "En dessous trois onglets ; en bas la langue de la matrice et le bouton qui la génère et l'ouvre dans le navigateur. À côté le champ « Depuis » avec le bouton de l'évolution ; sur la ligne du dessous la case pour la lecture IA et le choix du fournisseur.",
        "s4_b1": "<b>Processus :</b> la liste des processus ; en ajouter avec id, nom, responsable et marques.",
        "s4_b2": "<b>Évaluation :</b> choisir processus, évaluateur et date ; par question une valeur 0–4 ou « ? » (inconnu) "
                 "et le niveau de preuve ; l'enregistrement écrit le fichier dans le dossier assessments.",
        "s4_b3": "<b>Décision :</b> par processus la décision du board, la profondeur dans ses termes, date et instance.",
        "s5_t": "5  Réponses et calcul",
        "s5_p": "Le score est volontairement simple, pour que tout board puisse le recalculer.",
        "s5_h": ["Grandeur", "Signification"],
        "s5_rows": [
            ["Valeur par question", "0 « ne s'applique pas » à 4 « s'applique pleinement ». <b>« Inconnu » est une réponse autorisée</b> – une image de situation qui ne peut pas montrer l'ignorance feint la certitude."],
            ["Preuve", "documenté (document, mesure, système) · estimé (jugement de l'évaluateur) · par ouï-dire."],
            ["Score par dimension", "Moyenne des questions répondues, ramenée à 0–100 ; plus « n sur 8 répondues »."],
            ["Confiance", "Part des réponses documentées sur <b>toutes</b> les questions de la dimension : élevée à partir de deux tiers, moyenne à partir d'un tiers, sinon faible. « Inconnu » baisse la confiance, pas le score."],
            ["Plusieurs évaluations", "Médiane comme score, écart (la plus haute moins la plus basse) à côté. Deux personnes qui voient le même processus très différemment sont un constat, pas du bruit."],
            ["Score global", "Il n'y en a pas. Trois chiffres côte à côte sont plus honnêtes qu'un seul qui mélange trois choses différentes."],
        ],
        "s6_t": "6  Lire la matrice",
        "s6_p": "Le code couleur et la légende précèdent le premier tableau. Le score est en nuances de bleu – un constat, pas un feu tricolore. Seule la confiance porte des couleurs de feu.",
        "s6_h": ["Colonne", "Contenu"],
        "s6_rows": [
            ["Processus", "Nom, responsable, marques."],
            ["Par dimension", "Score, nombre d'évaluations, questions répondues, écart, badge de confiance. « Aucune évaluation » tant que rien n'est saisi."],
            ["Décision du board", "standardiser · propre à la marque · ouvert, avec date et instance."],
            ["Profondeur", "Les termes du board – texte libre à dessein, sans échelle imposée."],
        ],
        "s6_p2": "Sous la matrice suit la deuxième lecture : chaque évaluation avec chaque réponse et son niveau de preuve. Qui doute d'un chiffre y trouve de quoi il est fait.",
        "s7_t": "7  Limites voulues et conseils",
        "s7_b1": "Pas de proposition, pas de classement, pas de profondeur recommandée – par conception, non par oubli.",
        "s7_b2": "Pas d'IA dans le cœur : le calcul est déterministe, bibliothèque standard uniquement. La lecture IA optionnelle ne fait que formuler, marquée comme brouillon, et ne calcule rien.",
        "s7_b3": "Faites évaluer chaque processus par plus d'une personne – seul l'écart montre où l'image est partagée et où elle ne l'est pas.",
        "s7_b4": "Répondez « inconnu » plutôt que de deviner. Une confiance faible est une affirmation ; une valeur devinée est une tromperie.",
        "s8_t": '8  Évolution, lecture IA, dossier de conférence',
        "s8_p": "Depuis l'étape 2, la matrice a trois raccordements. Aucun ne change le calcul – ils le montrent autrement ou ailleurs.",
        "s8_h": ['Brique', "Ce qu'elle fait"],
        "s8_rows": [
            ['Évolution entre deux états', "« Qu'est-ce qui a changé depuis la dernière évaluation ? » Les évaluations sont datées, donc <font face='Courier'>--since AAAA-MM-JJ</font> recalcule l'état d'alors à partir des fichiers d'aujourd'hui ; <font face='Courier'>--delta DOSSIER</font> compare avec un second espace de travail. Par processus et dimension score, confiance, écart et nombre d'évaluations ancien → nouveau ; plus les nouvelles évaluations (date seulement), les décisions du board, les processus ajoutés ou retirés. « Aucun changement » est dit explicitement. Un score plus bas n'est pas une dégradation mais un autre constat."],
            ['Lecture IA (brouillon)', "<font face='Courier'>--narrate</font> (par défaut : ollama, local) ou la case dans l'interface. Le modèle ne voit qu'un contrat avec tous les chiffres de la matrice ou de l'évolution – processus, dimensions, marques, jamais de personnes. Chaque chiffre du texte doit figurer dans le contrat, sinon le brouillon est rejeté ; le prompt interdit toute recommandation sur ce qu'il faut harmoniser. Le brouillon se place, marqué, directement sous le tableau et en plus dans <font face='Courier'>…reading.md</font> pour la révision ; la preuve d'exploitation va dans llm_audit.jsonl."],
            ['Dossier de conférence', "Dans le module portfolio, une solution porte le champ <font face='Courier'>harmonisation</font> avec le dossier de l'espace de travail (dialogue des sources de données, dixième champ). Le dossier de conférence montre alors la matrice en annexe après l'input 4 – une vue du board, pas un cinquième input de conférence."],
        ],
        "s8_code": "python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20<br/>python -m harmonisation C:\\Lagebild\\harmo --since 2026-09-20 --narrate<br/>python -m harmonisation C:\\Lagebild\\harmo --narrate mock",
        "s8_box": "<b>Si l'IA échoue, la page reste.</b> La matrice ou l'évolution déterministe est toujours écrite ; l'absence de brouillon est signalée dans la ligne d'état ou par le code de retour 3 de la ligne de commande.",
    },
}


# ---------------------------------------------------------------------------
# Story renderer (one function, all languages)
# ---------------------------------------------------------------------------

def build_story(lang, st):
    t = T[lang]
    story = []
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())
    story.append(H1(t["toc"], st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("T1", fontName=_FB, fontSize=11, leading=18, spaceAfter=2),
        ParagraphStyle("T2", fontName=_FN, fontSize=9, leading=15, leftIndent=16),
    ]
    story.append(toc)

    story.append(PageBreak())
    story.append(H1(t["s1_t"], st))
    story.append(P(t["s1_p"], st))
    for k in ("s1_b1", "s1_b2", "s1_b3"):
        story.append(BL(t[k], st))
    story.append(SP(6))
    story.append(box(t["s1_box"], st))

    story.append(H1(t["s2_t"], st))
    story.append(BL(t["s2_gui"], st))
    story.append(P(t["s2_cli"], st))
    story.append(CD(t["s2_code"], st))

    story.append(H1(t["s3_t"], st))
    story.append(P(t["s3_p"], st))
    story.append(tbl(t["s3_h"], t["s3_rows"], [4.5*cm, 11.5*cm]))
    story.append(SP(8))
    story.append(box(t["s3_box"], st, bg="#fdf3e7"))

    story.append(H1(t["s4_t"], st))
    story.append(P(t["s4_p"], st))
    for k in ("s4_b1", "s4_b2", "s4_b3"):
        story.append(BL(t[k], st))

    story.append(H1(t["s5_t"], st))
    story.append(P(t["s5_p"], st))
    story.append(tbl(t["s5_h"], t["s5_rows"], [4.0*cm, 12.0*cm]))

    story.append(PageBreak())
    story.append(H1(t["s6_t"], st))
    story.append(P(t["s6_p"], st))
    story.append(tbl(t["s6_h"], t["s6_rows"], [4.5*cm, 11.5*cm]))
    story.append(SP(6))
    story.append(P(t["s6_p2"], st))

    story.append(H1(t["s7_t"], st))
    for k in ("s7_b1", "s7_b2", "s7_b3", "s7_b4"):
        story.append(BL(t[k], st))

    story.append(PageBreak())
    story.append(H1(t["s8_t"], st))
    story.append(P(t["s8_p"], st))
    story.append(tbl(t["s8_h"], t["s8_rows"], [4.0*cm, 12.0*cm]))
    story.append(SP(6))
    story.append(CD(t["s8_code"], st))
    story.append(SP(6))
    story.append(box(t["s8_box"], st, bg="#fdf3e7"))
    return story


def main():
    """Generate the harmonisation manual PDFs for all five languages."""
    st = make_styles()
    out_dir = Path(__file__).parent
    for lang in LANGS:
        out_path = out_dir / _OUTNAME[lang]
        doc = ManualDoc(str(out_path), lang=lang)
        doc.multiBuild(build_story(lang, st))
        print(f"PDF erstellt: {out_path}")


if __name__ == "__main__":
    main()
