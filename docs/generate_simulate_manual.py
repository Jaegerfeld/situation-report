# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstuetzung: Erstellt mit Unterstuetzung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geaendert:      01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch fuer das Modul simulate als PDF (5 Sprachen:
#   DE, EN, RO, PT, FR). Enthaelt Einleitung, Start, Eingabedatei, GUI mit
#   Screenshot, Parameter, Interpretation der drei Report-Ansichten
#   (Scope-Konfidenz-Gauge, Exceedance-Kurve, Termin-Verteilung) mit echten
#   Beispieldiagrammen aus den ART_A-Testdaten sowie Tipps. Datengetriebener
#   Ansatz: ein Renderer, fuenf Uebersetzungs-Dictionaries.
# =============================================================================

import sys
import tempfile
from datetime import date, timedelta
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _font_config import setup as _setup_fonts

_FN, _FB, _FI, _FBI = _setup_fonts()  # normal, bold, italic, bold_italic

import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus.tableofcontents import TableOfContents

from version import __version__ as _VERSION

# ---------------------------------------------------------------------------
# Paths / colours / styles
# ---------------------------------------------------------------------------
_TESTDATA    = Path(__file__).parent.parent / "tests" / "testdata" / "ART_A"
_ISSUE_TIMES = _TESTDATA / "ART_A_IssueTimes.xlsx"
_GUI_SHOT    = Path(__file__).parent / "assets" / "Simulate-GUI.png"

C_BLUE   = colors.HexColor("#14304a")
C_ACCENT = colors.HexColor("#2980b9")
C_LIGHT  = colors.HexColor("#ecf0f1")
C_MID    = colors.HexColor("#bdc3c7")
C_WHITE  = colors.white
C_HINT   = colors.HexColor("#7f8c8d")

CONTENT_WIDTH_CM = 15.5

LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR = "de", "en", "ro", "pt", "fr"
LANGS = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_OUTNAME = {
    LANG_DE: "simulate_Benutzerhandbuch.pdf",
    LANG_EN: "simulate_UserManual.pdf",
    LANG_RO: "simulate_ManualUtilizator.pdf",
    LANG_PT: "simulate_ManualUtilizador.pdf",
    LANG_FR: "simulate_ManuelUtilisateur.pdf",
}

_TBL_HDR = ParagraphStyle("H", fontName=_FB, fontSize=9, textColor=C_WHITE, leading=12)
_TBL_CELL = ParagraphStyle("C", fontName=_FN, fontSize=9, leading=12)


def make_styles():
    """Build the paragraph style dictionary."""
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
# Chart images (from ART_A test data, via the real simulate engine)
# ---------------------------------------------------------------------------

def _generate_chart_images(out_dir: Path) -> dict[str, Path]:
    """Render example forecast charts from the ART_A dataset as PNGs."""
    import random

    from build_reports.loader import load_report_data
    from simulate.charts import how_many_figure, scope_confidence_figure, when_done_figure
    from simulate.forecast import how_many, probability_at_least, when_done
    from simulate.throughput import closed_dates, to_sample

    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_report_data(_ISSUE_TIMES)
    cds = closed_dates(data)
    end = (cds[-1] + timedelta(days=1)) if cds else date.today()
    start = end - timedelta(days=365)
    sample = to_sample(data, start, end)

    horizon = 84
    backlog = max(5, round(sample.mean_per_day * horizon * 0.9))
    rng = random.Random(7)
    fc_hm = how_many(sample, horizon, 20000, rng=rng)
    prob = probability_at_least(fc_hm, backlog)
    target_date = date.today() + timedelta(days=horizon)
    fc_wd = when_done(sample, backlog, 20000, rng=rng, split_rate=0.1,
                      start_date=date.today())

    def save(fig, name, w=1400, h=460):
        p = out_dir / f"{name}.png"
        pio.write_image(fig, str(p), format="png", width=w, height=h)
        return p

    return {
        "gauge": save(scope_confidence_figure(prob, backlog, target_date), "gauge", h=380),
        "exceedance": save(how_many_figure(fc_hm, target=backlog), "exceedance"),
        "whendone": save(when_done_figure(fc_wd), "whendone"),
    }


def _img(path: Path, width_cm: float = CONTENT_WIDTH_CM) -> RLImage:
    ri = RLImage(str(path))
    w = width_cm * cm
    return RLImage(str(path), width=w, height=w * (ri.imageHeight / ri.imageWidth))


# ---------------------------------------------------------------------------
# Document template + cover
# ---------------------------------------------------------------------------

class ManualDoc(BaseDocTemplate):
    """Cover + normal page templates with a language-aware header/footer."""

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
        canvas.drawString(2.2*cm, h - 0.7*cm, f"simulate -- {T[self._lang]['header']}")
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
    """Draw the two-tone cover page."""
    w, h = A4
    t = T[lang]
    canvas.saveState()
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h*0.35, w, h*0.32, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont(_FB, 34)
    canvas.drawCentredString(w/2, h*0.60, "simulate")
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


# ---------------------------------------------------------------------------
# Flowable helpers
# ---------------------------------------------------------------------------

class _TocH(Paragraph):
    def __init__(self, text, style, level):
        super().__init__(text, style)
        self.toc_level = level


def H1(t, st): return _TocH(t, st["h1"], 0)
def H2(t, st): return _TocH(t, st["h2"], 1)
def P(t, st):  return Paragraph(t, st["body"])
def BL(t, st): return Paragraph("- " + t, st["bullet"])
def CD(t, st): return Paragraph(t, st["code"])
def CAP(t, st): return Paragraph(t, st["caption"])
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
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

T: dict[str, dict] = {
    LANG_DE: {
        "cover_sub": "Benutzerhandbuch",
        "cover_tag": "Monte-Carlo-Forecast fuer agile Teams",
        "cover_aud": "Fuer nicht-technische Anwender",
        "header": "Benutzerhandbuch", "page": "Seite %d", "toc": "Inhalt",
        "s1_t": "1  Was ist simulate?",
        "s1_p": "simulate erstellt aus den historischen Lieferdaten Ihres Teams eine "
                "Wahrscheinlichkeits-Vorhersage (Monte-Carlo-Simulation). Grundlage ist "
                "allein der <b>Durchsatz</b> - wie viele Aufgaben pro Tag abgeschlossen "
                "werden. Es sind keine Schaetzungen (Story Points) noetig. Beantwortet "
                "werden drei Fragen:",
        "s1_b1": "<b>Wie viele</b> Items schaffen wir in einem Zeitraum?",
        "s1_b2": "<b>Wann</b> ist ein Backlog von N Items <b>fertig</b>?",
        "s1_b3": "<b>Schaffen wir den Scope</b> bis zu einem Stichtag?",
        "s1_box": "Die Ergebnisse sind immer <b>Wahrscheinlichkeiten</b>, keine "
                  "Einzelwerte. 'Mit 85 % Konfidenz mindestens 20 Items' heisst: In "
                  "85 von 100 simulierten Zukunftsverlaeufen wurden 20 oder mehr Items "
                  "geschafft.",
        "s2_t": "2  Programm starten",
        "s2_gui": "<b>Ueber den Launcher:</b> Die Kachel <b>Simulate</b> im "
                  "SituationReport-Startfenster anklicken.",
        "s2_cli": "<b>Direkt:</b> ohne Argumente oeffnet sich die GUI, mit Argumenten "
                  "laeuft die Kommandozeile:",
        "s2_code": "python -m simulate ART_A_IssueTimes.xlsx --horizon 84 "
                   "--backlog 20 --output forecast.html",
        "s3_t": "3  Eingabedatei",
        "s3_p": "simulate benoetigt eine <b>IssueTimes.xlsx</b>, wie sie das Modul "
                "<b>transform_data</b> erzeugt. Fuer die Vorhersage zaehlt nur das "
                "Abschlussdatum (Closed Date) der Issues. Eine optionale CFD.xlsx kann "
                "zusaetzlich angegeben werden.",
        "s4_t": "4  Die Oberflaeche (GUI)",
        "s4_p": "Waehlen Sie oben die IssueTimes-Datei und stellen Sie darunter die "
                "Parameter ein. Ein Klick auf <b>Report erzeugen</b> fragt nach einem "
                "Speicherort und oeffnet den fertigen Report im Browser.",
        "s4_cap": "Abb. 1: Die simulate-Oberflaeche mit Datei- und Parameterfeldern.",
        "s4_th": ["Feld", "Bedeutung"],
        "s4_rows": [
            ["History-Fenster (Tage)", "Wie weit zurueck die historischen Daten "
             "betrachtet werden (Standard 180). Enthaelt bewusst auch Null-Tage."],
            ["History-Ende", "Enddatum des Fensters (leer = heute)."],
            ["Horizont (Tage)", "Zeitraum in die Zukunft fuer 'Wie viele' (Standard 84)."],
            ["Backlog", "Anzahl Items fuer Termin- und Scope-Konfidenz-Vorhersage "
             "(leer = nur 'Wie viele')."],
            ["Laeufe", "Anzahl Simulationsdurchgaenge (Standard 25000). Mehr = glatter."],
            ["Scope-Wachstum", "Erwartete neue Items je erledigtem Item (z. B. 0.1 = "
             "+10 % Nacharbeit/Splits)."],
            ["Seed", "Fester Startwert fuer reproduzierbare Ergebnisse (leer = zufaellig)."],
        ],
        "s5_t": "5  Den Report lesen",
        "s5_p": "Bei gesetztem Backlog enthaelt der Report drei aufeinander bezogene "
                "Ansichten - alle aus denselben Simulationslaeufen.",
        "s5a_t": "5.1  Scope-Konfidenz-Gauge",
        "s5a_p": "Die Tacho-Anzeige zeigt die Wahrscheinlichkeit, den Backlog bis zum "
                 "Horizont-Datum zu schaffen. Die rote Linie markiert die 85%-Schwelle; "
                 "die Farbzonen (rot/gelb/gruen) helfen bei der schnellen Einordnung.",
        "s5a_cap": "Abb. 2: Scope-Konfidenz - wie sicher schaffen wir den Scope bis zum Stichtag?",
        "s5b_t": "5.2  Exceedance-Kurve (Wie viele)",
        "s5b_p": "Die Kurve zeigt fuer jede Item-Menge die Wahrscheinlichkeit, "
                 "<b>mindestens</b> so viele zu schaffen. Die gestrichelten Linien bei "
                 "85/75/50 % sind Ablese-Hilfen: hohe Konfidenz = kleinere garantierte "
                 "Menge. Die senkrechte Linie markiert Ihren Backlog.",
        "s5b_cap": "Abb. 3: Exceedance-Kurve - Wahrscheinlichkeit, mindestens X Items zu schaffen.",
        "s5c_t": "5.3  Termin-Verteilung (Wann fertig)",
        "s5c_p": "Das Balkendiagramm zeigt, an welchem Tag der Backlog in den "
                 "Simulationen fertig wurde. Die Konfidenz-Linien nennen den Tag und das "
                 "Datum je Sicherheitsstufe. Konfidenzstufen, die im gesetzten "
                 "Zeitrahmen nicht erreichbar sind, werden als 'nicht im Rahmen' "
                 "ausgewiesen - nie als geschoenter Termin.",
        "s5c_cap": "Abb. 4: Termin-Verteilung - Tage bis zur Fertigstellung mit Konfidenz-Linien.",
        "s6_t": "6  Tipps",
        "s6_b1": "<b>Seed setzen</b>, wenn Sie exakt denselben Report reproduzieren wollen.",
        "s6_b2": "<b>Null-Tage sind Absicht:</b> Ein zuletzt ruhiger Zeitraum senkt die "
                 "Vorhersage korrekt - das Fenster deshalb nicht kuenstlich verkuerzen.",
        "s6_b3": "<b>Nicht ueberinterpretieren:</b> Eine 60%-Konfidenz ist kein Versagen, "
                 "sondern eine ehrliche Aussage ueber Unsicherheit.",
        "s6_b4": "<b>Scope-Wachstum</b> realistisch waehlen: Bei Epics entstehen aus einem "
                 "Item oft weitere - das verschiebt den Termin nach hinten.",
    },
    LANG_EN: {
        "cover_sub": "User Manual",
        "cover_tag": "Monte-Carlo forecasting for agile teams",
        "cover_aud": "For non-technical users",
        "header": "User Manual", "page": "Page %d", "toc": "Contents",
        "s1_t": "1  What is simulate?",
        "s1_p": "simulate turns your team's historical delivery data into a probabilistic "
                "forecast (a Monte-Carlo simulation). It is based purely on "
                "<b>throughput</b> - how many items are completed per day. No estimates "
                "(story points) are required. It answers three questions:",
        "s1_b1": "<b>How many</b> items will we complete in a given period?",
        "s1_b2": "<b>When</b> will a backlog of N items <b>be done</b>?",
        "s1_b3": "<b>Will we finish the scope</b> by a target date?",
        "s1_box": "Results are always <b>probabilities</b>, not single numbers. "
                  "'At least 20 items with 85 % confidence' means: in 85 of 100 simulated "
                  "futures, 20 or more items were completed.",
        "s2_t": "2  Starting the program",
        "s2_gui": "<b>From the launcher:</b> click the <b>Simulate</b> card in the "
                  "SituationReport start window.",
        "s2_cli": "<b>Directly:</b> without arguments the GUI opens, with arguments the "
                  "command line runs:",
        "s2_code": "python -m simulate ART_A_IssueTimes.xlsx --horizon 84 "
                   "--backlog 20 --output forecast.html",
        "s3_t": "3  Input file",
        "s3_p": "simulate needs an <b>IssueTimes.xlsx</b> as produced by the "
                "<b>transform_data</b> module. Only the issues' Closed Date matters for "
                "the forecast. An optional CFD.xlsx may also be provided.",
        "s4_t": "4  The interface (GUI)",
        "s4_p": "Pick the IssueTimes file at the top and set the parameters below. "
                "Clicking <b>Generate report</b> asks for a location and opens the "
                "finished report in your browser.",
        "s4_cap": "Fig. 1: The simulate interface with file and parameter fields.",
        "s4_th": ["Field", "Meaning"],
        "s4_rows": [
            ["History window (days)", "How far back the historical data is considered "
             "(default 180). Deliberately includes zero-throughput days."],
            ["History end", "End of the window (empty = today)."],
            ["Horizon (days)", "How far into the future for 'how many' (default 84)."],
            ["Backlog", "Number of items for the date and scope-confidence forecast "
             "(empty = 'how many' only)."],
            ["Runs", "Number of simulation runs (default 25000). More = smoother."],
            ["Scope growth", "Expected new items per completed item (e.g. 0.1 = +10 % "
             "rework/splits)."],
            ["Seed", "Fixed starting value for reproducible results (empty = random)."],
        ],
        "s5_t": "5  Reading the report",
        "s5_p": "When a backlog is given, the report shows three related views - all from "
                "the same simulation runs.",
        "s5a_t": "5.1  Scope-confidence gauge",
        "s5a_p": "The gauge shows the probability of finishing the backlog by the horizon "
                 "date. The red line marks the 85 % threshold; the colour zones "
                 "(red/amber/green) help you judge it at a glance.",
        "s5a_cap": "Fig. 2: Scope confidence - how likely are we to finish the scope by the date?",
        "s5b_t": "5.2  Exceedance curve (how many)",
        "s5b_p": "For each item count the curve shows the probability of completing "
                 "<b>at least</b> that many. The dashed 85/75/50 % lines are reading aids: "
                 "higher confidence = smaller guaranteed amount. The vertical line marks "
                 "your backlog.",
        "s5b_cap": "Fig. 3: Exceedance curve - probability of completing at least X items.",
        "s5c_t": "5.3  Completion distribution (when done)",
        "s5c_p": "The bar chart shows on which day the backlog was finished across the "
                 "simulations. The confidence lines give the day and date per confidence "
                 "level. Confidence levels that are not reachable within the cap are "
                 "reported as 'not within cap' - never as an over-optimistic date.",
        "s5c_cap": "Fig. 4: Completion distribution - days to finish with confidence lines.",
        "s6_t": "6  Tips",
        "s6_b1": "<b>Set a seed</b> if you want to reproduce exactly the same report.",
        "s6_b2": "<b>Zero days are intentional:</b> a recently quiet period correctly "
                 "lowers the forecast - don't shorten the window to hide it.",
        "s6_b3": "<b>Don't over-interpret:</b> a 60 % confidence is not a failure, it is "
                 "an honest statement about uncertainty.",
        "s6_b4": "<b>Choose scope growth</b> realistically: with epics one item often "
                 "spawns more - that pushes the finish date out.",
    },
    LANG_RO: {
        "cover_sub": "Manual de Utilizator",
        "cover_tag": "Prognoza Monte-Carlo pentru echipe agile",
        "cover_aud": "Pentru utilizatori non-tehnici",
        "header": "Manual de Utilizator", "page": "Pagina %d", "toc": "Cuprins",
        "s1_t": "1  Ce este simulate?",
        "s1_p": "simulate transforma datele istorice de livrare ale echipei intr-o "
                "prognoza probabilistica (simulare Monte-Carlo). Se bazeaza doar pe "
                "<b>throughput</b> - cate elemente sunt finalizate pe zi. Nu sunt "
                "necesare estimari (story points). Raspunde la trei intrebari:",
        "s1_b1": "<b>Cate</b> elemente vom finaliza intr-o perioada data?",
        "s1_b2": "<b>Cand</b> va fi gata un backlog de N elemente?",
        "s1_b3": "<b>Vom termina scope-ul</b> pana la o data limita?",
        "s1_box": "Rezultatele sunt intotdeauna <b>probabilitati</b>, nu valori unice. "
                  "'Cel putin 20 de elemente cu 85 % incredere' inseamna: in 85 din 100 "
                  "de scenarii simulate au fost finalizate 20 sau mai multe elemente.",
        "s2_t": "2  Pornirea programului",
        "s2_gui": "<b>Din launcher:</b> apasati cardul <b>Simulate</b> in fereastra de "
                  "start SituationReport.",
        "s2_cli": "<b>Direct:</b> fara argumente se deschide interfata grafica, cu "
                  "argumente ruleaza linia de comanda:",
        "s2_code": "python -m simulate ART_A_IssueTimes.xlsx --horizon 84 "
                   "--backlog 20 --output forecast.html",
        "s3_t": "3  Fisierul de intrare",
        "s3_p": "simulate are nevoie de un <b>IssueTimes.xlsx</b> produs de modulul "
                "<b>transform_data</b>. Pentru prognoza conteaza doar Closed Date al "
                "elementelor. Optional se poate furniza si un CFD.xlsx.",
        "s4_t": "4  Interfata (GUI)",
        "s4_p": "Alegeti sus fisierul IssueTimes si setati parametrii mai jos. Un clic pe "
                "<b>Genereaza raport</b> cere o locatie si deschide raportul in browser.",
        "s4_cap": "Fig. 1: Interfata simulate cu campurile de fisier si parametri.",
        "s4_th": ["Camp", "Semnificatie"],
        "s4_rows": [
            ["Fereastra istoric (zile)", "Cat de mult in urma se considera datele "
             "istorice (implicit 180). Include intentionat zilele cu throughput zero."],
            ["Sfarsit istoric", "Sfarsitul ferestrei (gol = azi)."],
            ["Orizont (zile)", "Cat de departe in viitor pentru 'cate' (implicit 84)."],
            ["Backlog", "Numar de elemente pentru prognoza de data si de incredere "
             "(gol = doar 'cate')."],
            ["Rulari", "Numarul de simulari (implicit 25000). Mai multe = mai neted."],
            ["Crestere scope", "Elemente noi asteptate per element finalizat (ex. 0.1 = "
             "+10 % rework/split-uri)."],
            ["Seed", "Valoare fixa de pornire pentru rezultate reproductibile (gol = aleator)."],
        ],
        "s5_t": "5  Citirea raportului",
        "s5_p": "Cand este dat un backlog, raportul arata trei vederi corelate - toate "
                "din aceleasi rulari de simulare.",
        "s5a_t": "5.1  Indicator de incredere pentru scope",
        "s5a_p": "Indicatorul arata probabilitatea de a finaliza backlog-ul pana la data "
                 "orizontului. Linia rosie marcheaza pragul de 85 %; zonele de culoare "
                 "(rosu/galben/verde) ajuta la o evaluare rapida.",
        "s5a_cap": "Fig. 2: Increderea in scope - cat de probabil terminam pana la data?",
        "s5b_t": "5.2  Curba de depasire (cate)",
        "s5b_p": "Pentru fiecare numar de elemente, curba arata probabilitatea de a "
                 "finaliza <b>cel putin</b> atatea. Liniile punctate 85/75/50 % sunt "
                 "ajutoare de citire: incredere mai mare = cantitate garantata mai mica. "
                 "Linia verticala marcheaza backlog-ul.",
        "s5b_cap": "Fig. 3: Curba de depasire - probabilitatea de a finaliza cel putin X elemente.",
        "s5c_t": "5.3  Distributia de finalizare (cand)",
        "s5c_p": "Graficul cu bare arata in ce zi a fost finalizat backlog-ul in "
                 "simulari. Liniile de incredere dau ziua si data pentru fiecare nivel. "
                 "Nivelurile care nu sunt atinse in intervalul stabilit sunt raportate ca "
                 "'in afara intervalului' - niciodata ca o data prea optimista.",
        "s5c_cap": "Fig. 4: Distributia de finalizare - zile pana la finalizare cu linii de incredere.",
        "s6_t": "6  Sfaturi",
        "s6_b1": "<b>Setati un seed</b> daca vreti sa reproduceti exact acelasi raport.",
        "s6_b2": "<b>Zilele zero sunt intentionate:</b> o perioada recent linistita "
                 "scade corect prognoza - nu scurtati fereastra pentru a o ascunde.",
        "s6_b3": "<b>Nu supra-interpretati:</b> o incredere de 60 % nu este un esec, ci o "
                 "afirmatie onesta despre incertitudine.",
        "s6_b4": "<b>Alegeti cresterea de scope</b> realist: la epice un element naste "
                 "adesea altele - asta impinge data de finalizare mai departe.",
    },
    LANG_PT: {
        "cover_sub": "Manual do Utilizador",
        "cover_tag": "Previsao Monte-Carlo para equipas ageis",
        "cover_aud": "Para utilizadores nao tecnicos",
        "header": "Manual do Utilizador", "page": "Pagina %d", "toc": "Indice",
        "s1_t": "1  O que e o simulate?",
        "s1_p": "O simulate transforma os dados historicos de entrega da equipa numa "
                "previsao probabilistica (simulacao Monte-Carlo). Baseia-se apenas no "
                "<b>throughput</b> - quantos itens sao concluidos por dia. Nao sao "
                "necessarias estimativas (story points). Responde a tres perguntas:",
        "s1_b1": "<b>Quantos</b> itens vamos concluir num periodo?",
        "s1_b2": "<b>Quando</b> estara pronto um backlog de N itens?",
        "s1_b3": "<b>Vamos terminar o scope</b> ate uma data limite?",
        "s1_box": "Os resultados sao sempre <b>probabilidades</b>, nao valores unicos. "
                  "'Pelo menos 20 itens com 85 % de confianca' significa: em 85 de 100 "
                  "futuros simulados foram concluidos 20 ou mais itens.",
        "s2_t": "2  Iniciar o programa",
        "s2_gui": "<b>A partir do launcher:</b> clique no cartao <b>Simulate</b> na "
                  "janela inicial do SituationReport.",
        "s2_cli": "<b>Diretamente:</b> sem argumentos abre a interface grafica, com "
                  "argumentos executa a linha de comandos:",
        "s2_code": "python -m simulate ART_A_IssueTimes.xlsx --horizon 84 "
                   "--backlog 20 --output forecast.html",
        "s3_t": "3  Ficheiro de entrada",
        "s3_p": "O simulate precisa de um <b>IssueTimes.xlsx</b> produzido pelo modulo "
                "<b>transform_data</b>. Para a previsao apenas importa a Closed Date dos "
                "itens. Opcionalmente pode indicar tambem um CFD.xlsx.",
        "s4_t": "4  A interface (GUI)",
        "s4_p": "Escolha em cima o ficheiro IssueTimes e defina os parametros abaixo. Um "
                "clique em <b>Gerar relatorio</b> pede um local e abre o relatorio no browser.",
        "s4_cap": "Fig. 1: A interface simulate com os campos de ficheiro e parametros.",
        "s4_th": ["Campo", "Significado"],
        "s4_rows": [
            ["Janela de historico (dias)", "Ate onde para tras os dados historicos sao "
             "considerados (por omissao 180). Inclui deliberadamente os dias com zero."],
            ["Fim do historico", "Fim da janela (vazio = hoje)."],
            ["Horizonte (dias)", "Ate onde no futuro para 'quantos' (por omissao 84)."],
            ["Backlog", "Numero de itens para a previsao de data e de confianca "
             "(vazio = apenas 'quantos')."],
            ["Execucoes", "Numero de simulacoes (por omissao 25000). Mais = mais suave."],
            ["Crescimento de scope", "Novos itens esperados por item concluido (ex. 0.1 = "
             "+10 % de retrabalho/splits)."],
            ["Seed", "Valor inicial fixo para resultados reproduziveis (vazio = aleatorio)."],
        ],
        "s5_t": "5  Ler o relatorio",
        "s5_p": "Quando e dado um backlog, o relatorio mostra tres vistas relacionadas - "
                "todas das mesmas execucoes de simulacao.",
        "s5a_t": "5.1  Indicador de confianca do scope",
        "s5a_p": "O indicador mostra a probabilidade de terminar o backlog ate a data do "
                 "horizonte. A linha vermelha marca o limiar de 85 %; as zonas de cor "
                 "(vermelho/amarelo/verde) ajudam a avaliar rapidamente.",
        "s5a_cap": "Fig. 2: Confianca do scope - qual a probabilidade de terminar ate a data?",
        "s5b_t": "5.2  Curva de excedencia (quantos)",
        "s5b_p": "Para cada quantidade de itens, a curva mostra a probabilidade de "
                 "concluir <b>pelo menos</b> essa quantidade. As linhas tracejadas "
                 "85/75/50 % sao auxiliares de leitura: maior confianca = quantidade "
                 "garantida menor. A linha vertical marca o backlog.",
        "s5b_cap": "Fig. 3: Curva de excedencia - probabilidade de concluir pelo menos X itens.",
        "s5c_t": "5.3  Distribuicao de conclusao (quando)",
        "s5c_p": "O grafico de barras mostra em que dia o backlog ficou pronto nas "
                 "simulacoes. As linhas de confianca dao o dia e a data por nivel. Niveis "
                 "que nao sao atingiveis dentro do limite sao reportados como 'fora do "
                 "limite' - nunca como uma data demasiado otimista.",
        "s5c_cap": "Fig. 4: Distribuicao de conclusao - dias ate terminar com linhas de confianca.",
        "s6_t": "6  Dicas",
        "s6_b1": "<b>Defina um seed</b> se quiser reproduzir exatamente o mesmo relatorio.",
        "s6_b2": "<b>Os dias zero sao intencionais:</b> um periodo recentemente calmo "
                 "baixa corretamente a previsao - nao encurte a janela para o esconder.",
        "s6_b3": "<b>Nao sobre-interprete:</b> uma confianca de 60 % nao e um fracasso, e "
                 "uma afirmacao honesta sobre a incerteza.",
        "s6_b4": "<b>Escolha o crescimento de scope</b> de forma realista: com epicos um "
                 "item gera muitas vezes outros - isso empurra a data para a frente.",
    },
    LANG_FR: {
        "cover_sub": "Manuel d'utilisation",
        "cover_tag": "Prevision Monte-Carlo pour equipes agiles",
        "cover_aud": "Pour les utilisateurs non techniques",
        "header": "Manuel d'utilisation", "page": "Page %d", "toc": "Sommaire",
        "s1_t": "1  Qu'est-ce que simulate ?",
        "s1_p": "simulate transforme les donnees historiques de livraison de votre equipe "
                "en une prevision probabiliste (simulation Monte-Carlo). Elle repose "
                "uniquement sur le <b>debit</b> (throughput) - combien d'elements sont "
                "termines par jour. Aucune estimation (story points) n'est necessaire. "
                "Elle repond a trois questions :",
        "s1_b1": "<b>Combien</b> d'elements terminerons-nous sur une periode ?",
        "s1_b2": "<b>Quand</b> un backlog de N elements sera-t-il <b>termine</b> ?",
        "s1_b3": "<b>Terminerons-nous le perimetre</b> avant une date cible ?",
        "s1_box": "Les resultats sont toujours des <b>probabilites</b>, pas des valeurs "
                  "uniques. 'Au moins 20 elements avec 85 % de confiance' signifie : dans "
                  "85 des 100 futurs simules, 20 elements ou plus ont ete termines.",
        "s2_t": "2  Demarrer le programme",
        "s2_gui": "<b>Depuis le launcher :</b> cliquez sur la carte <b>Simulate</b> dans "
                  "la fenetre de demarrage de SituationReport.",
        "s2_cli": "<b>Directement :</b> sans arguments l'interface graphique s'ouvre, avec "
                  "arguments la ligne de commande s'execute :",
        "s2_code": "python -m simulate ART_A_IssueTimes.xlsx --horizon 84 "
                   "--backlog 20 --output forecast.html",
        "s3_t": "3  Fichier d'entree",
        "s3_p": "simulate a besoin d'un <b>IssueTimes.xlsx</b> tel que produit par le "
                "module <b>transform_data</b>. Pour la prevision, seule la Closed Date "
                "des elements compte. Un CFD.xlsx peut aussi etre fourni en option.",
        "s4_t": "4  L'interface (GUI)",
        "s4_p": "Choisissez en haut le fichier IssueTimes et reglez les parametres en "
                "dessous. Un clic sur <b>Generer le rapport</b> demande un emplacement et "
                "ouvre le rapport dans le navigateur.",
        "s4_cap": "Fig. 1 : L'interface simulate avec les champs de fichier et de parametres.",
        "s4_th": ["Champ", "Signification"],
        "s4_rows": [
            ["Fenetre d'historique (jours)", "Jusqu'ou en arriere les donnees historiques "
             "sont prises en compte (par defaut 180). Inclut volontairement les jours a zero."],
            ["Fin d'historique", "Fin de la fenetre (vide = aujourd'hui)."],
            ["Horizon (jours)", "Jusqu'ou dans le futur pour 'combien' (par defaut 84)."],
            ["Backlog", "Nombre d'elements pour la prevision de date et de confiance "
             "(vide = 'combien' seulement)."],
            ["Executions", "Nombre de simulations (par defaut 25000). Plus = plus lisse."],
            ["Croissance du perimetre", "Nouveaux elements attendus par element termine "
             "(ex. 0.1 = +10 % de reprise/decoupages)."],
            ["Seed", "Valeur initiale fixe pour des resultats reproductibles (vide = aleatoire)."],
        ],
        "s5_t": "5  Lire le rapport",
        "s5_p": "Lorsqu'un backlog est fourni, le rapport montre trois vues liees - toutes "
                "issues des memes executions de simulation.",
        "s5a_t": "5.1  Jauge de confiance du perimetre",
        "s5a_p": "La jauge montre la probabilite de terminer le backlog avant la date "
                 "d'horizon. La ligne rouge marque le seuil de 85 % ; les zones de couleur "
                 "(rouge/orange/vert) aident a juger d'un coup d'oeil.",
        "s5a_cap": "Fig. 2 : Confiance du perimetre - quelle probabilite de terminer avant la date ?",
        "s5b_t": "5.2  Courbe de depassement (combien)",
        "s5b_p": "Pour chaque quantite d'elements, la courbe montre la probabilite d'en "
                 "terminer <b>au moins</b> autant. Les lignes pointillees 85/75/50 % sont "
                 "des aides de lecture : plus de confiance = quantite garantie plus "
                 "petite. La ligne verticale marque votre backlog.",
        "s5b_cap": "Fig. 3 : Courbe de depassement - probabilite de terminer au moins X elements.",
        "s5c_t": "5.3  Distribution d'achevement (quand)",
        "s5c_p": "Le diagramme en barres montre le jour ou le backlog a ete termine dans "
                 "les simulations. Les lignes de confiance donnent le jour et la date par "
                 "niveau. Les niveaux non atteignables dans la limite sont indiques comme "
                 "'hors limite' - jamais comme une date trop optimiste.",
        "s5c_cap": "Fig. 4 : Distribution d'achevement - jours jusqu'a la fin avec lignes de confiance.",
        "s6_t": "6  Conseils",
        "s6_b1": "<b>Definissez un seed</b> pour reproduire exactement le meme rapport.",
        "s6_b2": "<b>Les jours a zero sont voulus :</b> une periode recemment calme abaisse "
                 "correctement la prevision - ne raccourcissez pas la fenetre pour la cacher.",
        "s6_b3": "<b>Ne sur-interpretez pas :</b> une confiance de 60 % n'est pas un echec, "
                 "c'est une declaration honnete sur l'incertitude.",
        "s6_b4": "<b>Choisissez la croissance du perimetre</b> de maniere realiste : avec "
                 "les epics, un element en engendre souvent d'autres - cela repousse la date.",
    },
}


# ---------------------------------------------------------------------------
# Story renderer (one function, all languages)
# ---------------------------------------------------------------------------

def build_story(lang, st, images):
    """Build the document story and TOC for one language."""
    t = T[lang]
    story = []

    def add_img(key, cap):
        if images and key in images:
            story.append(SP(6))
            story.append(_img(images[key]))
            story.append(CAP(cap, st))

    # TOC
    story.append(PageBreak())
    story.append(H1(t["toc"], st))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("T1", fontName=_FB, fontSize=11, leading=18, spaceAfter=2),
        ParagraphStyle("T2", fontName=_FN, fontSize=9, leading=15, leftIndent=16),
    ]
    story.append(toc)

    # 1 Intro
    story.append(PageBreak())
    story.append(H1(t["s1_t"], st))
    story.append(P(t["s1_p"], st))
    story.append(BL(t["s1_b1"], st))
    story.append(BL(t["s1_b2"], st))
    story.append(BL(t["s1_b3"], st))
    story.append(SP(6))
    story.append(box(t["s1_box"], st))

    # 2 Start
    story.append(H1(t["s2_t"], st))
    story.append(BL(t["s2_gui"], st))
    story.append(P(t["s2_cli"], st))
    story.append(CD(t["s2_code"], st))

    # 3 Input
    story.append(H1(t["s3_t"], st))
    story.append(P(t["s3_p"], st))

    # 4 GUI + params
    story.append(PageBreak())
    story.append(H1(t["s4_t"], st))
    story.append(P(t["s4_p"], st))
    if _GUI_SHOT.is_file():
        story.append(SP(6))
        story.append(_img(_GUI_SHOT, 11))
        story.append(CAP(t["s4_cap"], st))
    story.append(SP(6))
    story.append(tbl(t["s4_th"], t["s4_rows"], [4.2*cm, 11.8*cm]))

    # 5 Reading the report
    story.append(PageBreak())
    story.append(H1(t["s5_t"], st))
    story.append(P(t["s5_p"], st))
    story.append(H2(t["s5a_t"], st))
    story.append(P(t["s5a_p"], st))
    add_img("gauge", t["s5a_cap"])
    story.append(H2(t["s5b_t"], st))
    story.append(P(t["s5b_p"], st))
    add_img("exceedance", t["s5b_cap"])
    story.append(H2(t["s5c_t"], st))
    story.append(P(t["s5c_p"], st))
    add_img("whendone", t["s5c_cap"])

    # 6 Tips
    story.append(H1(t["s6_t"], st))
    story.append(BL(t["s6_b1"], st))
    story.append(BL(t["s6_b2"], st))
    story.append(BL(t["s6_b3"], st))
    story.append(BL(t["s6_b4"], st))

    return story, toc


def _build_pdf(lang, out_path, st, images):
    doc = ManualDoc(str(out_path), lang=lang)
    story, _toc = build_story(lang, st, images)
    doc.multiBuild(story)


def main():
    """Generate the simulate manual PDFs for all five languages."""
    st = make_styles()
    out_dir = Path(__file__).parent
    with tempfile.TemporaryDirectory() as tmp:
        try:
            images = _generate_chart_images(Path(tmp))
        except Exception as exc:  # noqa: BLE001 — Charts optional; Manual trotzdem bauen
            print(f"WARNING: chart generation failed ({exc}); building without charts.")
            images = {}
        for lang in LANGS:
            out_path = out_dir / _OUTNAME[lang]
            _build_pdf(lang, out_path, st, images)
            print(f"  wrote {out_path.name}")


if __name__ == "__main__":
    main()
