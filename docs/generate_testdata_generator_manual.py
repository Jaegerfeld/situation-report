# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       31.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Benutzerhandbuch für testdata_generator als PDF in fünf
#   Sprachen: DE, EN, RO, PT, FR. Ein Aufbau, fünf Textkataloge (_M):
#   Datenraum in drei Schritten (Fenster/Browser), Ordnerinhalt, Geschichte,
#   Kommandozeile, Fortschreibung, klassischer Einzel-ART-Generator.
# =============================================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from _font_config import setup as _setup_fonts

_FN, _FB, _FI, _FBI = _setup_fonts()  # normal, bold, italic, bold_italic
from reportlab.pdfbase.pdfmetrics import registerFontFamily

registerFontFamily(_FN, normal=_FN, bold=_FB, italic=_FI, boldItalic=_FBI)
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
    "de": "Demo-Datenräume und synthetische Jira-Daten für SituationReport",
    "en": "Demo data rooms and synthetic Jira data for SituationReport",
    "ro": "Spații de date demo și date Jira sintetice pentru SituationReport",
    "pt": "Salas de dados demo e dados Jira sintéticos para SituationReport",
    "fr": "Espaces de données démo et données Jira synthétiques pour SituationReport",
}

_COVER_AUDIENCE = {
    "de": "Für Agile Coaches, PI Manager und Beta-Tester",
    "en": "For Agile Coaches, PI Managers and beta testers",
    "ro": "Pentru Agile Coaches, manageri PI și testeri beta",
    "pt": "Para Agile Coaches, gestores de PI e testadores beta",
    "fr": "Pour les Agile Coaches, PI Managers et testeurs bêta",
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
# Content — one structure, five languages
# ---------------------------------------------------------------------------
# Every chapter is built once in build_content(); the words come from _M[lang].
# All five catalogues carry the same keys (checked by tests/docs/test_manual_catalogue.py).

_CODE = "<font name='Courier'>%s</font>"


def _c(text: str) -> str:
    """Inline code in a paragraph."""
    return _CODE % text


def build_content(st: dict, lang: str) -> list:
    T = _M[lang]
    story: list = []

    # 1 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c1.h"], st), HR(),
              P(T["c1.p1"], st), P(T["c1.p2"], st), SP(4),
              box(T["c1.ways"], st), SP(8),
              P(T["c1.p3"], st), SP(4),
              box(T["c1.uses"], st, bg="#f4f4f4"), SP(6),
              HI(T["c1.beta"], st)]

    # 2 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c2.h"], st), HR(),
              H2(T["c2.pkg.h"], st), P(T["c2.pkg.p"], st),
              tbl([T["c2.pkg.col_file"], T["c2.pkg.col_what"]],
                  [[_c("DatenraumFenster.bat"), T["c2.pkg.window"]],
                   [_c("SituationReport.bat"), T["c2.pkg.launcher"]],
                   [_c("DatenraumBrowser.bat"), T["c2.pkg.browser"]],
                   [_c("TestdataGenerator.bat"), T["c2.pkg.single"]]],
                  col_widths=[4.6 * cm, 10.9 * cm]),
              SP(4), HI(T["c2.pkg.unix"], st), SP(4), HI(T["c2.pkg.defender"], st), SP(6),
              H2(T["c2.src.h"], st), P(T["c2.src.p"], st),
              PRE("python -m testdata_generator --dataspace\n"
                  "python -m testdata_generator --web\n"
                  "python -m testdata_generator", st),
              SP(6),
              H2(T["c2.wvb.h"], st), P(T["c2.wvb.p"], st), SP(6),
              H2(T["c2.lang.h"], st), P(T["c2.lang.p"], st)]

    # 3 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c3.h"], st), HR(), P(T["c3.p"], st)]
    story += img("Datenraum-Fenster.png", 15.5, T["c3.fig"], st)

    story += [H2(T["c3.s1.h"], st), P(T["c3.s1.p"], st),
              tbl([T["c3.s1.col_tpl"], T["c3.s1.col_tells"], T["c3.s1.col_stands"]],
                  [[T["tpl.calm"], T["tpl.calm.desc"], "3"],
                   [T["tpl.standard"] + " " + T["c3.s1.rec"], T["tpl.standard.desc"], "6"],
                   [T["tpl.escalation"], T["tpl.escalation.desc"], "6"],
                   [T["tpl.recovery"], T["tpl.recovery.desc"], "6"]],
                  col_widths=[3.2 * cm, 10.3 * cm, 2.0 * cm]),
              SP(6), P(T["c3.s1.events"], st), P(T["c3.s1.structure"], st),
              P(T["c3.s1.yields"], st)]

    story += [H2(T["c3.s2.h"], st), P(T["c3.s2.p"], st),
              tbl([T["c3.s2.col_setting"], T["c3.s2.col_default"], T["c3.s2.col_meaning"]],
                  [[T["ui.stands"], "6", T["c3.s2.stands"]],
                   [T["ui.scale"], "M", T["c3.s2.scale"]],
                   [T["ui.realism"], "60", T["c3.s2.realism"]],
                   [T["ui.seed"], "42", T["c3.s2.seed"]],
                   [T["ui.reference"], T["c3.s2.today"], T["c3.s2.reference"]],
                   [T["ui.lang"], T["c3.s2.ui_lang"], T["c3.s2.lang"]]],
                  col_widths=[3.4 * cm, 2.6 * cm, 9.5 * cm]),
              SP(6), P(T["c3.s2.details"], st), P(T["c3.s2.sources"], st),
              P(T["c3.s2.ai"], st), P(T["c3.s2.estimate"], st)]

    story += [H2(T["c3.s3.h"], st), P(T["c3.s3.target"], st), P(T["c3.s3.progress"], st),
              tbl([T["c3.s3.col_step"], T["c3.s3.col_makes"]],
                  [[T["step.story"], T["c3.s3.st.story"]],
                   [T["step.arts"], T["c3.s3.st.arts"]],
                   [T["step.registers"], T["c3.s3.st.registers"]],
                   [T["step.configs"], T["c3.s3.st.configs"]],
                   [T["step.sources"], T["c3.s3.st.sources"]],
                   [T["step.readme"], T["c3.s3.st.readme"]],
                   [T["step.stands"], T["c3.s3.st.stands"]],
                   [T["step.deltas"], T["c3.s3.st.deltas"]],
                   [T["step.ai_drafts"], T["c3.s3.st.ai_drafts"]]],
                  col_widths=[5.0 * cm, 10.5 * cm]),
              SP(6), P(T["c3.s3.cancel"], st), P(T["c3.s3.result"], st),
              P(T["c3.s3.compare"], st), P(T["c3.s3.after"], st)]

    # 4 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c4.h"], st), HR(), P(T["c4.p"], st),
              tbl([T["c4.col_path"], T["c4.col_content"]],
                  [[_c("structure.json"), T["c4.structure"]],
                   [_c("story.json"), T["c4.story"]],
                   [_c("README.md"), T["c4.readme"]],
                   [_c("portfolio.json"), T["c4.portfolio"]],
                   [_c("pi_config.json"), T["c4.pi"]],
                   [_c("solutions/&lt;name&gt;/"), T["c4.solutions"]],
                   [_c("raw/"), T["c4.raw"]],
                   [_c("sources/&lt;name&gt;/"), T["c4.sources"]],
                   [_c("snapshots/"), T["c4.snapshots"]],
                   [_c("deltas/"), T["c4.deltas"]],
                   [_c("ai_drafts/"), T["c4.ai_drafts"]]],
                  col_widths=[4.4 * cm, 11.1 * cm]),
              SP(8), P(T["c4.use"], st),
              PRE("python -m portfolio portfolio.json\n"
                  "python -m portfolio --delta snapshots/snapshot_prev.json snapshots/snapshot_now.json\n"
                  "python -m portfolio portfolio.json --conference mappe.html\n"
                  "python -m sources fetch\n"
                  "python -m get_data check raw/<art>_jira.json", st),
              SP(4), P(T["c4.multi"], st)]

    # 5 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c5.h"], st), HR(), P(T["c5.p"], st),
              box(T["c5.roles"], st), SP(8), P(T["c5.notices"], st), SP(4),
              tbl([T["c5.col_id"], T["c5.col_what"], T["c5.col_visible"]],
                  [[f"E{i}", T[f"ev.E{i}.title"], T[f"ev.E{i}.effect"]] for i in range(1, 11)],
                  col_widths=[1.2 * cm, 6.4 * cm, 7.9 * cm]),
              SP(8), P(T["c5.windows"], st)]

    # 6 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c6.h"], st), HR(), P(T["c6.p"], st),
              tbl([T["c6.col_opt"], T["c6.col_default"], T["c6.col_meaning"]],
                  [["--scenario portfolio", "—", T["c6.scenario"]],
                   ["--output " + T["c6.folder_word"], T["c6.required"], T["c6.output"]],
                   ["--structure small|standard|<br/>large|FILE.json", "standard", T["c6.structure"]],
                   ["--arts N[,N...]", "—", T["c6.arts"]],
                   ["--story calm|standard|<br/>escalation|recovery", "standard", T["c6.story"]],
                   ["--event ID=on|off", "—", T["c6.event"]],
                   ["--stands N", T["c6.stands_default"], T["c6.stands"]],
                   ["--scale s|m|l", "m", T["c6.scale"]],
                   ["--seed N", T["c6.seed_default"], T["c6.seed"]],
                   ["--art-profiles FILE.json", "—", T["c6.art_profiles"]],
                   ["--ai-drafts", T["c6.off"], T["c6.ai_drafts"]],
                   ["--lang de|en|ro|pt|fr", T["c6.lang_default"], T["c6.lang"]],
                   ["--continue " + T["c6.folder_word"] + " --to-date DATE", "—", T["c6.continue"]],
                   ["--web / --port N /<br/>--no-browser", "—", T["c6.web"]],
                   ["--dataspace", "—", T["c6.dataspace"]]],
                  col_widths=[4.9 * cm, 2.7 * cm, 7.9 * cm]),
              SP(8), H2(T["c6.ex.h"], st),
              PRE("# " + T["c6.ex.1"] + "\n"
                  "python -m testdata_generator --scenario portfolio --output demo/ --seed 42\n\n"
                  "# " + T["c6.ex.2"] + "\n"
                  "python -m testdata_generator --scenario portfolio --output demo-esc/ \\\n"
                  "    --story escalation --stands 8 --scale l --lang de\n\n"
                  "# " + T["c6.ex.3"] + "\n"
                  "python -m testdata_generator --scenario portfolio --output demo-3/ \\\n"
                  "    --arts 3,4s,1 --event E3=off --ai-drafts\n\n"
                  "# " + T["c6.ex.4"] + "\n"
                  "python -m testdata_generator --scenario portfolio --structure large \\\n"
                  "    --output demo-large/", st),
              SP(4), HI(T["c6.hint_default_lang"], st)]

    # 7 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c7.h"], st), HR(), P(T["c7.p1"], st),
              PRE("python -m testdata_generator --scenario portfolio \\\n"
                  "    --continue demo/ --to-date 2027-01-15", st),
              P(T["c7.p2"], st), HI(T["c7.hint"], st)]

    # 8 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c8.h"], st), HR(), P(T["c8.p"], st),
              H2(T["c8.win.h"], st), P(T["c8.win.p"], st)]
    story += img("Testdata-Generator-GUI.png", 13.0, T["c8.win.fig"], st)
    story += [H2(T["c8.wf.h"], st), P(T["c8.wf.p"], st),
              PRE(T["c8.wf.pre"], st),
              tbl([T["c8.wf.col_line"], T["c8.wf.col_meaning"]],
                  [["Name:Alias1:Alias2", T["c8.wf.alias"]],
                   [T["c8.wf.plain_name"], T["c8.wf.plain"]],
                   ["&lt;First&gt;Name", T["c8.wf.first"]],
                   ["&lt;Closed&gt;Name", T["c8.wf.closed"]]],
                  col_widths=[5 * cm, 10.5 * cm]),
              SP(6), P(T["c8.wf.example"], st),
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
              SP(4), HI(T["c8.wf.notes"], st)]

    story += [PageBreak(), H2(T["c8.par.h"], st), P(T["c8.par.p"], st),
              tbl([T["c8.par.col_param"], T["c8.par.col_default"], T["c8.par.col_desc"]],
                  [["--workflow FILE", T["c6.required"], T["c8.par.workflow"]],
                   ["--output FILE.json", "<project>_generated.json", T["c8.par.output"]],
                   ["--project KEY", "TEST", T["c8.par.project"]],
                   ["--issues N", "100", T["c8.par.issues"]],
                   ["--from-date YYYY-MM-DD", "2025-01-01", T["c8.par.from"]],
                   ["--to-date YYYY-MM-DD", "2025-12-31", T["c8.par.to"]],
                   ["--issue-types TYPE:W ...", "Feature:0.6 Bug:0.3 Enabler:0.1", T["c8.par.types"]],
                   ["--completion-rate FLOAT", "0.7", T["c8.par.completion"]],
                   ["--todo-rate FLOAT", "0.15", T["c8.par.todo"]],
                   ["--backflow-prob FLOAT", "0.1", T["c8.par.backflow"]],
                   ["--realism 0-100", "0", T["c8.par.realism"]],
                   ["--seed INT", T["c6.seed_default"], T["c8.par.seed"]],
                   ["--mean-cycle-days FLOAT", "—", T["c8.par.mean"]],
                   ["--std-cycle-days FLOAT", T["c8.par.std_default"], T["c8.par.std"]],
                   ["--pattern NAME", "none", T["c8.par.pattern"]],
                   ["--pi-duration-weeks INT", "12", T["c8.par.pi"]],
                   ["--pattern-strength 0-100", "50", T["c8.par.strength"]],
                   ["--continue OLD.json", "—", T["c8.par.continue"]],
                   ["--learn-from FILE.xlsx", "—", T["c8.par.learn"]]],
                  col_widths=[4.5 * cm, 3.5 * cm, 7.5 * cm])]

    story += [SP(10), H2(T["c8.pat.h"], st), P(T["c8.pat.p"], st),
              tbl([T["c8.pat.col_pattern"], T["c8.pat.col_look"], T["c8.pat.col_desc"]],
                  [["none", T["c8.pat.none.look"], T["c8.pat.none.desc"]],
                   ["triangle", T["c8.pat.triangle.look"], T["c8.pat.triangle.desc"]],
                   ["flat_triangle", T["c8.pat.flat.look"], T["c8.pat.flat.desc"]],
                   ["cluster", T["c8.pat.cluster.look"], T["c8.pat.cluster.desc"]],
                   ["batch", T["c8.pat.batch.look"], T["c8.pat.batch.desc"]]],
                  col_widths=[3.0 * cm, 4.0 * cm, 8.5 * cm]),
              SP(6), HI(T["c8.pat.hint"], st)]

    story += [PageBreak(), H2(T["c8.ex.h"], st), P(T["c8.ex.p"], st),
              H3(T["c8.ex.s1"], st),
              PRE("python -m testdata_generator \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt \\\n"
                  "    --project ART_A --issues 200 \\\n"
                  "    --from-date 2025-01-01 --to-date 2025-12-31 \\\n"
                  "    --issue-types Feature:0.6 Bug:0.2 Enabler:0.2 \\\n"
                  "    --completion-rate 0.75 --backflow-prob 0.08 \\\n"
                  "    --seed 42 --output ART_A_generated.json", st),
              H3(T["c8.ex.s2"], st),
              PRE("python -m transform_data ART_A_generated.json \\\n"
                  "    --workflow testdata_generator/workflow_ART_A.txt", st),
              H3(T["c8.ex.s3"], st),
              PRE("python -m build_reports", st),
              SP(6), box(T["c8.ex.expect"], st)]

    # 9 ---------------------------------------------------------------------
    story += [PageBreak(), H1(T["c9.h"], st), HR()]
    for i in range(1, 7):
        story += [H2(T[f"c9.q{i}"], st), P(T[f"c9.a{i}"], st)]

    # 10 --------------------------------------------------------------------
    terms = ["art", "dataspace", "delta", "conference", "seam", "register", "stand",
             "seed", "solution", "stage_map", "value_stream", "workflow", "realism", "cfd"]
    story += [PageBreak(), H1(T["c10.h"], st), HR(),
              tbl([T["c10.col_term"], T["c10.col_expl"]],
                  [[T[f"g.{k}.t"], T[f"g.{k}.e"]] for k in terms],
                  col_widths=[3.8 * cm, 11.7 * cm])]
    return story


_M: dict[str, dict[str, str]] = {}

_M["de"] = {
    # 1 -------------------------------------------------------------------
    "c1.h": "1  Was ist der Testdaten-Generator?",
    "c1.p1": "Der <b>Testdaten-Generator</b> erzeugt erfundene, aber realistische Daten für "
             "SituationReport — damit du Portfolio-Report, Delta-Briefing, Konferenzmappe und "
             "die Register vorführen, lernen und testen kannst, ohne echte Projektdaten "
             "anzufassen. Es kommen keine Personen vor; gleicher Seed ergibt denselben Datenraum.",
    "c1.p2": "Der Generator hat zwei Wege. Der <b>Datenraum</b> ist der Standardweg der Beta: "
             "In drei Schritten entsteht ein kompletter Portfolio-Ordner mit Struktur, Geschichte, "
             "Jira-Exporten je ART, Registern, Provider-Rohdaten, einer Reihe von Ständen und den "
             "fertigen Delta-Briefings. Der <b>einzelne ART</b> ist der klassische Weg: eine "
             "Jira-Export-Datei aus einer Workflow-Datei, mit allen Reglern für Cycle Time und "
             "Flow-Muster (Kapitel 8).",
    "c1.ways": "<b>Welcher Weg wann?</b><br/>"
               "- <b>Datenraum (Fenster oder Browser):</b> Schulung, Präsentation, Tutorials, "
               "Tests der Portfolio-Kette — alles, was ein ganzes Lagebild braucht.<br/>"
               "- <b>Einzelner ART:</b> ein Jira-Export für transform_data und build_reports, "
               "gezielte Flow-Muster für Trainings zu Cycle-Time-Scatterplots, Fortschreibung "
               "eines früheren Abzugs.",
    "c1.p3": "Dieses Handbuch beschreibt zuerst den Datenraum (Kapitel 2 bis 7) und danach den "
             "klassischen Einzel-ART-Generator (Kapitel 8). Wer nur die eine Minute bis zum ersten "
             "Portfolio-Report sucht, nimmt das Tutorial „Demo-Datenraum in einer Minute“ "
             "(docs/tutorials/demo-data-room.de.md, auch als PDF).",
    "c1.uses": "<b>Typische Einsatzgebiete:</b><br/>"
               "- <b>Neue Installation testen:</b> Läuft die Kette von den Rohdaten bis zum "
               "Portfolio-Report?<br/>"
               "- <b>Demos und Präsentationen:</b> eine Lage mit Ausreißer, schwacher Quelle und "
               "Nähten, ohne Datenschutzfrage<br/>"
               "- <b>Schulungen:</b> dieselbe Geschichte bei allen Teilnehmenden, reproduzierbar über den Seed<br/>"
               "- <b>Entwicklung:</b> Stresstest mit großer Struktur (Umfang L, bis 49 ARTs)",
    "c1.beta": "Stand: Beta, Oktober 2026. Die Oberfläche des Datenraums ist neu; der Reiter für "
               "einzelne ART-Profile in der Oberfläche fehlt noch (Kommandozeile: --art-profiles).",

    # 2 -------------------------------------------------------------------
    "c2.h": "2  Start",
    "c2.pkg.h": "2.1  Portables Paket (empfohlen)",
    "c2.pkg.p": "Das portable Paket enthält Python bereits eingebettet — keine Installation. "
                "Nach dem Entpacken liegen vier Startdateien für den Generator bereit:",
    "c2.pkg.col_file": "Startdatei (Windows)",
    "c2.pkg.col_what": "Was sie öffnet",
    "c2.pkg.window": "<b>Datenraum als Fenster</b> — der Standardweg. Drei Schritte, kein "
                     "Netzwerkport, läuft auch auf Firmenrechnern.",
    "c2.pkg.launcher": "Der Launcher mit allen Modulen; darin die Karten „Datenraum (Fenster)“ und "
                       "„Datenraum (Browser)“ sowie „Testdata Generator“ für den einzelnen ART.",
    "c2.pkg.browser": "<b>Datenraum im Browser</b> — dieselben drei Schritte als Webseite. Startet "
                      "einen lokalen Server auf 127.0.0.1 mit Zufallsschlüssel im Link. "
                      "Nur auf privaten Rechnern: Sicherheitssoftware auf Firmenrechnern blockiert "
                      "und meldet lokale Server.",
    "c2.pkg.single": "<b>Einzelner ART</b> — das klassische Fenster mit Workflow-Datei, "
                     "Reglern und Flow-Mustern (Kapitel 8).",
    "c2.pkg.unix": "macOS: dieselben Namen als .command (Rechtsklick → Öffnen). Linux: als .sh "
                   "(python3 und python3-tk vorausgesetzt). Der erste Start richtet einmal eine "
                   "Python-Umgebung ein — dafür ist Internet nötig.",
    "c2.pkg.defender": "Hinweis für Windows: Meldet der Start, dass Python nicht gefunden wird, war "
                       "die ZIP-Datei durch Windows blockiert. Rechtsklick auf die ZIP → "
                       "Eigenschaften → Sicherheit → Zulassen → OK → erneut entpacken.",
    "c2.src.h": "2.2  Aus dem Quellcode (Python erforderlich)",
    "c2.src.p": "Die drei Oberflächen entsprechen drei Aufrufen: Fenster, Browser, einzelner ART.",
    "c2.wvb.h": "2.3  Fenster oder Browser?",
    "c2.wvb.p": "Beide zeigen dieselben drei Schritte mit denselben Einstellungen und erzeugen "
                "denselben Datenraum. Das Fenster ist ein normales Programmfenster (tkinter) und "
                "braucht nichts weiter. Die Browser-Seite ist etwas bequemer zu lesen, läuft aber "
                "über einen lokalen Server — auf einem Firmenrechner hat die Endgeräte-Sicherheit "
                "das im ersten Test blockiert und gemeldet. Deshalb gilt: Fenster zuerst, Browser "
                "nur privat.",
    "c2.lang.h": "2.4  Sprachen",
    "c2.lang.p": "Oberfläche, Geschichte, README, Fortschritt, Protokoll und die erzeugten "
                 "Delta-Briefings gibt es in Deutsch, Englisch, Rumänisch, Portugiesisch und "
                 "Französisch. Der Generator startet in der Sprache, die im Launcher eingestellt "
                 "ist; oben rechts in Fenster und Browser-Seite lässt sie sich umschalten — "
                 "Eingaben bleiben erhalten. Ein Lauf hat eine Sprache: Oberfläche und erzeugte "
                 "Texte sind gleich. Ohne Launcher-Einstellung und ohne " + _c("--lang") +
                 " ist die Sprache Englisch. Rumänisch, Portugiesisch und Französisch sind "
                 "Entwürfe, die noch von Muttersprachlern geprüft werden.",

    # 3 -------------------------------------------------------------------
    "c3.h": "3  Der Datenraum in drei Schritten",
    "c3.p": "Fenster und Browser-Seite führen durch drei Schritte: <b>Szenario</b> (welche Lage), "
            "<b>Umfang &amp; Quellen</b> (wie groß, wie lang, wie echt) und <b>Erzeugen</b> "
            "(wohin, und los). Die Standardwerte ergeben die Demo-Lage, die auch Tutorials und "
            "Handbücher der Portfolio-Module verwenden.",
    "c3.fig": "Abb. 1: Schritt 1 „Szenario“ im Datenraum-Fenster — Vorlagen links, Ereignisse "
              "darunter, Struktur rechts",
    "c3.s1.h": "3.1  Schritt 1 — Szenario",
    "c3.s1.p": "Links wählst du eine <b>Vorlage</b> der Geschichte. Die Ereignisse binden sich an "
               "Rollen der Struktur rechts — Ausreißer, schwache Quelle, Nähte — nicht an feste Namen.",
    "c3.s1.col_tpl": "Vorlage",
    "c3.s1.col_tells": "Was sie erzählt",
    "c3.s1.col_stands": "Stände",
    "tpl.calm": "Ruhig",
    "tpl.calm.desc": "Keine Wendungen, alle Teams im Rahmen. Für die erste Schulung und das Lesen "
                     "eines ruhigen Bilds. Wer hier Alarm schlägt, hat das Bild überlesen.",
    "tpl.standard": "Standard-Lage",
    "c3.s1.rec": "(empfohlen)",
    "tpl.standard.desc": "Ausreißer, schwache Quelle, SLO-Bruch und stille Muster von Anfang an; die "
                         "Wendungen kommen mit dem letzten Stand. Für Präsentation und Tutorials.",
    "tpl.escalation": "Eskalation",
    "tpl.escalation.desc": "Druck steigt Stand für Stand: SLO-Bruch früh, blockierte Naht in der "
                           "Mitte, Verfall und Cross-Solution-Nähte spät. Für die Konferenz-Übung.",
    "tpl.recovery": "Erholung",
    "tpl.recovery.desc": "Beginnt schlecht und heilt: Nähte gelöst, SLO hält, Ausreißer findet "
                         "seinen Takt. Für das Delta-Briefing: Was hat sich geändert?",
    "c3.s1.events": "<b>Ereignisse der Vorlage.</b> Die Tabelle darunter zeigt je Ereignis, wann es "
                    "gilt (alle Stände, ab Stand n, letzter Stand), was passiert und als was es im "
                    "Report sichtbar wird. Jedes Ereignis hat ein Häkchen; abgeschaltete Ereignisse "
                    "fehlen im Datenraum. Ein Ereignis, dessen Voraussetzung aus ist, bleibt mit "
                    "Hinweis aus. Das Fenster eines Ereignisses folgt der Zahl der Stände aus "
                    "Schritt 2. Kapitel 5 erklärt die zehn Ereignisse.",
    "c3.s1.structure": "<b>Struktur des Datenraums (rechts).</b> Eine Struktur-Vorlage — Klein "
                       "(1 Portfolio · 1 Solution · 2 ARTs), Standard (1 · 2 · je 3), Groß "
                       "(5 Portfolios · 3–4 Solutions · 1–6 ARTs) — oder eine eigene: Portfolios "
                       "und Solutions hinzufügen oder entfernen, ARTs je Solution zählen, Namen "
                       "ändern (ART-Namen folgen der Solution). Je Solution wählst du den "
                       "klassischen Workflow oder eine eigene Stage-Map. Mindestens ein ART je "
                       "Solution.",
    "c3.s1.yields": "<b>Was entsteht.</b> Die Box unten rechts rechnet mit: Jira-Exporte, "
                    "Arbeitsmappen, Register, Stände und Delta-Briefings für die gewählte Struktur "
                    "(Standard: 6 Exporte, 18 Arbeitsmappen, 22 Register, 6 Stände, 5 Deltas). "
                    "Ab 30 ARTs warnt sie: Die Erzeugung dauert dann spürbar.",
    "c3.s2.h": "3.2  Schritt 2 — Umfang &amp; Quellen",
    "c3.s2.p": "Die Standardwerte reichen für Schulung und Präsentation.",
    "c3.s2.col_setting": "Einstellung",
    "c3.s2.col_default": "Standard",
    "c3.s2.col_meaning": "Bedeutung",
    "ui.stands": "Stände",
    "ui.scale": "Umfang",
    "ui.realism": "Realismus",
    "ui.seed": "Seed",
    "ui.reference": "Letzter Stand",
    "ui.lang": "Sprache der Texte",
    "c3.s2.stands": "2 bis 12 Stände im Abstand von 14 Tagen; jeder Stand ist ein eingefrorener "
                    "Snapshot, jedes Folgepaar ein fertiges Delta-Briefing. Die Vorlage „Ruhig“ "
                    "schlägt 3 vor.",
    "c3.s2.scale": "S = nur Story-Anker, kurze Register; M = realistische Register; L = Stresstest "
                   "mit vollen Registern (dichte Heatmap, volle Roadmap-Matrix). Die Anker und ihre "
                   "Geschichten sind auf jeder Stufe identisch.",
    "c3.s2.realism": "Unordnung der Statuswege: Sprünge, Abbrüche, Parken, Schleifen, "
                     "Wiedereröffnung. 0 = glatt, 100 = wie echt; 60 ist ein typischer ART.",
    "c3.s2.seed": "Gleicher Seed, gleiche Struktur und gleiches Referenzdatum ergeben denselben "
                  "Datenraum — ideal, wenn alle Teilnehmenden dasselbe sehen sollen.",
    "c3.s2.today": "heute",
    "c3.s2.reference": "Datum des letzten Stands; die anderen liegen je 14 Tage davor. Die "
                       "Qualitäts-Ampel des Portfolio-Reports stuft die Daten so als aktuell ein.",
    "c3.s2.ui_lang": "Sprache der Oberfläche",
    "c3.s2.lang": "Sprache von Geschichte, README und Delta-Briefings; folgt der Oberfläche.",
    "c3.s2.details": "<b>Details für Analysten.</b> Zykluszeiten, Flow-Muster und PI-Länge lassen sich "
                     "je ART übersteuern — dieselben Regler wie beim einzelnen ART. In dieser Beta "
                     "geht das über die Kommandozeile mit " + _c("--art-profiles DATEI.json") +
                     " (Kapitel 6); die Tabelle in der Oberfläche folgt mit dem ART-Reiter.",
    "c3.s2.sources": "<b>Quellen, die mitgeliefert werden.</b> Immer dabei: Jira-Exporte je ART "
                     "(keine Personen), Prometheus-SLO-Antworten, GitHub-Deployments/PRs/Incidents "
                     "für die erste Solution, GitLab-DORA-Tageswerte für die zweite, "
                     "SonarQube-Qualitätsmaße und eine SLO-CSV für den manuellen Weg — Rohdaten im "
                     "Format des jeweiligen Systems mit denselben Zahlen wie in den Registern, so "
                     "dass " + _c("sources fetch") + " im Datenraum ohne Netz läuft.",
    "c3.s2.ai": "<b>KI-Entwürfe (Schalter, standardmäßig aus).</b> Ein Mock-Lagevortrag, drei "
                "Antworten, ein Prompt-Bündel und eine Übungsantwort mit falschen Zahlen landen im "
                "Ordner ai_drafts/ — alle mit KI-Marker, keine freigegeben. Damit übst du die "
                "Freigabe und " + _c("llm check") + ", ohne ein Modell zu installieren.",
    "c3.s2.estimate": "Die Zeile <b>Schätzung</b> am Ende nennt Jira-Exporte, Register, Stände und "
                      "Deltas für deine Einstellungen; die Fußzeile fasst Vorlage, Umfang, Stände, "
                      "Realismus und Seed zusammen.",
    "c3.s3.h": "3.3  Schritt 3 — Erzeugen",
    "c3.s3.target": "<b>Zielordner.</b> Er wird angelegt. Ist er nicht leer, fragt der Generator nach "
                    "— „Trotzdem erzeugen“ überschreibt Dateien gleichen Namens, „Anderen Ordner "
                    "wählen“ geht zurück. „Durchsuchen …“ öffnet den Ordnerdialog; wo keiner "
                    "verfügbar ist, trägst du den Pfad ein.",
    "c3.s3.progress": "<b>Fortschritt.</b> „Datenraum erzeugen“ startet neun Schritte; jeder zeigt "
                      "Laufen, Fertig oder Übersprungen mit einem Detail. Die Dauer liegt je nach "
                      "Umfang bei Sekunden bis Minuten (Standard-Lage rund 10 Sekunden).",
    "c3.s3.col_step": "Schritt",
    "c3.s3.col_makes": "Was entsteht",
    "step.story": "Struktur und Geschichte",
    "step.arts": "Jira-Exporte und Arbeitsmappen",
    "step.registers": "Register",
    "step.configs": "Konfigurationen",
    "step.sources": "Provider-Rohdaten",
    "step.readme": "README",
    "step.stands": "Stände-Reihe",
    "step.deltas": "Delta-Briefings",
    "step.ai_drafts": "KI-Entwürfe (Mock)",
    "c3.s3.st.story": "structure.json und story.json: Rollen gebunden, Ereignisse festgelegt",
    "c3.s3.st.arts": "je ART ein Jira-Export unter raw/ und IssueTimes/Transitions/CFD unter solutions/…/arts/",
    "c3.s3.st.registers": "je Solution die Register (Risiken, Abhängigkeiten, NFR, SLO, DORA, Capabilities, Themen …)",
    "c3.s3.st.configs": "portfolio.json, solution.json je Solution, pi_config.json",
    "c3.s3.st.sources": "sources/&lt;solution&gt;/ mit Replay-Dateien und sources-Configs",
    "c3.s3.st.readme": "README.md mit Struktur, Geschichte, Ständen und weiteren Wegen",
    "c3.s3.st.stands": "snapshots/snapshot_&lt;nn&gt;_&lt;datum&gt;.json je Stand, stands.json, prev/now",
    "c3.s3.st.deltas": "deltas/delta_&lt;nn&gt;-&lt;nn+1&gt;.md und .html je Folgepaar",
    "c3.s3.st.ai_drafts": "ai_drafts/ — nur mit Schalter, sonst „übersprungen“",
    "c3.s3.cancel": "<b>Abbrechen</b> hält nach dem laufenden Schritt an; der Ordner enthält, was "
                    "bis dahin entstand. Ein Fehler erscheint mit Meldung in der Liste.",
    "c3.s3.result": "<b>Ergebniskarte.</b> Nach dem letzten Schritt erscheint „Datenraum fertig“ mit "
                    "Dauer und Seed, vier Kennzahlen (Vorgänge und ARTs, Register und Solutions, "
                    "Stände, Quellen-Arten), der Geschichte in drei Sätzen und Knöpfen: "
                    "Portfolio-Report öffnen, Konferenzmappe, Jüngstes Delta, README, Ordner "
                    "öffnen, KI-Entwürfe (wenn erzeugt). Die Reports werden beim ersten Klick "
                    "gerendert und im Browser geöffnet.",
    "c3.s3.compare": "<b>Delta vergleichen.</b> Zwei Stände wählen (etwa 3 → 4) und „Delta-Briefing "
                     "öffnen“ — alle Folgepaare liegen fertig unter deltas/.",
    "c3.s3.after": "<b>Danach.</b> „Neuen Datenraum mit anderer Vorlage …“ springt zu Schritt 1 "
                   "zurück; die Zeile darunter zeigt den Befehl zum Fortschreiben (Kapitel 7).",

    # 4 -------------------------------------------------------------------
    "c4.h": "4  Was im Ordner liegt",
    "c4.p": "Der Zielordner ist ein <b>Portfolio-Datenraum</b>: Alle Pfade in den Configs sind "
            "relativ zur jeweiligen Config-Datei. Der Ordner lässt sich als Ganzes verschieben, "
            "kopieren oder zippen.",
    "c4.col_path": "Pfad",
    "c4.col_content": "Inhalt",
    "c4.structure": "Struktur als Daten: Portfolios → Solutions → ARTs, Workflow je Solution",
    "c4.story": "Geschichte als Daten: Vorlage, gebundene Rollen, Ereignisse mit Schalter und Stand-Fenster, Hinweise",
    "c4.readme": "Beschreibung von Struktur, Geschichte, Ständen, Quellen und weiteren Wegen — in der Sprache des Laufs",
    "c4.portfolio": "Einstieg: Portfolio-Config über alle Solutions",
    "c4.pi": "PI-Intervalle über den Datenzeitraum",
    "c4.solutions": "je Solution solution.json (eigene stage_map, wo gewählt), arts/ mit IssueTimes, Transitions und CFD je ART, registers/ mit den Registern unter Standardnamen",
    "c4.raw": "Jira-Exporte je ART im REST-API-Format — zugleich Demo-Futter für get_data",
    "c4.sources": "Provider-Rohdaten als Replay-Dateien (Prometheus, GitHub oder GitLab, SonarQube, CSV) plus sources-Configs",
    "c4.snapshots": "snapshot_&lt;nn&gt;_&lt;datum&gt;.json je Stand, Index stands.json, snapshot_prev/now.json = die letzten beiden",
    "c4.deltas": "delta_&lt;nn&gt;-&lt;nn+1&gt;.md und .html je Folgepaar — fertig gerendert",
    "c4.ai_drafts": "nur mit Schalter: Mock-Lagevortrag, Antworten, Prompt-Bündel, Übungsantwort — alle mit KI-Marker",
    "c4.use": "Der Ordner ist direkt verwendbar — Portfolio-Report, Delta-Briefing eines beliebigen "
              "Paars, Konferenzmappe, " + _c("sources fetch") + " ohne Netz auf den Replay-Dateien "
              "(in sources/&lt;solution&gt;/) und die Export-Prüfung von get_data:",
    "c4.multi": "Bei mehreren Portfolios (Vorlage „Groß“ oder eigene Struktur) entsteht je Portfolio "
                "ein eigener Datenraum als Unterordner; eine README im Hauptordner verweist auf "
                "sie. Ein Lagebild über mehrere Portfolios hinweg ist heute kein Feature — die Daten "
                "dafür liegen bereits nebeneinander.",

    # 5 -------------------------------------------------------------------
    "c5.h": "5  Die Geschichte verstehen",
    "c5.p": "Jede Vorlage erzählt dieselbe Lage aus allen Registern heraus: Risiken, Abhängigkeiten, "
            "Annahmen, SLOs und Wecker zeigen auf dieselben Stellen. Die Ereignisse binden an "
            "<b>Rollen</b>, die aus der Struktur folgen — so bleibt die Geschichte auch bei eigener "
            "Struktur stimmig.",
    "c5.roles": "<b>Die Rollen:</b><br/>"
                "- <b>Erste Solution</b> („Gastgeber“): wirkt gesund, trägt die stillen Muster; ihr "
                "<b>letzter ART ist der Ausreißer</b>; zwischen ihren ARTs liegen die blockierte "
                "Abhängigkeit und die wiederkehrende Naht.<br/>"
                "- <b>Zweite Solution:</b> ihr <b>letzter ART ist die schwache Datenquelle</b>; hier "
                "reißt die „Order Sync API“ ihr SLO und erscheint das neue Sicherheitsrisiko.<br/>"
                "- <b>Cross-Solution-Naht:</b> der erste ART der zweiten Solution hängt am ersten ART "
                "der ersten — nur im Portfolio-Report sichtbar.<br/>"
                "- Weitere Solutions und Portfolios erhalten die seed-erzeugte Grundmenge ohne Story-Anker.",
    "c5.notices": "Was die Struktur nicht hergibt, entfällt mit <b>Hinweis</b> (in Schritt 1 und in "
                  "story.json): Mit nur einer Solution gibt es keine schwache Quelle, keinen "
                  "SLO-Bruch und keine Cross-Solution-Naht; hat die erste Solution nur einen ART, "
                  "fehlen Ausreißer, blockierte Abhängigkeit und wiederkehrende Naht. Die zehn "
                  "Ereignisse:",
    "c5.col_id": "Nr.",
    "c5.col_what": "Was passiert",
    "c5.col_visible": "Sichtbar als",
    "ev.E1.title": "Der Ausreißer-ART hat etwa die dreifache Cycle Time.",
    "ev.E1.effect": "Comparison-Report: Median/P95 rot; Wecker „P85 über 30 Tagen“ ausgelöst; Delivery-Bild selten und langsam; eine Capability at risk.",
    "ev.E2.title": "Die schwache Quelle liefert schwache Daten: kein CFD, kaum First Dates, Datenstand 60 Tage alt.",
    "ev.E2.effect": "Konfidenz medium; ein Risiko altert (50 Tage); eine Capability kritisch; ein Flussproblem überlebt vier Konferenzen; eine Annahme überschreitet ihr Prüfdatum; DORA/Qualität low.",
    "ev.E3.title": "Die Abhängigkeit zwischen zwei ARTs der ersten Solution ist blockiert und überfällig.",
    "ev.E3.effect": "Abhängigkeit at_risk → blocked; Heatmap rot; Wecker „zwei blockierte“ unterschwellig.",
    "ev.E4.title": "Die Cross-Solution-Naht gerät unter Druck; die Value Streams ziehen aneinander.",
    "ev.E4.effect": "Mehrere Abhängigkeiten rutschen von on_track über at_risk nach blocked — nur im Portfolio-Report sichtbar; Grundlage des Entscheidungspunkt-Indikators.",
    "ev.E5.title": "Dieselbe Naht öffnet zum dritten Mal eine Solution Area zum selben Thema (Testumgebung).",
    "ev.E5.effect": "Zwei Solution Areas geschlossen, eine neu — das EA-Signal: Schnitt oder Architektur prüfen, nicht die Teams.",
    "ev.E6.title": "Die „Order Sync API“ der zweiten Solution reißt ihr SLO.",
    "ev.E6.effect": "SLO-Register: breached; NFR „API response time“ verletzt; eine Runway-Lücke überfällig.",
    "ev.E7.title": "Die erste Solution wirkt gesund — mit den stillen Mustern.",
    "ev.E7.effect": "Ein Risiko seit 45 Tagen owned (Aging); ein Theme ohne Epic („declared &amp; forgotten“); ein Flussproblem überlebt drei Konferenzen; eine Capability ohne ART; SLO „Checkout“ at risk.",
    "ev.E8.title": "Die Datenqualität der schwachen Quelle verfällt weiter.",
    "ev.E8.effect": "Anteil der Vorgänge ohne First Date steigt auf 80 % — Konfidenz medium → low, Abdeckung im Titel sichtbar.",
    "ev.E9.title": "Neues Risiko in der zweiten Solution: Security-Review nicht terminiert.",
    "ev.E9.effect": "Ein hohes, mitigiertes Risiko erscheint — im Delta-Briefing als neu.",
    "ev.E10.title": "Roadmaps aktualisiert.",
    "ev.E10.effect": "Ein Epic verliert sein Theme (Zombie-Initiative); ein Epic der zweiten Solution wird von P2 nach P1 gezogen.",
    "c5.windows": "<b>Stand-Fenster.</b> Jede Vorlage legt fest, in welchen Ständen ein Ereignis gilt. "
                  "Standard-Lage: Ausreißer, schwache Quelle, SLO-Bruch und stille Muster in allen "
                  "Ständen, die Wendungen (Blockade, Nähte, Verfall, neues Risiko, Roadmaps) nur im "
                  "letzten. Eskalation staffelt sie über die Reihe, Erholung kehrt sie um: Stand 1 "
                  "zeigt alles, dann heilt eines nach dem anderen. Die README des Datenraums "
                  "listet je Ereignis sein Fenster; davor und danach zeigt die Reihe die Lage ohne es.",

    # 6 -------------------------------------------------------------------
    "c6.h": "6  Der Datenraum auf der Kommandozeile",
    "c6.p": "Alles aus den drei Schritten gibt es auch als Option von " +
            _c("python -m testdata_generator --scenario portfolio") + ". Vor dem Bau nennt die "
            "Kommandozeile Struktur, Schalter und Schätzung; danach Ordner, Stände und Dauer.",
    "c6.col_opt": "Option",
    "c6.col_default": "Standard",
    "c6.col_meaning": "Bedeutung",
    "c6.folder_word": "ORDNER",
    "c6.required": "(Pflicht)",
    "c6.scenario": "Datenraum statt einzelnem ART erzeugen",
    "c6.output": "Zielordner (wird angelegt)",
    "c6.structure": "Struktur-Vorlage oder eigene structure.json (Portfolios → Solutions → ARTs, Workflow je Solution)",
    "c6.arts": "Ein Portfolio aus ART-Zahlen je Solution, z. B. 3,4s,1 — drei Solutions mit 3, 4 und 1 ARTs; ein angehängtes s gibt der Solution eine eigene Stage-Map. Nicht mit --structure kombinierbar.",
    "c6.story": "Vorlage der Geschichte (Ruhig, Standard-Lage, Eskalation, Erholung)",
    "c6.event": "Ein Ereignis an- oder abschalten, z. B. --event E3=off --event E9=on; wiederholbar. Ein Ereignis, dessen Voraussetzung aus ist, bleibt mit Hinweis aus.",
    "c6.stands_default": "6 (Ruhig 3)",
    "c6.stands": "Zahl der Stände (2–12), 14 Tage Abstand, der letzte auf dem Referenzdatum; jedes Folgepaar bekommt ein Delta-Briefing unter deltas/",
    "c6.scale": "Umfang der Register je Solution: s = nur Anker, m = realistische Demo, l = Stresstest",
    "c6.seed_default": "(zufällig)",
    "c6.seed": "Seed für reproduzierbare Ausgabe; die Oberfläche nimmt 42",
    "c6.art_profiles": "Regler je ART als JSON, z. B. {\"Alpha-1\": {\"mean_cycle_days\": 30, \"pattern\": \"cluster\", \"pattern_strength\": 80}}. Felder: issue_count, mean_cycle_days, std_cycle_days, completion_rate, todo_rate, backflow_prob, pattern, pattern_strength, pi_duration_weeks, realism. Overrides gelten in allen Ständen; alles andere behält seinen Story-Wert.",
    "c6.off": "aus",
    "c6.ai_drafts": "Mock-KI-Entwürfe mit Marker nach ai_drafts/ schreiben",
    "c6.lang_default": "Suite-Sprache, sonst en",
    "c6.lang": "Sprache von Oberfläche, Konsole und erzeugten Texten",
    "c6.continue": "Einen bestehenden Datenraum bis zum Datum fortschreiben (Kapitel 7)",
    "c6.web": "Browser-Oberfläche starten: lokaler Server auf 127.0.0.1 (Port 0 = zufällig frei), Zugangsschlüssel im Link; --no-browser druckt nur den Link. Ende mit Strg+C.",
    "c6.dataspace": "Datenraum-Fenster starten — dieselben drei Schritte ohne Server",
    "c6.ex.h": "Beispiele",
    "c6.ex.1": "Standard-Lage, wie in Tutorial und Handbüchern",
    "c6.ex.2": "Eskalation über acht Stände, Stresstest, deutsche Texte",
    "c6.ex.3": "Eigene Struktur, ein Ereignis aus, KI-Übung an",
    "c6.ex.4": "Fünf Portfolios, 49 ARTs — dauert spürbar",
    "c6.hint_default_lang": "Ohne --lang und ohne Launcher-Einstellung sind Konsole und erzeugte Texte "
                            "englisch. Wer Deutsch will, gibt --lang de mit oder stellt den Launcher um.",

    # 7 -------------------------------------------------------------------
    "c7.h": "7  Fortschreiben",
    "c7.p1": "Ein Datenraum lässt sich zu einem späteren Datum fortschreiben — wie ein zweiter Abzug "
             "aus Jira: Die Vergangenheit bleibt, offene Vorgänge laufen weiter, neue kommen dazu.",
    "c7.p2": "Der Generator schreibt die Jira-Exporte, IssueTimes/Transitions/CFD, Configs und die "
             "PI-Config im Ordner fort; der bisherige snapshot_now wird snapshot_prev, der neue Stand "
             "snapshot_now, und die README erhält einen Nachtrag mit altem und neuem Referenzdatum "
             "und der Zahl neuer Vorgänge. Die Register bleiben unverändert. Die Regler kommen aus "
             "dem Generator-Protokoll der Dateien; die Sprache folgt " + _c("--lang") + ".",
    "c7.hint": "Die Ergebniskarte zeigt den passenden Befehl unter „Danach“. Für einen einzelnen "
               "Jira-Export gibt es --continue OLD.json (Kapitel 8).",

    # 8 -------------------------------------------------------------------
    "c8.h": "8  Ein einzelner ART (klassischer Generator)",
    "c8.p": "Der klassische Weg erzeugt <b>eine</b> Jira-Export-Datei im REST-API-Format aus einer "
            "Workflow-Datei: Vorgänge durchlaufen die Stages, verbleiben unterschiedlich lange, "
            "fallen gelegentlich zurück und schließen mit einstellbarer Quote ab. Die Datei geht "
            "direkt in transform_data und build_reports. Die Regler für Cycle Time und Flow-Muster "
            "sind dieselben, die der Datenraum je ART über --art-profiles übersteuert.",
    "c8.win.h": "8.1  Das Fenster",
    "c8.win.p": "TestdataGenerator.bat (bzw. " + _c("python -m testdata_generator") + " ohne Option) "
                "öffnet das Fenster mit Eingabefeldern für alle Parameter. Pflichtfeld ist nur die "
                "Workflow-Datei; alles andere hat Standardwerte. Der Bereich „Demo-Portfolio“ unten "
                "erzeugt die Standard-Lage per Knopf — der Datenraum aus Kapitel 3 kann mehr.",
    "c8.win.fig": "Abb. 2: Fenster des klassischen Generators für einen einzelnen ART",
    "c8.wf.h": "8.2  Die Workflow-Datei",
    "c8.wf.p": "Die Workflow-Datei definiert die Stages deines Jira-Boards und ist das einzige "
               "Pflichtfeld. Sie hat dasselbe Format wie in transform_data — eine Datei genügt für "
               "beide Module. Jede Zeile beschreibt eine Stage; Aliases (alternative Status-Namen "
               "im Jira-Export) werden durch Doppelpunkte abgetrennt. Zwei Sonderzeilen markieren "
               "Anfang und Ende der aktiven Bearbeitung:",
    "c8.wf.pre": "KanonischerName:Alias1:Alias2\n<First>ErsteAktiveStage\n<Closed>AbgeschlosseneStage",
    "c8.wf.col_line": "Zeile",
    "c8.wf.col_meaning": "Bedeutung",
    "c8.wf.alias": "Stage mit einem oder mehreren alternativen Jira-Status-Namen",
    "c8.wf.plain_name": "Name (ohne :)",
    "c8.wf.plain": "Stage ohne Aliases",
    "c8.wf.first": "Erste aktive Stage — hier beginnt die Cycle Time",
    "c8.wf.closed": "Abgeschlossene Stage — markiert einen Vorgang als fertig",
    "c8.wf.example": "Das mitgelieferte Beispiel " + _c("workflow_ART_A.txt") + " bildet einen typischen SAFe-ART-Workflow ab:",
    "c8.wf.notes": "„Funnel“ hat vier Aliases — alle vier Jira-Status werden auf Funnel normiert. "
                   "Analysis ist die erste aktive Stage (Cycle Time beginnt hier). Releasing gilt als "
                   "abgeschlossen; Done (nach Releasing) nimmt auch Canceled-Vorgänge auf.",
    "c8.par.h": "8.3  Parameter-Referenz",
    "c8.par.p": "Alle Parameter gibt es im Fenster und auf der Kommandozeile.",
    "c8.par.col_param": "Parameter",
    "c8.par.col_default": "Standard",
    "c8.par.col_desc": "Beschreibung",
    "c8.par.workflow": "Workflow-Definitionsdatei (.txt)",
    "c8.par.output": "Pfad der Ausgabedatei",
    "c8.par.project": "Jira-Projekt-Key der erzeugten Vorgänge",
    "c8.par.issues": "Zahl der Vorgänge",
    "c8.par.from": "Frühestes Erstellungsdatum",
    "c8.par.to": "Spätestes Übergangsdatum",
    "c8.par.types": "Vorgangstypen mit Gewichtung (Summe muss nicht 1 ergeben)",
    "c8.par.completion": "Anteil der Vorgänge, die die Closed-Stage erreichen (0–1)",
    "c8.par.todo": "Anteil offener Vorgänge, die in frühen Stages verbleiben (0–1)",
    "c8.par.backflow": "Wahrscheinlichkeit eines Rückschritts je Übergang (0–1)",
    "c8.par.realism": "Unordnung der Statuswege: Sprünge, Abbrüche, Parken, Schleifen, Wiedereröffnung; etwa 70 wie ein echter ART",
    "c8.par.seed": "Seed für reproduzierbare Ausgabe",
    "c8.par.mean": "Mittlere Cycle Time in Tagen (lognormal); schaltet die Cycle-Time-Steuerung ein",
    "c8.par.std_default": "30 % des Mittels",
    "c8.par.std": "Standardabweichung der Cycle Time in Tagen",
    "c8.par.pattern": "Flow-Muster: none / triangle / flat_triangle / cluster / batch (siehe 8.4)",
    "c8.par.pi": "PI-Länge in Wochen (für cluster und batch)",
    "c8.par.strength": "Stärke des Musters (0 = subtil, 50 = Standard, 100 = stark)",
    "c8.par.continue": "Früheren Abzug bis --to-date fortschreiben: Vergangenheit bleibt Byte für Byte, offene Vorgänge laufen weiter, neue kommen dazu; braucht --workflow",
    "c8.par.learn": "Übergangsprofil aus einer echten Transitions-Datei lernen (nur Zählungen und Stunden); --transition-profile erzeugt damit",
    "c8.pat.h": "8.4  Flow-Muster",
    "c8.pat.p": "Der Generator simuliert typische Flow-Antipattern aus der Literatur von Vacanti und "
                "Singh. Dazu wird --mean-cycle-days mit --pattern kombiniert; im Fenster gibt es "
                "Auswahlknöpfe und Schieberegler.",
    "c8.pat.col_pattern": "Muster",
    "c8.pat.col_look": "Scatterplot",
    "c8.pat.col_desc": "Beschreibung",
    "c8.pat.none.look": "Gleichmäßige Punktwolke",
    "c8.pat.none.desc": "Zufällige Cycle Time ohne Trend — Standardverhalten",
    "c8.pat.triangle.look": "Dreieck, rechter Winkel unten rechts",
    "c8.pat.triangle.desc": "Cycle Time steigt linear über die Zeit (etwa 1–4× bei Standardstärke). Ein Prozess, der zunehmend langsamer wird.",
    "c8.pat.flat.look": "Dreieck, Anstieg flacht ab",
    "c8.pat.flat.desc": "Wie triangle, der Anstieg verflacht am Ende. Eine Verschlechterung, die sich stabilisiert.",
    "c8.pat.cluster.look": "Senkrechte Häufungen am PI-Ende",
    "c8.pat.cluster.desc": "Cycle Time bleibt stabil, aber die meisten Vorgänge schließen in den letzten zwei Wochen vor PI-Ende. Deadline-getriebenes Verhalten.",
    "c8.pat.batch.look": "Säulen variabler Höhe am PI-Ende",
    "c8.pat.batch.desc": "Wie cluster, aber mit stark unterschiedlicher Cycle Time (0,1× bis 3× Mittel). Kurze und sehr lange Aufgaben werden gemeinsam ans PI-Ende geschoben.",
    "c8.pat.hint": "--pattern erfordert --mean-cycle-days; ohne wird das Muster ignoriert. "
                   "--std-cycle-days steuert die Streuung, --pi-duration-weeks die PI-Länge für cluster und batch.",
    "c8.ex.h": "8.5  ART_A — vollständiges Beispiel",
    "c8.ex.p": "Vom Generator bis zum fertigen Report am fiktiven Projekt ART_A:",
    "c8.ex.s1": "Schritt 1: Testdaten erzeugen",
    "c8.ex.s2": "Schritt 2: Mit transform_data verarbeiten",
    "c8.ex.s3": "Schritt 3: Report mit build_reports erstellen",
    "c8.ex.expect": "<b>Was zu erwarten ist (Seed 42, 200 Vorgänge):</b><br/>"
                    "- Keys ART_A-0001 bis ART_A-0200<br/>"
                    "- Typen etwa 120 Feature, 40 Bug, 40 Enabler<br/>"
                    "- Etwa 150 Vorgänge in Releasing oder Done<br/>"
                    "- Erstellungsdaten über das Jahr 2025 verteilt<br/>"
                    "- Gelegentliche Rückschritte (backflow-prob 0.08 = etwa 8 %)",

    # 9 -------------------------------------------------------------------
    "c9.h": "9  Häufige Fragen",
    "c9.q1": "Fenster oder Browser — was soll ich nehmen?",
    "c9.a1": "Das Fenster. Es erzeugt denselben Datenraum und öffnet keinen Netzwerkport. Die "
             "Browser-Seite nur auf einem privaten Rechner; auf Firmenrechnern blockiert und "
             "meldet die Sicherheitssoftware lokale Server.",
    "c9.q2": "Warum ist mein Datenraum englisch, obwohl ich Deutsch spreche?",
    "c9.a2": "Ohne Sprachangabe nimmt der Generator die Suite-Sprache aus dem Launcher, sonst "
             "Englisch. Stell den Launcher auf Deutsch, schalte oben rechts um oder gib "
             "--lang de mit.",
    "c9.q3": "Der Zielordner ist nicht leer — was passiert?",
    "c9.a3": "Der Generator fragt nach. „Trotzdem erzeugen“ überschreibt Dateien gleichen Namens "
             "und lässt alles andere stehen; „Anderen Ordner wählen“ bricht ab.",
    "c9.q4": "Die Erzeugung dauert lange.",
    "c9.a4": "Ab 30 ARTs oder bei Umfang L mit mehreren Portfolios warnt die Box „Was entsteht“. "
             "Für Schulungen reichen Standard-Struktur und Umfang M (rund 10 Sekunden).",
    "c9.q5": "Testdaten oder echte Daten?",
    "c9.a5": "Für Demos, Schulungen und Installationstests sind Testdaten die bessere Wahl — ohne "
             "Datenschutzfrage. Für echte Flow-Analysen und Entscheidungen braucht es echte "
             "Daten; den manuellen Export beschreibt das Handbuch Get Data.",
    "c9.q6": "Kann ich einzelne ARTs anders einstellen?",
    "c9.a6": "Ja, über --art-profiles DATEI.json auf der Kommandozeile (Kapitel 6). Der Reiter "
             "dafür in der Oberfläche folgt in einem späteren Beta-Stand.",

    # 10 ------------------------------------------------------------------
    "c10.h": "10  Glossar",
    "c10.col_term": "Begriff",
    "c10.col_expl": "Erklärung",
    "g.art.t": "ART",
    "g.art.e": "Agile Release Train — mehrere Teams, die in SAFe gemeinsam liefern",
    "g.dataspace.t": "Datenraum",
    "g.dataspace.e": "Ein Ordner mit allem, was ein Portfolio-Lagebild braucht: Configs, Exporte, Register, Stände, Briefings — in sich geschlossen und verschiebbar",
    "g.delta.t": "Delta-Briefing",
    "g.delta.e": "„Was hat sich geändert?“ zwischen zwei Ständen — Durchsatz, Konfidenz, Nähte, neue Risiken",
    "g.conference.t": "Konferenzmappe",
    "g.conference.e": "Die Mappe für die Value Stream Conference: Flussprobleme, die Konferenzen überleben, mit dem Lagebild dazu",
    "g.seam.t": "Naht",
    "g.seam.e": "Eine Abhängigkeit zwischen ARTs oder Solutions, an der sich Druck zeigt — innerhalb einer Solution oder zwischen den Value Streams",
    "g.register.t": "Register",
    "g.register.e": "Eine Liste je Solution: Risiken, Abhängigkeiten, Annahmen, NFR, Runway, SLO, DORA, Capabilities, Themen, Flussprobleme …",
    "g.stand.t": "Stand",
    "g.stand.e": "Ein eingefrorener Snapshot des Lagebilds zu einem Datum; die Stände liegen 14 Tage auseinander",
    "g.seed.t": "Seed",
    "g.seed.e": "Startwert des Zufallsgenerators — gleicher Seed, gleiche Ausgabe",
    "g.solution.t": "Solution",
    "g.solution.e": "Eine Gruppe von ARTs, die gemeinsam eine Lösung liefert; im Datenraum die Ebene mit eigenen Registern",
    "g.stage_map.t": "Stage-Map",
    "g.stage_map.e": "Eigene Zusammenfassung der Workflow-Stages einer Solution (etwa Vorlauf/Umsetzung/Fertig) statt des Default-Pfads",
    "g.value_stream.t": "Value Stream",
    "g.value_stream.e": "Der Fluss vom Bedarf bis zum Wert; im Datenraum durch die Solutions vertreten",
    "g.workflow.t": "Workflow",
    "g.workflow.e": "Geordnete Abfolge von Stages, die ein Vorgang durchläuft; als Textdatei beschrieben",
    "g.realism.t": "Realismus",
    "g.realism.e": "Grad der Unordnung in den Statuswegen: Sprünge, Abbrüche, Parken, Schleifen, Wiedereröffnung",
    "g.cfd.t": "CFD",
    "g.cfd.e": "Cumulative Flow Diagram — Bestand je Stage über die Zeit, kumuliert",
}

_M["en"] = {
    # 1 -------------------------------------------------------------------
    "c1.h": "1  What is the Testdata Generator?",
    "c1.p1": "The <b>Testdata Generator</b> produces invented but realistic data for SituationReport "
             "— so you can demonstrate, learn and test the portfolio report, delta briefing, "
             "conference folder and the registers without touching real project data. No persons "
             "appear; the same seed yields the same data room.",
    "c1.p2": "The generator has two paths. The <b>data room</b> is the default path of the beta: in "
             "three steps it builds a complete portfolio folder with structure, story, Jira exports "
             "per ART, registers, provider raw data, a series of stands and the rendered delta "
             "briefings. The <b>single ART</b> is the classic path: one Jira export file from a "
             "workflow file, with every knob for cycle time and flow patterns (chapter 8).",
    "c1.ways": "<b>Which path when?</b><br/>"
               "- <b>Data room (window or browser):</b> training, presentation, tutorials, tests of "
               "the portfolio chain — everything that needs a whole situation picture.<br/>"
               "- <b>Single ART:</b> one Jira export for transform_data and build_reports, targeted "
               "flow patterns for cycle-time scatterplot training, continuation of an earlier extract.",
    "c1.p3": "This manual describes the data room first (chapters 2 to 7) and the classic single-ART "
             "generator afterwards (chapter 8). If you only want the one minute to the first "
             "portfolio report, take the tutorial “Demo data room in one minute” "
             "(docs/tutorials/demo-data-room.md, also as PDF).",
    "c1.uses": "<b>Typical uses:</b><br/>"
               "- <b>Test a new installation:</b> does the chain run from raw data to the portfolio report?<br/>"
               "- <b>Demos and presentations:</b> a situation with outlier, weak source and seams, "
               "with no privacy question<br/>"
               "- <b>Training:</b> the same story for every participant, reproducible through the seed<br/>"
               "- <b>Development:</b> stress test with a large structure (scale L, up to 49 ARTs)",
    "c1.beta": "Status: beta, October 2026. The data-room UI is new; the tab for per-ART profiles in "
               "the UI is still missing (command line: --art-profiles).",

    # 2 -------------------------------------------------------------------
    "c2.h": "2  Getting started",
    "c2.pkg.h": "2.1  Portable package (recommended)",
    "c2.pkg.p": "The portable package embeds Python — nothing to install. After unpacking, four "
                "start files for the generator are ready:",
    "c2.pkg.col_file": "Start file (Windows)",
    "c2.pkg.col_what": "What it opens",
    "c2.pkg.window": "<b>Data room as a window</b> — the default path. Three steps, no network port, "
                     "runs on company computers too.",
    "c2.pkg.launcher": "The launcher with all modules; it carries the cards “Data room (window)” and "
                       "“Data room (browser)” as well as “Testdata Generator” for the single ART.",
    "c2.pkg.browser": "<b>Data room in the browser</b> — the same three steps as a web page. Starts a "
                      "local server on 127.0.0.1 with a random key in the link. Private computers "
                      "only: security software on company computers blocks and reports local servers.",
    "c2.pkg.single": "<b>Single ART</b> — the classic window with workflow file, knobs and flow "
                     "patterns (chapter 8).",
    "c2.pkg.unix": "macOS: the same names as .command (right-click → Open). Linux: as .sh (python3 "
                   "and python3-tk required). The first start sets up a Python environment once — "
                   "this needs internet.",
    "c2.pkg.defender": "Note for Windows: if the start reports that Python cannot be found, Windows "
                       "had blocked the ZIP file. Right-click the ZIP → Properties → Security → "
                       "Unblock → OK → unpack again.",
    "c2.src.h": "2.2  From source (Python required)",
    "c2.src.p": "The three UIs correspond to three calls: window, browser, single ART.",
    "c2.wvb.h": "2.3  Window or browser?",
    "c2.wvb.p": "Both show the same three steps with the same settings and produce the same data "
                "room. The window is an ordinary program window (tkinter) and needs nothing else. "
                "The browser page is slightly more comfortable to read but runs through a local "
                "server — on a company computer the endpoint security blocked and reported that in "
                "the first test. Hence: window first, browser only privately.",
    "c2.lang.h": "2.4  Languages",
    "c2.lang.p": "UI, story, README, progress, log and the generated delta briefings exist in German, "
                 "English, Romanian, Portuguese and French. The generator starts in the language set "
                 "in the launcher; the switch at the top right of window and browser page changes it "
                 "— inputs are kept. One run has one language: UI and generated texts match. Without "
                 "a launcher setting and without " + _c("--lang") + " the language is English. "
                 "Romanian, Portuguese and French are drafts still to be reviewed by native speakers.",

    # 3 -------------------------------------------------------------------
    "c3.h": "3  The data room in three steps",
    "c3.p": "Window and browser page lead through three steps: <b>Scenario</b> (which situation), "
            "<b>Scope &amp; sources</b> (how big, how long, how real) and <b>Generate</b> (where to, "
            "and go). The defaults produce the demo situation that the tutorials and manuals of the "
            "portfolio modules use as well.",
    "c3.fig": "Fig. 1: Step 1 “Scenario” in the data-room window — templates on the left, events "
              "below, structure on the right (German UI)",
    "c3.s1.h": "3.1  Step 1 — Scenario",
    "c3.s1.p": "On the left you pick a <b>template</b> of the story. The events bind to roles of the "
               "structure on the right — outlier, weak source, seams — not to fixed names.",
    "c3.s1.col_tpl": "Template",
    "c3.s1.col_tells": "What it tells",
    "c3.s1.col_stands": "Stands",
    "tpl.calm": "Calm",
    "tpl.calm.desc": "No turning points, every team within bounds. For the first training and for "
                     "reading a quiet picture. Whoever raises an alarm here has misread the picture.",
    "tpl.standard": "Standard situation",
    "c3.s1.rec": "(recommended)",
    "tpl.standard.desc": "Outlier, weak source, SLO breach and silent patterns from the start; the "
                         "turning points arrive with the last stand. For presentations and tutorials.",
    "tpl.escalation": "Escalation",
    "tpl.escalation.desc": "Pressure rises stand by stand: SLO breach early, blocked seam in the "
                           "middle, decay and cross-solution seams late. For the conference exercise.",
    "tpl.recovery": "Recovery",
    "tpl.recovery.desc": "Starts badly and heals: seams resolved, SLO holds, the outlier finds its "
                         "rhythm. For the delta briefing: what has changed?",
    "c3.s1.events": "<b>Events of the template.</b> The table below shows for each event when it "
                    "applies (all stands, from stand n, last stand), what happens and as what it "
                    "becomes visible in the report. Every event has a checkbox; switched-off events "
                    "are absent from the data room. An event whose prerequisite is off stays off with "
                    "a notice. The window of an event follows the number of stands from step 2. "
                    "Chapter 5 explains the ten events.",
    "c3.s1.structure": "<b>Structure of the data room (right).</b> A structure template — Small "
                       "(1 portfolio · 1 solution · 2 ARTs), Standard (1 · 2 · 3 each), Large "
                       "(5 portfolios · 3–4 solutions · 1–6 ARTs) — or your own: add or remove "
                       "portfolios and solutions, count ARTs per solution, change names (ART names "
                       "follow the solution). Per solution you choose the classic workflow or an own "
                       "stage map. At least one ART per solution.",
    "c3.s1.yields": "<b>What is produced.</b> The box at the bottom right keeps count: Jira exports, "
                    "workbooks, registers, stands and delta briefings for the chosen structure "
                    "(standard: 6 exports, 18 workbooks, 22 registers, 6 stands, 5 deltas). From "
                    "30 ARTs it warns: generation then takes noticeably longer.",
    "c3.s2.h": "3.2  Step 2 — Scope &amp; sources",
    "c3.s2.p": "The defaults are enough for training and presentation.",
    "c3.s2.col_setting": "Setting",
    "c3.s2.col_default": "Default",
    "c3.s2.col_meaning": "Meaning",
    "ui.stands": "Stands",
    "ui.scale": "Scale",
    "ui.realism": "Realism",
    "ui.seed": "Seed",
    "ui.reference": "Last stand",
    "ui.lang": "Language of the texts",
    "c3.s2.stands": "2 to 12 stands, 14 days apart; every stand is a frozen snapshot, every "
                    "consecutive pair a rendered delta briefing. The “Calm” template suggests 3.",
    "c3.s2.scale": "S = story anchors only, short registers; M = realistic registers; L = stress "
                   "test with full registers (dense heatmap, full roadmap matrix). The anchors and "
                   "their stories are identical at every level.",
    "c3.s2.realism": "Untidiness of the status paths: skips, cancels, parking, loops, reopening. "
                     "0 = smooth, 100 = like real; 60 is a typical ART.",
    "c3.s2.seed": "The same seed, structure and reference date yield the same data room — ideal "
                  "when every participant should see the same thing.",
    "c3.s2.today": "today",
    "c3.s2.reference": "Date of the last stand; the others lie 14 days apart before it. The quality "
                       "traffic light of the portfolio report thus rates the data as current.",
    "c3.s2.ui_lang": "UI language",
    "c3.s2.lang": "Language of story, README and delta briefings; follows the UI.",
    "c3.s2.details": "<b>Details for analysts.</b> Cycle times, flow patterns and PI length can be "
                     "overridden per ART — the same knobs as for the single ART. In this beta that "
                     "works on the command line with " + _c("--art-profiles FILE.json") +
                     " (chapter 6); the table in the UI follows with the ART tab.",
    "c3.s2.sources": "<b>Sources shipped with the room.</b> Always included: Jira exports per ART (no "
                     "persons), Prometheus SLO responses, GitHub deployments/PRs/incidents for the "
                     "first solution, GitLab DORA daily values for the second, SonarQube quality "
                     "measures and an SLO CSV for the manual path — raw data in each system's own "
                     "format with the same numbers as the registers, so that " + _c("sources fetch") +
                     " runs in the data room without network.",
    "c3.s2.ai": "<b>AI drafts (switch, off by default).</b> A mock spoken briefing, three answers, a "
                "prompt bundle and a practice answer with wrong numbers land in ai_drafts/ — all "
                "carrying the AI marker, none approved. With them you practise approval and " +
                _c("llm check") + " without installing a model.",
    "c3.s2.estimate": "The <b>Estimate</b> line at the end names Jira exports, registers, stands and "
                      "deltas for your settings; the footer summarises template, scale, stands, "
                      "realism and seed.",
    "c3.s3.h": "3.3  Step 3 — Generate",
    "c3.s3.target": "<b>Target folder.</b> It is created. If it is not empty, the generator asks — "
                    "“Generate anyway” overwrites files of the same name, “Choose another folder” "
                    "goes back. “Browse …” opens the folder dialog; where none is available, you "
                    "type the path.",
    "c3.s3.progress": "<b>Progress.</b> “Generate data room” starts nine steps; each shows running, "
                      "done or skipped with a detail. Duration ranges from seconds to minutes "
                      "depending on scope (standard situation about 10 seconds).",
    "c3.s3.col_step": "Step",
    "c3.s3.col_makes": "What is produced",
    "step.story": "Structure and story",
    "step.arts": "Jira exports and workbooks",
    "step.registers": "Registers",
    "step.configs": "Configurations",
    "step.sources": "Provider raw data",
    "step.readme": "README",
    "step.stands": "Series of stands",
    "step.deltas": "Delta briefings",
    "step.ai_drafts": "AI drafts (mock)",
    "c3.s3.st.story": "structure.json and story.json: roles bound, events fixed",
    "c3.s3.st.arts": "per ART one Jira export under raw/ and IssueTimes/Transitions/CFD under solutions/…/arts/",
    "c3.s3.st.registers": "per solution the registers (risks, dependencies, NFR, SLO, DORA, capabilities, themes …)",
    "c3.s3.st.configs": "portfolio.json, solution.json per solution, pi_config.json",
    "c3.s3.st.sources": "sources/&lt;solution&gt;/ with replay files and sources configs",
    "c3.s3.st.readme": "README.md with structure, story, stands and further paths",
    "c3.s3.st.stands": "snapshots/snapshot_&lt;nn&gt;_&lt;date&gt;.json per stand, stands.json, prev/now",
    "c3.s3.st.deltas": "deltas/delta_&lt;nn&gt;-&lt;nn+1&gt;.md and .html per consecutive pair",
    "c3.s3.st.ai_drafts": "ai_drafts/ — only with the switch, otherwise “skipped”",
    "c3.s3.cancel": "<b>Cancel</b> stops after the running step; the folder contains what was built "
                    "until then. An error appears with its message in the list.",
    "c3.s3.result": "<b>Result card.</b> After the last step “Data room ready” appears with duration "
                    "and seed, four figures (issues and ARTs, registers and solutions, stands, source "
                    "types), the story in three sentences and buttons: Open portfolio report, "
                    "Conference folder, Latest delta, README, Open folder, AI drafts (if generated). "
                    "Reports are rendered on the first click and opened in the browser.",
    "c3.s3.compare": "<b>Compare delta.</b> Pick two stands (say 3 → 4) and “Open delta briefing” — "
                     "all consecutive pairs lie ready under deltas/.",
    "c3.s3.after": "<b>Afterwards.</b> “New data room with another template …” jumps back to step 1; "
                   "the line below shows the command for continuation (chapter 7).",

    # 4 -------------------------------------------------------------------
    "c4.h": "4  What lies in the folder",
    "c4.p": "The target folder is a <b>portfolio data room</b>: all paths in the configs are relative "
            "to their config file. The folder can be moved, copied or zipped as a whole.",
    "c4.col_path": "Path",
    "c4.col_content": "Content",
    "c4.structure": "Structure as data: portfolios → solutions → ARTs, workflow per solution",
    "c4.story": "Story as data: template, bound roles, events with switch and stand window, notices",
    "c4.readme": "Description of structure, story, stands, sources and further paths — in the language of the run",
    "c4.portfolio": "Entry point: portfolio config across all solutions",
    "c4.pi": "PI intervals across the data period",
    "c4.solutions": "per solution solution.json (own stage_map where chosen), arts/ with IssueTimes, Transitions and CFD per ART, registers/ with the registers under standard names",
    "c4.raw": "Jira exports per ART in REST API format — at the same time demo input for get_data",
    "c4.sources": "provider raw data as replay files (Prometheus, GitHub or GitLab, SonarQube, CSV) plus sources configs",
    "c4.snapshots": "snapshot_&lt;nn&gt;_&lt;date&gt;.json per stand, index stands.json, snapshot_prev/now.json = the last two",
    "c4.deltas": "delta_&lt;nn&gt;-&lt;nn+1&gt;.md and .html per consecutive pair — rendered",
    "c4.ai_drafts": "only with the switch: mock spoken briefing, answers, prompt bundle, practice answer — all with the AI marker",
    "c4.use": "The folder is directly usable — portfolio report, delta briefing of any pair, "
              "conference folder, " + _c("sources fetch") + " without network on the replay files "
              "(in sources/&lt;solution&gt;/) and the export check of get_data:",
    "c4.multi": "With several portfolios (template “Large” or own structure) each portfolio becomes "
                "its own data room in a sub-folder; a README in the main folder points to them. A "
                "situation picture across several portfolios is not a feature today — the data for "
                "it already lies side by side.",

    # 5 -------------------------------------------------------------------
    "c5.h": "5  Understanding the story",
    "c5.p": "Every template tells the same situation from all registers: risks, dependencies, "
            "assumptions, SLOs and alarms point at the same places. The events bind to <b>roles</b> "
            "that follow from the structure — so the story stays coherent with your own structure too.",
    "c5.roles": "<b>The roles:</b><br/>"
                "- <b>First solution</b> (“host”): looks healthy, carries the silent patterns; its "
                "<b>last ART is the outlier</b>; between its ARTs lie the blocked dependency and the "
                "recurring seam.<br/>"
                "- <b>Second solution:</b> its <b>last ART is the weak data source</b>; here the "
                "“Order Sync API” breaches its SLO and the new security risk appears.<br/>"
                "- <b>Cross-solution seam:</b> the first ART of the second solution depends on the "
                "first ART of the first — visible only in the portfolio report.<br/>"
                "- Further solutions and portfolios receive the seed-generated base set without story anchors.",
    "c5.notices": "What the structure cannot provide is dropped with a <b>notice</b> (in step 1 and in "
                  "story.json): with a single solution there is no weak source, no SLO breach and no "
                  "cross-solution seam; if the first solution has only one ART, outlier, blocked "
                  "dependency and recurring seam are missing. The ten events:",
    "c5.col_id": "No.",
    "c5.col_what": "What happens",
    "c5.col_visible": "Visible as",
    "ev.E1.title": "The outlier ART has about three times the cycle time.",
    "ev.E1.effect": "Comparison report: median/P95 red; alarm “P85 over 30 days” triggered; delivery picture rare and slow; one capability at risk.",
    "ev.E2.title": "The weak source delivers weak data: no CFD, hardly any first dates, data 60 days old.",
    "ev.E2.effect": "Confidence medium; one risk ages (50 days); one capability critical; one flow problem survives four conferences; one assumption passes its review date; DORA/quality low.",
    "ev.E3.title": "The dependency between two ARTs of the first solution is blocked and overdue.",
    "ev.E3.effect": "Dependency at_risk → blocked; heatmap red; alarm “two blocked” just below threshold.",
    "ev.E4.title": "The cross-solution seam comes under pressure; the value streams pull at each other.",
    "ev.E4.effect": "Several dependencies slide from on_track via at_risk to blocked — visible only in the portfolio report; basis of the decision-point indicator.",
    "ev.E5.title": "The same seam opens a solution area on the same topic (test environment) for the third time.",
    "ev.E5.effect": "Two solution areas closed, one new — the EA signal: check the cut or the architecture, not the teams.",
    "ev.E6.title": "The “Order Sync API” of the second solution breaches its SLO.",
    "ev.E6.effect": "SLO register: breached; NFR “API response time” violated; one runway gap overdue.",
    "ev.E7.title": "The first solution looks healthy — with the silent patterns.",
    "ev.E7.effect": "One risk owned for 45 days (aging); one theme without epic (“declared &amp; forgotten”); one flow problem survives three conferences; one capability without ART; SLO “Checkout” at risk.",
    "ev.E8.title": "The data quality of the weak source decays further.",
    "ev.E8.effect": "Share of issues without first date rises to 80 % — confidence medium → low, coverage visible in the title.",
    "ev.E9.title": "New risk in the second solution: security review not scheduled.",
    "ev.E9.effect": "A high, mitigated risk appears — new in the delta briefing.",
    "ev.E10.title": "Roadmaps updated.",
    "ev.E10.effect": "One epic loses its theme (zombie initiative); one epic of the second solution is pulled from P2 to P1.",
    "c5.windows": "<b>Stand windows.</b> Every template fixes in which stands an event applies. "
                  "Standard situation: outlier, weak source, SLO breach and silent patterns in all "
                  "stands, the turning points (blockage, seams, decay, new risk, roadmaps) only in "
                  "the last. Escalation staggers them over the series, Recovery reverses them: "
                  "stand 1 shows everything, then one thing after another heals. The README of the "
                  "data room lists each event's window; before and after it the series shows the "
                  "situation without it.",

    # 6 -------------------------------------------------------------------
    "c6.h": "6  The data room on the command line",
    "c6.p": "Everything from the three steps is also an option of " +
            _c("python -m testdata_generator --scenario portfolio") + ". Before building, the "
            "command line prints structure, switches and estimate; afterwards folder, stands and duration.",
    "c6.col_opt": "Option",
    "c6.col_default": "Default",
    "c6.col_meaning": "Meaning",
    "c6.folder_word": "FOLDER",
    "c6.required": "(required)",
    "c6.scenario": "Generate a data room instead of a single ART",
    "c6.output": "Target folder (is created)",
    "c6.structure": "Structure template or own structure.json (portfolios → solutions → ARTs, workflow per solution)",
    "c6.arts": "One portfolio from ART counts per solution, e.g. 3,4s,1 — three solutions with 3, 4 and 1 ARTs; a trailing s gives that solution its own stage map. Not combinable with --structure.",
    "c6.story": "Story template (calm, standard, escalation, recovery)",
    "c6.event": "Switch one event on or off, e.g. --event E3=off --event E9=on; repeatable. An event whose prerequisite is off stays off with a notice.",
    "c6.stands_default": "6 (calm 3)",
    "c6.stands": "Number of stands (2–12), 14 days apart, the last on the reference date; every consecutive pair gets a delta briefing under deltas/",
    "c6.scale": "Register volume per solution: s = anchors only, m = realistic demo, l = stress test",
    "c6.seed_default": "(random)",
    "c6.seed": "Seed for reproducible output; the UI uses 42",
    "c6.art_profiles": "Knobs per ART as JSON, e.g. {\"Alpha-1\": {\"mean_cycle_days\": 30, \"pattern\": \"cluster\", \"pattern_strength\": 80}}. Fields: issue_count, mean_cycle_days, std_cycle_days, completion_rate, todo_rate, backflow_prob, pattern, pattern_strength, pi_duration_weeks, realism. Overrides apply in all stands; everything else keeps its story value.",
    "c6.off": "off",
    "c6.ai_drafts": "Write mock AI drafts with marker to ai_drafts/",
    "c6.lang_default": "suite language, else en",
    "c6.lang": "Language of UI, console and generated texts",
    "c6.continue": "Continue an existing data room up to the date (chapter 7)",
    "c6.web": "Start the browser UI: local server on 127.0.0.1 (port 0 = random free), access key in the link; --no-browser only prints the link. Ends with Ctrl+C.",
    "c6.dataspace": "Start the data-room window — the same three steps without a server",
    "c6.ex.h": "Examples",
    "c6.ex.1": "Standard situation, as in tutorial and manuals",
    "c6.ex.2": "Escalation over eight stands, stress test, German texts",
    "c6.ex.3": "Own structure, one event off, AI practice on",
    "c6.ex.4": "Five portfolios, 49 ARTs — takes noticeably longer",
    "c6.hint_default_lang": "Without --lang and without a launcher setting, console and generated texts "
                            "are English. For German pass --lang de or switch the launcher.",

    # 7 -------------------------------------------------------------------
    "c7.h": "7  Continuing a data room",
    "c7.p1": "A data room can be continued to a later date — like a second extract from Jira: the "
             "past stays, open issues move on, new ones are added.",
    "c7.p2": "The generator continues the Jira exports, IssueTimes/Transitions/CFD, configs and the "
             "PI config in place; the previous snapshot_now becomes snapshot_prev, the new stand "
             "snapshot_now, and the README gets a note with old and new reference date and the "
             "number of new issues. The registers stay unchanged. The knobs come from the generator "
             "record of the files; the language follows " + _c("--lang") + ".",
    "c7.hint": "The result card shows the matching command under “Afterwards”. For a single Jira "
               "export there is --continue OLD.json (chapter 8).",

    # 8 -------------------------------------------------------------------
    "c8.h": "8  A single ART (classic generator)",
    "c8.p": "The classic path produces <b>one</b> Jira export file in REST API format from a "
            "workflow file: issues pass through the stages, dwell for varying times, occasionally "
            "fall back and close at a configurable rate. The file goes straight into transform_data "
            "and build_reports. The knobs for cycle time and flow patterns are the same ones the data "
            "room overrides per ART through --art-profiles.",
    "c8.win.h": "8.1  The window",
    "c8.win.p": "TestdataGenerator.bat (or " + _c("python -m testdata_generator") + " without "
                "options) opens the window with input fields for every parameter. Only the workflow "
                "file is mandatory; everything else has defaults. The “Demo portfolio” area at the "
                "bottom builds the standard situation at a click — the data room of chapter 3 can do more.",
    "c8.win.fig": "Fig. 2: Window of the classic generator for a single ART",
    "c8.wf.h": "8.2  The workflow file",
    "c8.wf.p": "The workflow file defines the stages of your Jira board and is the only mandatory "
               "field. It has the same format as in transform_data — one file serves both modules. "
               "Each line describes a stage; aliases (alternative status names in the Jira export) "
               "are separated by colons. Two special lines mark the start and end of active work:",
    "c8.wf.pre": "CanonicalName:Alias1:Alias2\n<First>FirstActiveStage\n<Closed>ClosedStage",
    "c8.wf.col_line": "Line",
    "c8.wf.col_meaning": "Meaning",
    "c8.wf.alias": "Stage with one or more alternative Jira status names",
    "c8.wf.plain_name": "Name (no :)",
    "c8.wf.plain": "Stage without aliases",
    "c8.wf.first": "First active stage — cycle time starts here",
    "c8.wf.closed": "Closed stage — marks an issue as done",
    "c8.wf.example": "The bundled example " + _c("workflow_ART_A.txt") + " models a typical SAFe ART workflow:",
    "c8.wf.notes": "“Funnel” has four aliases — all four Jira statuses normalise to Funnel. Analysis is "
                   "the first active stage (cycle time starts here). Releasing counts as closed; Done "
                   "(after Releasing) also takes cancelled issues.",
    "c8.par.h": "8.3  Parameter reference",
    "c8.par.p": "All parameters exist in the window and on the command line.",
    "c8.par.col_param": "Parameter",
    "c8.par.col_default": "Default",
    "c8.par.col_desc": "Description",
    "c8.par.workflow": "Workflow definition file (.txt)",
    "c8.par.output": "Output file path",
    "c8.par.project": "Jira project key of the generated issues",
    "c8.par.issues": "Number of issues",
    "c8.par.from": "Earliest creation date",
    "c8.par.to": "Latest transition date",
    "c8.par.types": "Issue types with weights (need not sum to 1)",
    "c8.par.completion": "Share of issues reaching the closed stage (0–1)",
    "c8.par.todo": "Share of open issues staying in early stages (0–1)",
    "c8.par.backflow": "Probability of a backward step per transition (0–1)",
    "c8.par.realism": "Untidiness of the status paths: skips, cancels, parking, loops, reopening; about 70 is like a real ART",
    "c8.par.seed": "Seed for reproducible output",
    "c8.par.mean": "Mean cycle time in days (lognormal); enables cycle-time control",
    "c8.par.std_default": "30 % of mean",
    "c8.par.std": "Standard deviation of cycle time in days",
    "c8.par.pattern": "Flow pattern: none / triangle / flat_triangle / cluster / batch (see 8.4)",
    "c8.par.pi": "PI length in weeks (for cluster and batch)",
    "c8.par.strength": "Pattern intensity (0 = subtle, 50 = default, 100 = strong)",
    "c8.par.continue": "Continue an earlier extract up to --to-date: the past stays byte for byte, open issues move on, new ones are added; needs --workflow",
    "c8.par.learn": "Learn a transition profile from a real transitions file (counts and hours only); --transition-profile generates with it",
    "c8.pat.h": "8.4  Flow patterns",
    "c8.pat.p": "The generator simulates typical flow anti-patterns from the literature of Vacanti and "
                "Singh. Combine --mean-cycle-days with --pattern; the window offers radio buttons and sliders.",
    "c8.pat.col_pattern": "Pattern",
    "c8.pat.col_look": "Scatterplot",
    "c8.pat.col_desc": "Description",
    "c8.pat.none.look": "Even point cloud",
    "c8.pat.none.desc": "Random cycle time without trend — default behaviour",
    "c8.pat.triangle.look": "Triangle, right angle bottom right",
    "c8.pat.triangle.desc": "Cycle time rises linearly over time (about 1–4× at default strength). A process that slows down more and more.",
    "c8.pat.flat.look": "Triangle, rise flattens",
    "c8.pat.flat.desc": "Like triangle, the rise flattens towards the end. A deterioration that stabilises.",
    "c8.pat.cluster.look": "Vertical clusters at PI end",
    "c8.pat.cluster.desc": "Cycle time stays stable, but most issues close in the last two weeks before PI end. Deadline-driven behaviour.",
    "c8.pat.batch.look": "Columns of varying height at PI end",
    "c8.pat.batch.desc": "Like cluster, but with strongly varying cycle time (0.1× to 3× mean). Short and very long items are pushed to the PI end together.",
    "c8.pat.hint": "--pattern requires --mean-cycle-days; without it the pattern is ignored. "
                   "--std-cycle-days controls the spread, --pi-duration-weeks the PI length for cluster and batch.",
    "c8.ex.h": "8.5  ART_A — complete example",
    "c8.ex.p": "From the generator to the finished report on the fictional project ART_A:",
    "c8.ex.s1": "Step 1: Generate test data",
    "c8.ex.s2": "Step 2: Process with transform_data",
    "c8.ex.s3": "Step 3: Create the report with build_reports",
    "c8.ex.expect": "<b>What to expect (seed 42, 200 issues):</b><br/>"
                    "- Keys ART_A-0001 to ART_A-0200<br/>"
                    "- Types about 120 Feature, 40 Bug, 40 Enabler<br/>"
                    "- About 150 issues in Releasing or Done<br/>"
                    "- Creation dates spread over 2025<br/>"
                    "- Occasional backward steps (backflow-prob 0.08 = about 8 %)",

    # 9 -------------------------------------------------------------------
    "c9.h": "9  Frequently asked questions",
    "c9.q1": "Window or browser — which should I use?",
    "c9.a1": "The window. It produces the same data room and opens no network port. Use the browser "
             "page only on a private computer; on company computers the security software blocks "
             "and reports local servers.",
    "c9.q2": "Why is my data room in English although I speak German?",
    "c9.a2": "Without a language argument the generator takes the suite language from the launcher, "
             "else English. Set the launcher to German, switch at the top right or pass --lang de.",
    "c9.q3": "The target folder is not empty — what happens?",
    "c9.a3": "The generator asks. “Generate anyway” overwrites files of the same name and leaves "
             "everything else; “Choose another folder” aborts.",
    "c9.q4": "Generation takes long.",
    "c9.a4": "From 30 ARTs, or at scale L with several portfolios, the “What is produced” box warns. "
             "For training, standard structure and scale M are enough (about 10 seconds).",
    "c9.q5": "Test data or real data?",
    "c9.a5": "For demos, training and installation tests, test data is the better choice — no "
             "privacy question. Real flow analyses and decisions need real data; the manual export "
             "is described in the Get Data manual.",
    "c9.q6": "Can I set individual ARTs differently?",
    "c9.a6": "Yes, through --art-profiles FILE.json on the command line (chapter 6). The tab for it "
             "in the UI follows in a later beta.",

    # 10 ------------------------------------------------------------------
    "c10.h": "10  Glossary",
    "c10.col_term": "Term",
    "c10.col_expl": "Explanation",
    "g.art.t": "ART",
    "g.art.e": "Agile Release Train — several teams delivering together in SAFe",
    "g.dataspace.t": "Data room",
    "g.dataspace.e": "A folder with everything a portfolio situation picture needs: configs, exports, registers, stands, briefings — self-contained and movable",
    "g.delta.t": "Delta briefing",
    "g.delta.e": "“What has changed?” between two stands — throughput, confidence, seams, new risks",
    "g.conference.t": "Conference folder",
    "g.conference.e": "The folder for the value stream conference: flow problems that survive conferences, with the situation picture",
    "g.seam.t": "Seam",
    "g.seam.e": "A dependency between ARTs or solutions where pressure shows — within a solution or between value streams",
    "g.register.t": "Register",
    "g.register.e": "A list per solution: risks, dependencies, assumptions, NFR, runway, SLO, DORA, capabilities, themes, flow problems …",
    "g.stand.t": "Stand",
    "g.stand.e": "A frozen snapshot of the situation picture at a date; stands lie 14 days apart",
    "g.seed.t": "Seed",
    "g.seed.e": "Start value of the random generator — same seed, same output",
    "g.solution.t": "Solution",
    "g.solution.e": "A group of ARTs delivering one solution together; in the data room the level with its own registers",
    "g.stage_map.t": "Stage map",
    "g.stage_map.e": "A solution's own grouping of the workflow stages (say lead-in/implementation/done) instead of the default path",
    "g.value_stream.t": "Value stream",
    "g.value_stream.e": "The flow from need to value; represented in the data room by the solutions",
    "g.workflow.t": "Workflow",
    "g.workflow.e": "Ordered sequence of stages an issue passes through; described as a text file",
    "g.realism.t": "Realism",
    "g.realism.e": "Degree of untidiness in the status paths: skips, cancels, parking, loops, reopening",
    "g.cfd.t": "CFD",
    "g.cfd.e": "Cumulative Flow Diagram — stock per stage over time, cumulated",
}

_M["ro"] = {
    # 1 -------------------------------------------------------------------
    "c1.h": "1  Ce este Generatorul de date de test?",
    "c1.p1": "<b>Generatorul de date de test</b> produce date inventate, dar realiste, pentru "
             "SituationReport — ca să poți demonstra, învăța și testa raportul de portofoliu, "
             "briefingul delta, mapa de conferință și registrele fără să atingi date reale de "
             "proiect. Nu apar persoane; același seed dă același spațiu de date.",
    "c1.p2": "Generatorul are două căi. <b>Spațiul de date</b> este calea implicită a versiunii beta: "
             "în trei pași se construiește un folder de portofoliu complet, cu structură, poveste, "
             "exporturi Jira per ART, registre, date brute ale providerilor, o serie de stări și "
             "briefingurile delta gata redate. <b>ART-ul singular</b> este calea clasică: un fișier "
             "de export Jira dintr-un fișier de flux de lucru, cu toate reglajele pentru cycle time "
             "și modele de flux (capitolul 8).",
    "c1.ways": "<b>Ce cale, când?</b><br/>"
               "- <b>Spațiu de date (fereastră sau browser):</b> instruire, prezentare, tutoriale, "
               "teste ale lanțului de portofoliu — tot ce are nevoie de o imagine a situației completă.<br/>"
               "- <b>ART singular:</b> un export Jira pentru transform_data și build_reports, modele de "
               "flux țintite pentru instruirea pe scatterplot-uri de cycle time, continuarea unui extras anterior.",
    "c1.p3": "Acest manual descrie mai întâi spațiul de date (capitolele 2–7) și apoi generatorul "
             "clasic pentru un singur ART (capitolul 8). Cine vrea doar minutul până la primul raport "
             "de portofoliu ia tutorialul „Spațiu de date demo într-un minut” "
             "(docs/tutorials/demo-data-room.md, și ca PDF).",
    "c1.uses": "<b>Utilizări tipice:</b><br/>"
               "- <b>Testarea unei instalări noi:</b> rulează lanțul de la datele brute până la raportul de portofoliu?<br/>"
               "- <b>Demonstrații și prezentări:</b> o situație cu valoare aberantă, sursă slabă și cusături, fără întrebări de confidențialitate<br/>"
               "- <b>Instruire:</b> aceeași poveste pentru toți participanții, reproductibilă prin seed<br/>"
               "- <b>Dezvoltare:</b> test de stres cu structură mare (amploare L, până la 49 de ART-uri)",
    "c1.beta": "Stare: beta, octombrie 2026. Interfața spațiului de date este nouă; fila pentru "
               "profilurile per ART din interfață lipsește încă (linia de comandă: --art-profiles).",

    # 2 -------------------------------------------------------------------
    "c2.h": "2  Pornire",
    "c2.pkg.h": "2.1  Pachet portabil (recomandat)",
    "c2.pkg.p": "Pachetul portabil include Python — nimic de instalat. După dezarhivare, patru fișiere "
                "de pornire pentru generator sunt pregătite:",
    "c2.pkg.col_file": "Fișier de pornire (Windows)",
    "c2.pkg.col_what": "Ce deschide",
    "c2.pkg.window": "<b>Spațiul de date ca fereastră</b> — calea implicită. Trei pași, niciun port de "
                     "rețea, rulează și pe calculatoarele de firmă.",
    "c2.pkg.launcher": "Launcher-ul cu toate modulele; conține cardurile „Spațiu de date (fereastră)” și "
                       "„Spațiu de date (browser)”, precum și „Testdata Generator” pentru ART-ul singular.",
    "c2.pkg.browser": "<b>Spațiul de date în browser</b> — aceiași trei pași ca pagină web. Pornește un "
                      "server local pe 127.0.0.1 cu o cheie aleatoare în link. Doar pe calculatoare "
                      "private: software-ul de securitate de pe calculatoarele de firmă blochează și raportează serverele locale.",
    "c2.pkg.single": "<b>ART singular</b> — fereastra clasică cu fișier de flux de lucru, reglaje și "
                     "modele de flux (capitolul 8).",
    "c2.pkg.unix": "macOS: aceleași nume ca .command (clic dreapta → Deschide). Linux: ca .sh (sunt "
                   "necesare python3 și python3-tk). Prima pornire configurează o dată un mediu "
                   "Python — pentru asta e nevoie de internet.",
    "c2.pkg.defender": "Notă pentru Windows: dacă pornirea anunță că Python nu este găsit, Windows a "
                       "blocat fișierul ZIP. Clic dreapta pe ZIP → Proprietăți → Securitate → "
                       "Deblocare → OK → dezarhivați din nou.",
    "c2.src.h": "2.2  Din codul sursă (necesită Python)",
    "c2.src.p": "Cele trei interfețe corespund la trei apeluri: fereastră, browser, ART singular.",
    "c2.wvb.h": "2.3  Fereastră sau browser?",
    "c2.wvb.p": "Ambele arată aceiași trei pași cu aceleași setări și produc același spațiu de date. "
                "Fereastra este o fereastră de program obișnuită (tkinter) și nu are nevoie de nimic "
                "altceva. Pagina de browser este puțin mai comod de citit, dar rulează printr-un server "
                "local — pe un calculator de firmă, securitatea endpoint a blocat și raportat acest "
                "lucru la primul test. De aceea: fereastra mai întâi, browserul doar privat.",
    "c2.lang.h": "2.4  Limbi",
    "c2.lang.p": "Interfața, povestea, README, progresul, jurnalul și briefingurile delta generate există "
                 "în germană, engleză, română, portugheză și franceză. Generatorul pornește în limba "
                 "setată în launcher; comutatorul din dreapta sus al ferestrei și al paginii o schimbă — "
                 "intrările se păstrează. O rulare are o singură limbă: interfața și textele generate "
                 "coincid. Fără setare în launcher și fără " + _c("--lang") + " limba este engleza. "
                 "Româna, portugheza și franceza sunt schițe care urmează să fie verificate de vorbitori nativi.",

    # 3 -------------------------------------------------------------------
    "c3.h": "3  Spațiul de date în trei pași",
    "c3.p": "Fereastra și pagina de browser conduc prin trei pași: <b>Scenariu</b> (ce situație), "
            "<b>Amploare &amp; surse</b> (cât de mare, cât de lung, cât de real) și <b>Generare</b> "
            "(unde, și start). Valorile implicite produc situația demo pe care o folosesc și "
            "tutorialele și manualele modulelor de portofoliu.",
    "c3.fig": "Fig. 1: Pasul 1 „Scenariu” în fereastra spațiului de date — șabloane în stânga, "
              "evenimente dedesubt, structură în dreapta (interfață germană)",
    "c3.s1.h": "3.1  Pasul 1 — Scenariu",
    "c3.s1.p": "În stânga alegi un <b>șablon</b> al poveștii. Evenimentele se leagă de rolurile "
               "structurii din dreapta — valoare aberantă, sursă slabă, cusături — nu de nume fixe.",
    "c3.s1.col_tpl": "Șablon",
    "c3.s1.col_tells": "Ce povestește",
    "c3.s1.col_stands": "Stări",
    "tpl.calm": "Calm",
    "tpl.calm.desc": "Fără răsturnări, toate echipele în limite. Pentru prima instruire și pentru "
                     "citirea unei imagini liniștite. Cine dă alarma aici a citit greșit imaginea.",
    "tpl.standard": "Situație standard",
    "c3.s1.rec": "(recomandat)",
    "tpl.standard.desc": "Valoare aberantă, sursă slabă, încălcare SLO și modele tăcute de la început; "
                         "răsturnările vin cu ultima stare. Pentru prezentări și tutoriale.",
    "tpl.escalation": "Escaladare",
    "tpl.escalation.desc": "Presiunea crește stare cu stare: încălcare SLO devreme, cusătură blocată la "
                           "mijloc, degradare și cusături cross-solution târziu. Pentru exercițiul de conferință.",
    "tpl.recovery": "Recuperare",
    "tpl.recovery.desc": "Începe prost și se vindecă: cusături rezolvate, SLO ține, valoarea aberantă "
                         "își găsește ritmul. Pentru briefingul delta: ce s-a schimbat?",
    "c3.s1.events": "<b>Evenimentele șablonului.</b> Tabelul de dedesubt arată, pentru fiecare "
                    "eveniment, când se aplică (toate stările, de la starea n, ultima stare), ce se "
                    "întâmplă și ca ce devine vizibil în raport. Fiecare eveniment are o bifă; "
                    "evenimentele oprite lipsesc din spațiul de date. Un eveniment a cărui condiție "
                    "este oprită rămâne oprit, cu o notă. Fereastra unui eveniment urmează numărul de "
                    "stări din pasul 2. Capitolul 5 explică cele zece evenimente.",
    "c3.s1.structure": "<b>Structura spațiului de date (dreapta).</b> Un șablon de structură — Mic "
                       "(1 portofoliu · 1 soluție · 2 ART-uri), Standard (1 · 2 · câte 3), Mare "
                       "(5 portofolii · 3–4 soluții · 1–6 ART-uri) — sau una proprie: adaugi sau "
                       "elimini portofolii și soluții, numeri ART-urile per soluție, schimbi numele "
                       "(numele ART-urilor urmează soluția). Per soluție alegi fluxul de lucru clasic "
                       "sau o stage map proprie. Cel puțin un ART per soluție.",
    "c3.s1.yields": "<b>Ce se produce.</b> Caseta din dreapta jos ține socoteala: exporturi Jira, "
                    "registre de lucru, registre, stări și briefinguri delta pentru structura aleasă "
                    "(standard: 6 exporturi, 18 registre de lucru, 22 registre, 6 stări, 5 delte). De "
                    "la 30 de ART-uri avertizează: generarea durează atunci simțitor mai mult.",
    "c3.s2.h": "3.2  Pasul 2 — Amploare &amp; surse",
    "c3.s2.p": "Valorile implicite sunt suficiente pentru instruire și prezentare.",
    "c3.s2.col_setting": "Setare",
    "c3.s2.col_default": "Implicit",
    "c3.s2.col_meaning": "Semnificație",
    "ui.stands": "Stări",
    "ui.scale": "Amploare",
    "ui.realism": "Realism",
    "ui.seed": "Seed",
    "ui.reference": "Ultima stare",
    "ui.lang": "Limba textelor",
    "c3.s2.stands": "2 până la 12 stări la distanță de 14 zile; fiecare stare este un snapshot "
                    "înghețat, fiecare pereche consecutivă un briefing delta gata redat. Șablonul "
                    "„Calm” propune 3.",
    "c3.s2.scale": "S = doar ancorele poveștii, registre scurte; M = registre realiste; L = test de "
                   "stres cu registre pline (heatmap densă, matrice roadmap completă). Ancorele și "
                   "poveștile lor sunt identice la orice nivel.",
    "c3.s2.realism": "Dezordinea traseelor de stare: salturi, anulări, parcări, bucle, redeschideri. "
                     "0 = neted, 100 = ca în realitate; 60 este un ART tipic.",
    "c3.s2.seed": "Același seed, aceeași structură și aceeași dată de referință dau același spațiu de "
                  "date — ideal când toți participanții trebuie să vadă același lucru.",
    "c3.s2.today": "azi",
    "c3.s2.reference": "Data ultimei stări; celelalte sunt cu câte 14 zile înainte. Semaforul de "
                       "calitate al raportului de portofoliu consideră astfel datele actuale.",
    "c3.s2.ui_lang": "limba interfeței",
    "c3.s2.lang": "Limba poveștii, a README și a briefingurilor delta; urmează interfața.",
    "c3.s2.details": "<b>Detalii pentru analiști.</b> Cycle time, modelele de flux și lungimea PI pot fi "
                     "suprascrise per ART — aceleași reglaje ca la ART-ul singular. În această versiune "
                     "beta se face din linia de comandă cu " + _c("--art-profiles FIȘIER.json") +
                     " (capitolul 6); tabelul din interfață urmează odată cu fila ART.",
    "c3.s2.sources": "<b>Surse livrate împreună.</b> Întotdeauna incluse: exporturi Jira per ART (fără "
                     "persoane), răspunsuri SLO Prometheus, deployments/PR-uri/incidente GitHub pentru "
                     "prima soluție, valori zilnice DORA GitLab pentru a doua, măsuri de calitate "
                     "SonarQube și un CSV SLO pentru calea manuală — date brute în formatul fiecărui "
                     "sistem, cu aceleași numere ca în registre, astfel încât " + _c("sources fetch") +
                     " rulează în spațiul de date fără rețea.",
    "c3.s2.ai": "<b>Schițe AI (comutator, implicit oprit).</b> Un briefing vorbit mock, trei răspunsuri, "
                "un pachet de prompt și un răspuns de exercițiu cu numere greșite ajung în ai_drafts/ — "
                "toate cu marcaj AI, niciunul aprobat. Cu ele exersezi aprobarea și " + _c("llm check") +
                " fără să instalezi un model.",
    "c3.s2.estimate": "Linia <b>Estimare</b> de la final numește exporturile Jira, registrele, stările și "
                      "deltele pentru setările tale; subsolul rezumă șablonul, amploarea, stările, "
                      "realismul și seed-ul.",
    "c3.s3.h": "3.3  Pasul 3 — Generare",
    "c3.s3.target": "<b>Folderul țintă.</b> Este creat. Dacă nu este gol, generatorul întreabă — "
                    "„Generează oricum” suprascrie fișierele cu același nume, „Alege alt folder” se "
                    "întoarce. „Răsfoiește …” deschide dialogul de foldere; unde nu există, introduci calea.",
    "c3.s3.progress": "<b>Progres.</b> „Generează spațiul de date” pornește nouă pași; fiecare arată "
                      "în curs, gata sau sărit, cu un detaliu. Durata este de la secunde la minute, în "
                      "funcție de amploare (situația standard circa 10 secunde).",
    "c3.s3.col_step": "Pas",
    "c3.s3.col_makes": "Ce se produce",
    "step.story": "Structură și poveste",
    "step.arts": "Exporturi Jira și registre de lucru",
    "step.registers": "Registre",
    "step.configs": "Configurații",
    "step.sources": "Date brute ale providerilor",
    "step.readme": "README",
    "step.stands": "Seria de stări",
    "step.deltas": "Briefinguri delta",
    "step.ai_drafts": "Schițe AI (mock)",
    "c3.s3.st.story": "structure.json și story.json: roluri legate, evenimente fixate",
    "c3.s3.st.arts": "per ART un export Jira sub raw/ și IssueTimes/Transitions/CFD sub solutions/…/arts/",
    "c3.s3.st.registers": "per soluție registrele (riscuri, dependențe, NFR, SLO, DORA, capabilități, teme …)",
    "c3.s3.st.configs": "portfolio.json, solution.json per soluție, pi_config.json",
    "c3.s3.st.sources": "sources/&lt;soluție&gt;/ cu fișiere replay și configurații sources",
    "c3.s3.st.readme": "README.md cu structură, poveste, stări și alte căi",
    "c3.s3.st.stands": "snapshots/snapshot_&lt;nn&gt;_&lt;data&gt;.json per stare, stands.json, prev/now",
    "c3.s3.st.deltas": "deltas/delta_&lt;nn&gt;-&lt;nn+1&gt;.md și .html per pereche consecutivă",
    "c3.s3.st.ai_drafts": "ai_drafts/ — doar cu comutatorul, altfel „sărit”",
    "c3.s3.cancel": "<b>Anulare</b> oprește după pasul în curs; folderul conține ce s-a construit până "
                    "atunci. O eroare apare cu mesajul ei în listă.",
    "c3.s3.result": "<b>Cardul de rezultat.</b> După ultimul pas apare „Spațiu de date gata” cu durata "
                    "și seed-ul, patru cifre (elemente și ART-uri, registre și soluții, stări, tipuri "
                    "de surse), povestea în trei propoziții și butoane: Deschide raportul de "
                    "portofoliu, Mapa de conferință, Ultimul delta, README, Deschide folderul, Schițe "
                    "AI (dacă au fost generate). Rapoartele se redau la primul clic și se deschid în browser.",
    "c3.s3.compare": "<b>Compară delta.</b> Alegi două stări (de pildă 3 → 4) și „Deschide briefingul "
                     "delta” — toate perechile consecutive sunt gata sub deltas/.",
    "c3.s3.after": "<b>Apoi.</b> „Spațiu de date nou cu alt șablon …” sare înapoi la pasul 1; linia de "
                   "dedesubt arată comanda de continuare (capitolul 7).",

    # 4 -------------------------------------------------------------------
    "c4.h": "4  Ce se află în folder",
    "c4.p": "Folderul țintă este un <b>spațiu de date de portofoliu</b>: toate căile din configurații "
            "sunt relative la fișierul de configurare. Folderul poate fi mutat, copiat sau arhivat ca întreg.",
    "c4.col_path": "Cale",
    "c4.col_content": "Conținut",
    "c4.structure": "Structura ca date: portofolii → soluții → ART-uri, flux de lucru per soluție",
    "c4.story": "Povestea ca date: șablon, roluri legate, evenimente cu comutator și fereastră de stări, note",
    "c4.readme": "Descrierea structurii, poveștii, stărilor, surselor și a altor căi — în limba rulării",
    "c4.portfolio": "Punct de intrare: configurația de portofoliu peste toate soluțiile",
    "c4.pi": "Intervalele PI peste perioada datelor",
    "c4.solutions": "per soluție solution.json (stage_map proprie unde a fost aleasă), arts/ cu IssueTimes, Transitions și CFD per ART, registers/ cu registrele sub nume standard",
    "c4.raw": "Exporturi Jira per ART în format REST API — totodată material demo pentru get_data",
    "c4.sources": "Date brute ale providerilor ca fișiere replay (Prometheus, GitHub sau GitLab, SonarQube, CSV) plus configurații sources",
    "c4.snapshots": "snapshot_&lt;nn&gt;_&lt;data&gt;.json per stare, index stands.json, snapshot_prev/now.json = ultimele două",
    "c4.deltas": "delta_&lt;nn&gt;-&lt;nn+1&gt;.md și .html per pereche consecutivă — gata redate",
    "c4.ai_drafts": "doar cu comutatorul: briefing vorbit mock, răspunsuri, pachet de prompt, răspuns de exercițiu — toate cu marcaj AI",
    "c4.use": "Folderul este direct utilizabil — raport de portofoliu, briefing delta al oricărei perechi, "
              "mapă de conferință, " + _c("sources fetch") + " fără rețea pe fișierele replay (în "
              "sources/&lt;soluție&gt;/) și verificarea exportului din get_data:",
    "c4.multi": "Cu mai multe portofolii (șablonul „Mare” sau structură proprie), fiecare portofoliu "
                "devine propriul spațiu de date într-un subfolder; un README în folderul principal "
                "trimite la ele. O imagine a situației peste mai multe portofolii nu este azi o "
                "funcție — datele pentru ea stau deja una lângă alta.",

    # 5 -------------------------------------------------------------------
    "c5.h": "5  Înțelegerea poveștii",
    "c5.p": "Fiecare șablon povestește aceeași situație din toate registrele: riscurile, dependențele, "
            "ipotezele, SLO-urile și alarmele arată spre aceleași locuri. Evenimentele se leagă de "
            "<b>roluri</b> care decurg din structură — așa povestea rămâne coerentă și cu structura ta.",
    "c5.roles": "<b>Rolurile:</b><br/>"
                "- <b>Prima soluție</b> („gazda”): pare sănătoasă, poartă modelele tăcute; <b>ultimul ei "
                "ART este valoarea aberantă</b>; între ART-urile ei stau dependența blocată și cusătura recurentă.<br/>"
                "- <b>A doua soluție:</b> <b>ultimul ei ART este sursa slabă de date</b>; aici „Order Sync "
                "API” își încalcă SLO-ul și apare noul risc de securitate.<br/>"
                "- <b>Cusătura cross-solution:</b> primul ART al celei de-a doua soluții depinde de primul "
                "ART al primei — vizibil doar în raportul de portofoliu.<br/>"
                "- Alte soluții și portofolii primesc setul de bază generat de seed, fără ancore de poveste.",
    "c5.notices": "Ce nu oferă structura dispare cu o <b>notă</b> (în pasul 1 și în story.json): cu o "
                  "singură soluție nu există sursă slabă, încălcare SLO și cusătură cross-solution; dacă "
                  "prima soluție are un singur ART, lipsesc valoarea aberantă, dependența blocată și "
                  "cusătura recurentă. Cele zece evenimente:",
    "c5.col_id": "Nr.",
    "c5.col_what": "Ce se întâmplă",
    "c5.col_visible": "Vizibil ca",
    "ev.E1.title": "ART-ul aberant are cam de trei ori cycle time-ul.",
    "ev.E1.effect": "Raport de comparație: mediană/P95 roșu; alarma „P85 peste 30 de zile” declanșată; imaginea livrării rară și lentă; o capabilitate at risk.",
    "ev.E2.title": "Sursa slabă livrează date slabe: fără CFD, aproape fără first dates, date vechi de 60 de zile.",
    "ev.E2.effect": "Încredere medium; un risc îmbătrânește (50 de zile); o capabilitate critică; o problemă de flux supraviețuiește patru conferințe; o ipoteză depășește data de revizuire; DORA/calitate low.",
    "ev.E3.title": "Dependența dintre două ART-uri ale primei soluții este blocată și întârziată.",
    "ev.E3.effect": "Dependență at_risk → blocked; heatmap roșu; alarma „două blocate” chiar sub prag.",
    "ev.E4.title": "Cusătura cross-solution intră sub presiune; value stream-urile trag unul de altul.",
    "ev.E4.effect": "Mai multe dependențe alunecă din on_track prin at_risk în blocked — vizibil doar în raportul de portofoliu; baza indicatorului punctelor de decizie.",
    "ev.E5.title": "Aceeași cusătură deschide a treia oară o solution area pe același subiect (mediu de test).",
    "ev.E5.effect": "Două solution areas închise, una nouă — semnalul EA: verifică tăietura sau arhitectura, nu echipele.",
    "ev.E6.title": "„Order Sync API” din a doua soluție își încalcă SLO-ul.",
    "ev.E6.effect": "Registrul SLO: breached; NFR „API response time” încălcat; o lacună de runway întârziată.",
    "ev.E7.title": "Prima soluție pare sănătoasă — cu modelele tăcute.",
    "ev.E7.effect": "Un risc owned de 45 de zile (aging); o temă fără epic („declared &amp; forgotten”); o problemă de flux supraviețuiește trei conferințe; o capabilitate fără ART; SLO „Checkout” at risk.",
    "ev.E8.title": "Calitatea datelor sursei slabe se degradează în continuare.",
    "ev.E8.effect": "Ponderea elementelor fără first date urcă la 80 % — încredere medium → low, acoperirea vizibilă în titlu.",
    "ev.E9.title": "Risc nou în a doua soluție: security review neprogramat.",
    "ev.E9.effect": "Apare un risc înalt, mitigat — nou în briefingul delta.",
    "ev.E10.title": "Roadmap-uri actualizate.",
    "ev.E10.effect": "Un epic își pierde tema (inițiativă zombie); un epic al celei de-a doua soluții este tras de la P2 la P1.",
    "c5.windows": "<b>Ferestre de stări.</b> Fiecare șablon stabilește în ce stări se aplică un eveniment. "
                  "Situație standard: valoarea aberantă, sursa slabă, încălcarea SLO și modelele tăcute în "
                  "toate stările, răsturnările (blocaj, cusături, degradare, risc nou, roadmap-uri) doar în "
                  "ultima. Escaladarea le eșalonează pe serie, Recuperarea le inversează: starea 1 arată "
                  "tot, apoi se vindecă una după alta. README-ul spațiului de date listează fereastra "
                  "fiecărui eveniment; înainte și după, seria arată situația fără el.",

    # 6 -------------------------------------------------------------------
    "c6.h": "6  Spațiul de date în linia de comandă",
    "c6.p": "Tot ce e în cei trei pași există și ca opțiune a " +
            _c("python -m testdata_generator --scenario portfolio") + ". Înainte de construire, linia de "
            "comandă afișează structura, comutatoarele și estimarea; după, folderul, stările și durata.",
    "c6.col_opt": "Opțiune",
    "c6.col_default": "Implicit",
    "c6.col_meaning": "Semnificație",
    "c6.folder_word": "FOLDER",
    "c6.required": "(obligatoriu)",
    "c6.scenario": "Generează un spațiu de date în loc de un ART singular",
    "c6.output": "Folderul țintă (este creat)",
    "c6.structure": "Șablon de structură sau structure.json propriu (portofolii → soluții → ART-uri, flux de lucru per soluție)",
    "c6.arts": "Un portofoliu din numărul de ART-uri per soluție, de ex. 3,4s,1 — trei soluții cu 3, 4 și 1 ART-uri; un s final dă soluției o stage map proprie. Nu se combină cu --structure.",
    "c6.story": "Șablonul poveștii (calm, standard, escalation, recovery)",
    "c6.event": "Pornește sau oprește un eveniment, de ex. --event E3=off --event E9=on; repetabil. Un eveniment a cărui condiție este oprită rămâne oprit, cu o notă.",
    "c6.stands_default": "6 (calm 3)",
    "c6.stands": "Numărul de stări (2–12), la 14 zile, ultima la data de referință; fiecare pereche consecutivă primește un briefing delta sub deltas/",
    "c6.scale": "Volumul registrelor per soluție: s = doar ancore, m = demo realist, l = test de stres",
    "c6.seed_default": "(aleator)",
    "c6.seed": "Seed pentru ieșire reproductibilă; interfața folosește 42",
    "c6.art_profiles": "Reglaje per ART ca JSON, de ex. {\"Alpha-1\": {\"mean_cycle_days\": 30, \"pattern\": \"cluster\", \"pattern_strength\": 80}}. Câmpuri: issue_count, mean_cycle_days, std_cycle_days, completion_rate, todo_rate, backflow_prob, pattern, pattern_strength, pi_duration_weeks, realism. Suprascrierile se aplică în toate stările; restul își păstrează valoarea din poveste.",
    "c6.off": "oprit",
    "c6.ai_drafts": "Scrie schițe AI mock cu marcaj în ai_drafts/",
    "c6.lang_default": "limba suitei, altfel en",
    "c6.lang": "Limba interfeței, a consolei și a textelor generate",
    "c6.continue": "Continuă un spațiu de date existent până la dată (capitolul 7)",
    "c6.web": "Pornește interfața în browser: server local pe 127.0.0.1 (port 0 = aleator liber), cheie de acces în link; --no-browser afișează doar linkul. Se încheie cu Ctrl+C.",
    "c6.dataspace": "Pornește fereastra spațiului de date — aceiași trei pași fără server",
    "c6.ex.h": "Exemple",
    "c6.ex.1": "Situație standard, ca în tutorial și manuale",
    "c6.ex.2": "Escaladare pe opt stări, test de stres, texte în germană",
    "c6.ex.3": "Structură proprie, un eveniment oprit, exercițiu AI pornit",
    "c6.ex.4": "Cinci portofolii, 49 de ART-uri — durează simțitor",
    "c6.hint_default_lang": "Fără --lang și fără setare în launcher, consola și textele generate sunt în "
                            "engleză. Pentru română, dați --lang ro sau schimbați launcher-ul.",

    # 7 -------------------------------------------------------------------
    "c7.h": "7  Continuarea unui spațiu de date",
    "c7.p1": "Un spațiu de date poate fi continuat până la o dată ulterioară — ca un al doilea extras "
             "din Jira: trecutul rămâne, elementele deschise merg mai departe, altele noi se adaugă.",
    "c7.p2": "Generatorul continuă pe loc exporturile Jira, IssueTimes/Transitions/CFD, configurațiile și "
             "configurația PI; vechiul snapshot_now devine snapshot_prev, noua stare snapshot_now, iar "
             "README primește o notă cu vechea și noua dată de referință și numărul de elemente noi. "
             "Registrele rămân neschimbate. Reglajele vin din înregistrarea generatorului din fișiere; "
             "limba urmează " + _c("--lang") + ".",
    "c7.hint": "Cardul de rezultat arată comanda potrivită sub „Apoi”. Pentru un singur export Jira "
               "există --continue OLD.json (capitolul 8).",

    # 8 -------------------------------------------------------------------
    "c8.h": "8  Un singur ART (generatorul clasic)",
    "c8.p": "Calea clasică produce <b>un</b> fișier de export Jira în format REST API dintr-un fișier de "
            "flux de lucru: elementele trec prin stadii, zăbovesc timp variabil, cad ocazional înapoi și "
            "se închid cu o rată reglabilă. Fișierul intră direct în transform_data și build_reports. "
            "Reglajele pentru cycle time și modele de flux sunt aceleași pe care spațiul de date le "
            "suprascrie per ART prin --art-profiles.",
    "c8.win.h": "8.1  Fereastra",
    "c8.win.p": "TestdataGenerator.bat (sau " + _c("python -m testdata_generator") + " fără opțiuni) "
                "deschide fereastra cu câmpuri pentru toți parametrii. Doar fișierul de flux de lucru "
                "este obligatoriu; restul are valori implicite. Zona „Portofoliu demo” de jos "
                "construiește situația standard la un clic — spațiul de date din capitolul 3 poate mai mult.",
    "c8.win.fig": "Fig. 2: Fereastra generatorului clasic pentru un singur ART",
    "c8.wf.h": "8.2  Fișierul de flux de lucru",
    "c8.wf.p": "Fișierul de flux de lucru definește stadiile board-ului Jira și este singurul câmp "
               "obligatoriu. Are același format ca în transform_data — un fișier servește ambele module. "
               "Fiecare linie descrie un stadiu; aliasurile (nume alternative de stare în exportul Jira) "
               "se separă prin două puncte. Două linii speciale marchează începutul și sfârșitul lucrului activ:",
    "c8.wf.pre": "NumeCanonic:Alias1:Alias2\n<First>PrimulStadiuActiv\n<Closed>StadiuÎnchis",
    "c8.wf.col_line": "Linie",
    "c8.wf.col_meaning": "Semnificație",
    "c8.wf.alias": "Stadiu cu unul sau mai multe nume alternative de stare Jira",
    "c8.wf.plain_name": "Nume (fără :)",
    "c8.wf.plain": "Stadiu fără aliasuri",
    "c8.wf.first": "Primul stadiu activ — aici începe cycle time",
    "c8.wf.closed": "Stadiu închis — marchează un element ca finalizat",
    "c8.wf.example": "Exemplul livrat " + _c("workflow_ART_A.txt") + " modelează un flux SAFe ART tipic:",
    "c8.wf.notes": "„Funnel” are patru aliasuri — toate cele patru stări Jira se normalizează la Funnel. "
                   "Analysis este primul stadiu activ (cycle time începe aici). Releasing contează ca "
                   "închis; Done (după Releasing) preia și elementele anulate.",
    "c8.par.h": "8.3  Referință parametri",
    "c8.par.p": "Toți parametrii există în fereastră și în linia de comandă.",
    "c8.par.col_param": "Parametru",
    "c8.par.col_default": "Implicit",
    "c8.par.col_desc": "Descriere",
    "c8.par.workflow": "Fișier de definire a fluxului de lucru (.txt)",
    "c8.par.output": "Calea fișierului de ieșire",
    "c8.par.project": "Cheia proiectului Jira al elementelor generate",
    "c8.par.issues": "Numărul de elemente",
    "c8.par.from": "Cea mai timpurie dată de creare",
    "c8.par.to": "Cea mai târzie dată de tranziție",
    "c8.par.types": "Tipuri de elemente cu ponderi (suma nu trebuie să fie 1)",
    "c8.par.completion": "Ponderea elementelor care ating stadiul închis (0–1)",
    "c8.par.todo": "Ponderea elementelor deschise care rămân în stadii timpurii (0–1)",
    "c8.par.backflow": "Probabilitatea unui pas înapoi per tranziție (0–1)",
    "c8.par.realism": "Dezordinea traseelor de stare: salturi, anulări, parcări, bucle, redeschideri; circa 70 ca un ART real",
    "c8.par.seed": "Seed pentru ieșire reproductibilă",
    "c8.par.mean": "Cycle time mediu în zile (lognormal); activează controlul cycle time",
    "c8.par.std_default": "30 % din medie",
    "c8.par.std": "Abaterea standard a cycle time în zile",
    "c8.par.pattern": "Model de flux: none / triangle / flat_triangle / cluster / batch (vezi 8.4)",
    "c8.par.pi": "Lungimea PI în săptămâni (pentru cluster și batch)",
    "c8.par.strength": "Intensitatea modelului (0 = subtil, 50 = implicit, 100 = puternic)",
    "c8.par.continue": "Continuă un extras anterior până la --to-date: trecutul rămâne byte cu byte, elementele deschise merg mai departe, altele noi se adaugă; necesită --workflow",
    "c8.par.learn": "Învață un profil de tranziție dintr-un fișier real de tranziții (doar numărători și ore); --transition-profile generează cu el",
    "c8.pat.h": "8.4  Modele de flux",
    "c8.pat.p": "Generatorul simulează anti-modele de flux tipice din literatura lui Vacanti și Singh. "
                "Combinați --mean-cycle-days cu --pattern; fereastra oferă butoane radio și glisoare.",
    "c8.pat.col_pattern": "Model",
    "c8.pat.col_look": "Scatterplot",
    "c8.pat.col_desc": "Descriere",
    "c8.pat.none.look": "Nor de puncte uniform",
    "c8.pat.none.desc": "Cycle time aleator fără tendință — comportament implicit",
    "c8.pat.triangle.look": "Triunghi, unghi drept jos dreapta",
    "c8.pat.triangle.desc": "Cycle time crește liniar în timp (circa 1–4× la intensitate implicită). Un proces care încetinește tot mai mult.",
    "c8.pat.flat.look": "Triunghi, creșterea se aplatizează",
    "c8.pat.flat.desc": "Ca triangle, creșterea se aplatizează spre final. O deteriorare care se stabilizează.",
    "c8.pat.cluster.look": "Aglomerări verticale la finalul PI",
    "c8.pat.cluster.desc": "Cycle time rămâne stabil, dar majoritatea elementelor se închid în ultimele două săptămâni înainte de finalul PI. Comportament dictat de termen.",
    "c8.pat.batch.look": "Coloane de înălțime variabilă la finalul PI",
    "c8.pat.batch.desc": "Ca cluster, dar cu cycle time foarte variabil (0,1× până la 3× media). Sarcini scurte și foarte lungi sunt împinse împreună la finalul PI.",
    "c8.pat.hint": "--pattern necesită --mean-cycle-days; fără el modelul este ignorat. "
                   "--std-cycle-days controlează dispersia, --pi-duration-weeks lungimea PI pentru cluster și batch.",
    "c8.ex.h": "8.5  ART_A — exemplu complet",
    "c8.ex.p": "De la generator la raportul finit pe proiectul fictiv ART_A:",
    "c8.ex.s1": "Pasul 1: Generare date de test",
    "c8.ex.s2": "Pasul 2: Procesare cu transform_data",
    "c8.ex.s3": "Pasul 3: Creare raport cu build_reports",
    "c8.ex.expect": "<b>La ce să te aștepți (seed 42, 200 de elemente):</b><br/>"
                    "- Chei ART_A-0001 până la ART_A-0200<br/>"
                    "- Tipuri circa 120 Feature, 40 Bug, 40 Enabler<br/>"
                    "- Circa 150 de elemente în Releasing sau Done<br/>"
                    "- Date de creare răspândite pe 2025<br/>"
                    "- Pași înapoi ocazionali (backflow-prob 0.08 = circa 8 %)",

    # 9 -------------------------------------------------------------------
    "c9.h": "9  Întrebări frecvente",
    "c9.q1": "Fereastră sau browser — ce să folosesc?",
    "c9.a1": "Fereastra. Produce același spațiu de date și nu deschide niciun port de rețea. Pagina de "
             "browser doar pe un calculator privat; pe calculatoarele de firmă software-ul de securitate "
             "blochează și raportează serverele locale.",
    "c9.q2": "De ce spațiul meu de date este în engleză, deși vorbesc română?",
    "c9.a2": "Fără indicarea limbii, generatorul ia limba suitei din launcher, altfel engleza. Setați "
             "launcher-ul pe română, comutați din dreapta sus sau dați --lang ro.",
    "c9.q3": "Folderul țintă nu este gol — ce se întâmplă?",
    "c9.a3": "Generatorul întreabă. „Generează oricum” suprascrie fișierele cu același nume și lasă restul; "
             "„Alege alt folder” renunță.",
    "c9.q4": "Generarea durează mult.",
    "c9.a4": "De la 30 de ART-uri sau la amploare L cu mai multe portofolii, caseta „Ce se produce” "
             "avertizează. Pentru instruire ajung structura standard și amploarea M (circa 10 secunde).",
    "c9.q5": "Date de test sau date reale?",
    "c9.a5": "Pentru demonstrații, instruire și teste de instalare, datele de test sunt alegerea mai bună "
             "— fără întrebări de confidențialitate. Analizele de flux și deciziile reale au nevoie de "
             "date reale; exportul manual este descris în manualul Get Data.",
    "c9.q6": "Pot seta ART-uri individuale diferit?",
    "c9.a6": "Da, prin --art-profiles FIȘIER.json în linia de comandă (capitolul 6). Fila pentru asta "
             "din interfață urmează într-o versiune beta ulterioară.",

    # 10 ------------------------------------------------------------------
    "c10.h": "10  Glosar",
    "c10.col_term": "Termen",
    "c10.col_expl": "Explicație",
    "g.art.t": "ART",
    "g.art.e": "Agile Release Train — mai multe echipe care livrează împreună în SAFe",
    "g.dataspace.t": "Spațiu de date",
    "g.dataspace.e": "Un folder cu tot ce are nevoie o imagine a situației de portofoliu: configurații, exporturi, registre, stări, briefinguri — de sine stătător și mutabil",
    "g.delta.t": "Briefing delta",
    "g.delta.e": "„Ce s-a schimbat?” între două stări — debit, încredere, cusături, riscuri noi",
    "g.conference.t": "Mapă de conferință",
    "g.conference.e": "Mapa pentru value stream conference: probleme de flux care supraviețuiesc conferințelor, cu imaginea situației",
    "g.seam.t": "Cusătură",
    "g.seam.e": "O dependență între ART-uri sau soluții unde se vede presiunea — în interiorul unei soluții sau între value stream-uri",
    "g.register.t": "Registru",
    "g.register.e": "O listă per soluție: riscuri, dependențe, ipoteze, NFR, runway, SLO, DORA, capabilități, teme, probleme de flux …",
    "g.stand.t": "Stare",
    "g.stand.e": "Un snapshot înghețat al imaginii situației la o dată; stările sunt la 14 zile distanță",
    "g.seed.t": "Seed",
    "g.seed.e": "Valoarea de pornire a generatorului aleator — același seed, aceeași ieșire",
    "g.solution.t": "Soluție",
    "g.solution.e": "Un grup de ART-uri care livrează împreună o soluție; în spațiul de date, nivelul cu registre proprii",
    "g.stage_map.t": "Stage map",
    "g.stage_map.e": "Gruparea proprie a stadiilor fluxului de lucru pentru o soluție (de pildă pregătire/implementare/gata) în locul căii implicite",
    "g.value_stream.t": "Value stream",
    "g.value_stream.e": "Fluxul de la nevoie la valoare; reprezentat în spațiul de date prin soluții",
    "g.workflow.t": "Flux de lucru",
    "g.workflow.e": "Succesiunea ordonată de stadii prin care trece un element; descrisă ca fișier text",
    "g.realism.t": "Realism",
    "g.realism.e": "Gradul de dezordine al traseelor de stare: salturi, anulări, parcări, bucle, redeschideri",
    "g.cfd.t": "CFD",
    "g.cfd.e": "Cumulative Flow Diagram — stocul per stadiu în timp, cumulat",
}

_M["pt"] = {
    # 1 -------------------------------------------------------------------
    "c1.h": "1  O que é o Gerador de dados de teste?",
    "c1.p1": "O <b>Gerador de dados de teste</b> produz dados inventados mas realistas para o "
             "SituationReport — para demonstrar, aprender e testar o relatório de portefólio, o "
             "briefing delta, a pasta de conferência e os registos sem tocar em dados reais de "
             "projeto. Não aparecem pessoas; a mesma seed dá a mesma sala de dados.",
    "c1.p2": "O gerador tem dois caminhos. A <b>sala de dados</b> é o caminho padrão da beta: em três "
             "passos constrói uma pasta de portefólio completa com estrutura, história, exportações "
             "Jira por ART, registos, dados brutos dos fornecedores, uma série de estados e os "
             "briefings delta já renderizados. O <b>ART individual</b> é o caminho clássico: um "
             "ficheiro de exportação Jira a partir de um ficheiro de fluxo de trabalho, com todos os "
             "controlos de cycle time e padrões de fluxo (capítulo 8).",
    "c1.ways": "<b>Que caminho, quando?</b><br/>"
               "- <b>Sala de dados (janela ou browser):</b> formação, apresentação, tutoriais, testes "
               "da cadeia de portefólio — tudo o que precisa de um quadro de situação completo.<br/>"
               "- <b>ART individual:</b> uma exportação Jira para transform_data e build_reports, "
               "padrões de fluxo dirigidos para formação em scatterplots de cycle time, continuação "
               "de uma extração anterior.",
    "c1.p3": "Este manual descreve primeiro a sala de dados (capítulos 2 a 7) e depois o gerador "
             "clássico de ART individual (capítulo 8). Quem só quer o minuto até ao primeiro relatório "
             "de portefólio usa o tutorial «Sala de dados demo num minuto» "
             "(docs/tutorials/demo-data-room.md, também em PDF).",
    "c1.uses": "<b>Utilizações típicas:</b><br/>"
               "- <b>Testar uma instalação nova:</b> a cadeia corre dos dados brutos ao relatório de portefólio?<br/>"
               "- <b>Demonstrações e apresentações:</b> uma situação com outlier, fonte fraca e costuras, sem questões de privacidade<br/>"
               "- <b>Formação:</b> a mesma história para todos os participantes, reprodutível pela seed<br/>"
               "- <b>Desenvolvimento:</b> teste de stress com estrutura grande (escala L, até 49 ARTs)",
    "c1.beta": "Estado: beta, outubro de 2026. A interface da sala de dados é nova; o separador de "
               "perfis por ART na interface ainda falta (linha de comandos: --art-profiles).",

    # 2 -------------------------------------------------------------------
    "c2.h": "2  Arranque",
    "c2.pkg.h": "2.1  Pacote portátil (recomendado)",
    "c2.pkg.p": "O pacote portátil inclui o Python — nada a instalar. Depois de descompactar, quatro "
                "ficheiros de arranque do gerador ficam prontos:",
    "c2.pkg.col_file": "Ficheiro de arranque (Windows)",
    "c2.pkg.col_what": "O que abre",
    "c2.pkg.window": "<b>Sala de dados como janela</b> — o caminho padrão. Três passos, nenhuma porta "
                     "de rede, corre também em computadores de empresa.",
    "c2.pkg.launcher": "O launcher com todos os módulos; traz os cartões «Sala de dados (janela)» e "
                       "«Sala de dados (browser)», além de «Testdata Generator» para o ART individual.",
    "c2.pkg.browser": "<b>Sala de dados no browser</b> — os mesmos três passos como página web. Inicia um "
                      "servidor local em 127.0.0.1 com uma chave aleatória no link. Só em computadores "
                      "privados: o software de segurança dos computadores de empresa bloqueia e reporta servidores locais.",
    "c2.pkg.single": "<b>ART individual</b> — a janela clássica com ficheiro de fluxo de trabalho, "
                     "controlos e padrões de fluxo (capítulo 8).",
    "c2.pkg.unix": "macOS: os mesmos nomes como .command (clique direito → Abrir). Linux: como .sh "
                   "(requer python3 e python3-tk). O primeiro arranque configura uma vez um ambiente "
                   "Python — para isso é precisa internet.",
    "c2.pkg.defender": "Nota para Windows: se o arranque disser que o Python não foi encontrado, o Windows "
                       "bloqueou o ficheiro ZIP. Clique direito no ZIP → Propriedades → Segurança → "
                       "Desbloquear → OK → descompactar de novo.",
    "c2.src.h": "2.2  A partir do código-fonte (requer Python)",
    "c2.src.p": "As três interfaces correspondem a três chamadas: janela, browser, ART individual.",
    "c2.wvb.h": "2.3  Janela ou browser?",
    "c2.wvb.p": "Ambas mostram os mesmos três passos com as mesmas definições e produzem a mesma sala de "
                "dados. A janela é uma janela de programa normal (tkinter) e não precisa de mais nada. A "
                "página do browser é um pouco mais cómoda de ler, mas corre através de um servidor local "
                "— num computador de empresa, a segurança de endpoint bloqueou e reportou isso no primeiro "
                "teste. Por isso: janela primeiro, browser só em privado.",
    "c2.lang.h": "2.4  Idiomas",
    "c2.lang.p": "Interface, história, README, progresso, registo e os briefings delta gerados existem em "
                 "alemão, inglês, romeno, português e francês. O gerador arranca no idioma definido no "
                 "launcher; o seletor no canto superior direito da janela e da página muda-o — as entradas "
                 "mantêm-se. Uma execução tem um idioma: interface e textos gerados coincidem. Sem definição "
                 "no launcher e sem " + _c("--lang") + " o idioma é o inglês. Romeno, português e francês "
                 "são rascunhos ainda por rever por falantes nativos.",

    # 3 -------------------------------------------------------------------
    "c3.h": "3  A sala de dados em três passos",
    "c3.p": "Janela e página do browser conduzem por três passos: <b>Cenário</b> (que situação), "
            "<b>Âmbito &amp; fontes</b> (quão grande, quão longo, quão real) e <b>Gerar</b> (para onde, e "
            "avançar). Os valores padrão produzem a situação demo que os tutoriais e manuais dos módulos "
            "de portefólio também usam.",
    "c3.fig": "Fig. 1: Passo 1 «Cenário» na janela da sala de dados — modelos à esquerda, eventos em "
              "baixo, estrutura à direita (interface alemã)",
    "c3.s1.h": "3.1  Passo 1 — Cenário",
    "c3.s1.p": "À esquerda escolhe um <b>modelo</b> da história. Os eventos ligam-se a papéis da estrutura "
               "à direita — outlier, fonte fraca, costuras — não a nomes fixos.",
    "c3.s1.col_tpl": "Modelo",
    "c3.s1.col_tells": "O que conta",
    "c3.s1.col_stands": "Estados",
    "tpl.calm": "Calmo",
    "tpl.calm.desc": "Sem viragens, todas as equipas dentro dos limites. Para a primeira formação e para "
                     "ler um quadro tranquilo. Quem dá o alarme aqui leu mal o quadro.",
    "tpl.standard": "Situação padrão",
    "c3.s1.rec": "(recomendado)",
    "tpl.standard.desc": "Outlier, fonte fraca, violação de SLO e padrões silenciosos desde o início; as "
                         "viragens chegam com o último estado. Para apresentações e tutoriais.",
    "tpl.escalation": "Escalada",
    "tpl.escalation.desc": "A pressão sobe estado a estado: violação de SLO cedo, costura bloqueada a meio, "
                           "degradação e costuras cross-solution tarde. Para o exercício de conferência.",
    "tpl.recovery": "Recuperação",
    "tpl.recovery.desc": "Começa mal e cura: costuras resolvidas, SLO cumpre, o outlier encontra o seu ritmo. "
                         "Para o briefing delta: o que mudou?",
    "c3.s1.events": "<b>Eventos do modelo.</b> A tabela em baixo mostra, por evento, quando se aplica (todos "
                    "os estados, a partir do estado n, último estado), o que acontece e como se torna "
                    "visível no relatório. Cada evento tem uma caixa de verificação; eventos desligados "
                    "faltam na sala de dados. Um evento cuja condição está desligada fica desligado, com "
                    "uma nota. A janela de um evento segue o número de estados do passo 2. O capítulo 5 "
                    "explica os dez eventos.",
    "c3.s1.structure": "<b>Estrutura da sala de dados (direita).</b> Um modelo de estrutura — Pequena "
                       "(1 portefólio · 1 solução · 2 ARTs), Padrão (1 · 2 · 3 cada), Grande "
                       "(5 portefólios · 3–4 soluções · 1–6 ARTs) — ou uma própria: adicionar ou remover "
                       "portefólios e soluções, contar ARTs por solução, mudar nomes (os nomes dos ARTs "
                       "seguem a solução). Por solução escolhe o fluxo de trabalho clássico ou um stage "
                       "map próprio. Pelo menos um ART por solução.",
    "c3.s1.yields": "<b>O que se produz.</b> A caixa em baixo à direita faz as contas: exportações Jira, "
                    "livros de trabalho, registos, estados e briefings delta para a estrutura escolhida "
                    "(padrão: 6 exportações, 18 livros, 22 registos, 6 estados, 5 deltas). A partir de "
                    "30 ARTs avisa: a geração demora então sensivelmente mais.",
    "c3.s2.h": "3.2  Passo 2 — Âmbito &amp; fontes",
    "c3.s2.p": "Os valores padrão chegam para formação e apresentação.",
    "c3.s2.col_setting": "Definição",
    "c3.s2.col_default": "Padrão",
    "c3.s2.col_meaning": "Significado",
    "ui.stands": "Estados",
    "ui.scale": "Âmbito",
    "ui.realism": "Realismo",
    "ui.seed": "Seed",
    "ui.reference": "Último estado",
    "ui.lang": "Idioma dos textos",
    "c3.s2.stands": "2 a 12 estados com 14 dias de intervalo; cada estado é um snapshot congelado, cada "
                    "par consecutivo um briefing delta pronto. O modelo «Calmo» sugere 3.",
    "c3.s2.scale": "S = só âncoras da história, registos curtos; M = registos realistas; L = teste de "
                   "stress com registos completos (heatmap densa, matriz de roadmap completa). As âncoras "
                   "e as suas histórias são idênticas em qualquer nível.",
    "c3.s2.realism": "Desordem dos percursos de estado: saltos, cancelamentos, estacionamentos, ciclos, "
                     "reaberturas. 0 = liso, 100 = como na realidade; 60 é um ART típico.",
    "c3.s2.seed": "A mesma seed, estrutura e data de referência dão a mesma sala de dados — ideal quando "
                  "todos os participantes devem ver o mesmo.",
    "c3.s2.today": "hoje",
    "c3.s2.reference": "Data do último estado; os outros ficam 14 dias antes, cada um. O semáforo de "
                       "qualidade do relatório de portefólio classifica assim os dados como atuais.",
    "c3.s2.ui_lang": "idioma da interface",
    "c3.s2.lang": "Idioma da história, do README e dos briefings delta; segue a interface.",
    "c3.s2.details": "<b>Detalhes para analistas.</b> Cycle times, padrões de fluxo e duração do PI podem "
                     "ser sobrepostos por ART — os mesmos controlos do ART individual. Nesta beta isso "
                     "faz-se na linha de comandos com " + _c("--art-profiles FICHEIRO.json") +
                     " (capítulo 6); a tabela na interface segue com o separador ART.",
    "c3.s2.sources": "<b>Fontes fornecidas.</b> Sempre incluídas: exportações Jira por ART (sem pessoas), "
                     "respostas SLO do Prometheus, deployments/PRs/incidentes do GitHub para a primeira "
                     "solução, valores diários DORA do GitLab para a segunda, medidas de qualidade do "
                     "SonarQube e um CSV de SLO para o caminho manual — dados brutos no formato de cada "
                     "sistema com os mesmos números dos registos, de modo que " + _c("sources fetch") +
                     " corre na sala de dados sem rede.",
    "c3.s2.ai": "<b>Rascunhos de IA (interruptor, desligado por padrão).</b> Um briefing falado mock, três "
                "respostas, um pacote de prompt e uma resposta de exercício com números errados vão para "
                "ai_drafts/ — todos com a marca de IA, nenhum aprovado. Com eles pratica a aprovação e o " +
                _c("llm check") + " sem instalar um modelo.",
    "c3.s2.estimate": "A linha <b>Estimativa</b> no fim indica exportações Jira, registos, estados e deltas "
                      "para as suas definições; o rodapé resume modelo, âmbito, estados, realismo e seed.",
    "c3.s3.h": "3.3  Passo 3 — Gerar",
    "c3.s3.target": "<b>Pasta de destino.</b> É criada. Se não estiver vazia, o gerador pergunta — «Gerar "
                    "mesmo assim» sobrescreve ficheiros com o mesmo nome, «Escolher outra pasta» volta "
                    "atrás. «Procurar …» abre o diálogo de pastas; onde não houver, escreve o caminho.",
    "c3.s3.progress": "<b>Progresso.</b> «Gerar sala de dados» inicia nove passos; cada um mostra em curso, "
                      "concluído ou saltado, com um detalhe. A duração vai de segundos a minutos conforme "
                      "o âmbito (situação padrão cerca de 10 segundos).",
    "c3.s3.col_step": "Passo",
    "c3.s3.col_makes": "O que se produz",
    "step.story": "Estrutura e história",
    "step.arts": "Exportações Jira e livros de trabalho",
    "step.registers": "Registos",
    "step.configs": "Configurações",
    "step.sources": "Dados brutos dos fornecedores",
    "step.readme": "README",
    "step.stands": "Série de estados",
    "step.deltas": "Briefings delta",
    "step.ai_drafts": "Rascunhos de IA (mock)",
    "c3.s3.st.story": "structure.json e story.json: papéis ligados, eventos fixados",
    "c3.s3.st.arts": "por ART uma exportação Jira em raw/ e IssueTimes/Transitions/CFD em solutions/…/arts/",
    "c3.s3.st.registers": "por solução os registos (riscos, dependências, NFR, SLO, DORA, capacidades, temas …)",
    "c3.s3.st.configs": "portfolio.json, solution.json por solução, pi_config.json",
    "c3.s3.st.sources": "sources/&lt;solução&gt;/ com ficheiros replay e configurações sources",
    "c3.s3.st.readme": "README.md com estrutura, história, estados e outros caminhos",
    "c3.s3.st.stands": "snapshots/snapshot_&lt;nn&gt;_&lt;data&gt;.json por estado, stands.json, prev/now",
    "c3.s3.st.deltas": "deltas/delta_&lt;nn&gt;-&lt;nn+1&gt;.md e .html por par consecutivo",
    "c3.s3.st.ai_drafts": "ai_drafts/ — só com o interruptor, senão «saltado»",
    "c3.s3.cancel": "<b>Cancelar</b> para depois do passo em curso; a pasta contém o que foi construído até "
                    "aí. Um erro aparece com a sua mensagem na lista.",
    "c3.s3.result": "<b>Cartão de resultado.</b> Depois do último passo aparece «Sala de dados pronta» com "
                    "duração e seed, quatro números (itens e ARTs, registos e soluções, estados, tipos de "
                    "fontes), a história em três frases e botões: Abrir relatório de portefólio, Pasta de "
                    "conferência, Último delta, README, Abrir pasta, Rascunhos de IA (se gerados). Os "
                    "relatórios são renderizados no primeiro clique e abertos no browser.",
    "c3.s3.compare": "<b>Comparar delta.</b> Escolher dois estados (por exemplo 3 → 4) e «Abrir briefing "
                     "delta» — todos os pares consecutivos estão prontos em deltas/.",
    "c3.s3.after": "<b>Depois.</b> «Nova sala de dados com outro modelo …» volta ao passo 1; a linha em "
                   "baixo mostra o comando de continuação (capítulo 7).",

    # 4 -------------------------------------------------------------------
    "c4.h": "4  O que está na pasta",
    "c4.p": "A pasta de destino é uma <b>sala de dados de portefólio</b>: todos os caminhos nas "
            "configurações são relativos ao respetivo ficheiro de configuração. A pasta pode ser movida, "
            "copiada ou compactada como um todo.",
    "c4.col_path": "Caminho",
    "c4.col_content": "Conteúdo",
    "c4.structure": "Estrutura como dados: portefólios → soluções → ARTs, fluxo de trabalho por solução",
    "c4.story": "História como dados: modelo, papéis ligados, eventos com interruptor e janela de estados, notas",
    "c4.readme": "Descrição de estrutura, história, estados, fontes e outros caminhos — no idioma da execução",
    "c4.portfolio": "Ponto de entrada: configuração de portefólio sobre todas as soluções",
    "c4.pi": "Intervalos de PI ao longo do período dos dados",
    "c4.solutions": "por solução solution.json (stage_map própria onde escolhida), arts/ com IssueTimes, Transitions e CFD por ART, registers/ com os registos sob nomes padrão",
    "c4.raw": "Exportações Jira por ART em formato REST API — ao mesmo tempo material demo para o get_data",
    "c4.sources": "Dados brutos dos fornecedores como ficheiros replay (Prometheus, GitHub ou GitLab, SonarQube, CSV) mais configurações sources",
    "c4.snapshots": "snapshot_&lt;nn&gt;_&lt;data&gt;.json por estado, índice stands.json, snapshot_prev/now.json = os dois últimos",
    "c4.deltas": "delta_&lt;nn&gt;-&lt;nn+1&gt;.md e .html por par consecutivo — já renderizados",
    "c4.ai_drafts": "só com o interruptor: briefing falado mock, respostas, pacote de prompt, resposta de exercício — todos com a marca de IA",
    "c4.use": "A pasta é diretamente utilizável — relatório de portefólio, briefing delta de qualquer par, "
              "pasta de conferência, " + _c("sources fetch") + " sem rede sobre os ficheiros replay (em "
              "sources/&lt;solução&gt;/) e a verificação de exportação do get_data:",
    "c4.multi": "Com vários portefólios (modelo «Grande» ou estrutura própria), cada portefólio torna-se a "
                "sua própria sala de dados numa subpasta; um README na pasta principal aponta para elas. "
                "Um quadro de situação sobre vários portefólios não é hoje uma funcionalidade — os dados "
                "para isso já estão lado a lado.",

    # 5 -------------------------------------------------------------------
    "c5.h": "5  Compreender a história",
    "c5.p": "Cada modelo conta a mesma situação a partir de todos os registos: riscos, dependências, "
            "pressupostos, SLOs e alarmes apontam para os mesmos sítios. Os eventos ligam-se a "
            "<b>papéis</b> que decorrem da estrutura — assim a história mantém-se coerente também com a sua estrutura.",
    "c5.roles": "<b>Os papéis:</b><br/>"
                "- <b>Primeira solução</b> («anfitriã»): parece saudável, carrega os padrões silenciosos; o "
                "seu <b>último ART é o outlier</b>; entre os seus ARTs estão a dependência bloqueada e a costura recorrente.<br/>"
                "- <b>Segunda solução:</b> o seu <b>último ART é a fonte fraca de dados</b>; aqui a «Order Sync "
                "API» viola o seu SLO e surge o novo risco de segurança.<br/>"
                "- <b>Costura cross-solution:</b> o primeiro ART da segunda solução depende do primeiro ART "
                "da primeira — visível só no relatório de portefólio.<br/>"
                "- Outras soluções e portefólios recebem o conjunto base gerado pela seed, sem âncoras de história.",
    "c5.notices": "O que a estrutura não oferece cai com uma <b>nota</b> (no passo 1 e em story.json): com "
                  "uma única solução não há fonte fraca, violação de SLO nem costura cross-solution; se a "
                  "primeira solução tiver só um ART, faltam outlier, dependência bloqueada e costura "
                  "recorrente. Os dez eventos:",
    "c5.col_id": "N.º",
    "c5.col_what": "O que acontece",
    "c5.col_visible": "Visível como",
    "ev.E1.title": "O ART outlier tem cerca de três vezes o cycle time.",
    "ev.E1.effect": "Relatório de comparação: mediana/P95 a vermelho; alarme «P85 acima de 30 dias» disparado; quadro de entrega raro e lento; uma capacidade at risk.",
    "ev.E2.title": "A fonte fraca entrega dados fracos: sem CFD, quase sem first dates, dados com 60 dias.",
    "ev.E2.effect": "Confiança medium; um risco envelhece (50 dias); uma capacidade crítica; um problema de fluxo sobrevive a quatro conferências; um pressuposto ultrapassa a data de revisão; DORA/qualidade low.",
    "ev.E3.title": "A dependência entre dois ARTs da primeira solução está bloqueada e atrasada.",
    "ev.E3.effect": "Dependência at_risk → blocked; heatmap a vermelho; alarme «duas bloqueadas» logo abaixo do limiar.",
    "ev.E4.title": "A costura cross-solution entra sob pressão; os value streams puxam um pelo outro.",
    "ev.E4.effect": "Várias dependências deslizam de on_track por at_risk para blocked — visível só no relatório de portefólio; base do indicador de pontos de decisão.",
    "ev.E5.title": "A mesma costura abre pela terceira vez uma solution area sobre o mesmo tema (ambiente de teste).",
    "ev.E5.effect": "Duas solution areas fechadas, uma nova — o sinal de EA: verificar o corte ou a arquitetura, não as equipas.",
    "ev.E6.title": "A «Order Sync API» da segunda solução viola o seu SLO.",
    "ev.E6.effect": "Registo SLO: breached; NFR «API response time» violado; uma lacuna de runway atrasada.",
    "ev.E7.title": "A primeira solução parece saudável — com os padrões silenciosos.",
    "ev.E7.effect": "Um risco owned há 45 dias (aging); um tema sem epic («declared &amp; forgotten»); um problema de fluxo sobrevive a três conferências; uma capacidade sem ART; SLO «Checkout» at risk.",
    "ev.E8.title": "A qualidade dos dados da fonte fraca degrada-se ainda mais.",
    "ev.E8.effect": "A proporção de itens sem first date sobe para 80 % — confiança medium → low, cobertura visível no título.",
    "ev.E9.title": "Novo risco na segunda solução: security review não agendada.",
    "ev.E9.effect": "Surge um risco alto, mitigado — novo no briefing delta.",
    "ev.E10.title": "Roadmaps atualizados.",
    "ev.E10.effect": "Um epic perde o seu tema (iniciativa zombie); um epic da segunda solução é puxado de P2 para P1.",
    "c5.windows": "<b>Janelas de estados.</b> Cada modelo fixa em que estados um evento se aplica. Situação "
                  "padrão: outlier, fonte fraca, violação de SLO e padrões silenciosos em todos os estados, "
                  "as viragens (bloqueio, costuras, degradação, novo risco, roadmaps) só no último. A "
                  "Escalada escalona-as pela série, a Recuperação inverte-as: o estado 1 mostra tudo, "
                  "depois cura uma coisa atrás da outra. O README da sala de dados lista a janela de cada "
                  "evento; antes e depois, a série mostra a situação sem ele.",

    # 6 -------------------------------------------------------------------
    "c6.h": "6  A sala de dados na linha de comandos",
    "c6.p": "Tudo o que está nos três passos existe também como opção de " +
            _c("python -m testdata_generator --scenario portfolio") + ". Antes de construir, a linha de "
            "comandos mostra estrutura, interruptores e estimativa; depois, pasta, estados e duração.",
    "c6.col_opt": "Opção",
    "c6.col_default": "Padrão",
    "c6.col_meaning": "Significado",
    "c6.folder_word": "PASTA",
    "c6.required": "(obrigatório)",
    "c6.scenario": "Gerar uma sala de dados em vez de um ART individual",
    "c6.output": "Pasta de destino (é criada)",
    "c6.structure": "Modelo de estrutura ou structure.json próprio (portefólios → soluções → ARTs, fluxo de trabalho por solução)",
    "c6.arts": "Um portefólio a partir do número de ARTs por solução, p. ex. 3,4s,1 — três soluções com 3, 4 e 1 ARTs; um s final dá à solução um stage map próprio. Não combinável com --structure.",
    "c6.story": "Modelo da história (calm, standard, escalation, recovery)",
    "c6.event": "Ligar ou desligar um evento, p. ex. --event E3=off --event E9=on; repetível. Um evento cuja condição está desligada fica desligado, com uma nota.",
    "c6.stands_default": "6 (calm 3)",
    "c6.stands": "Número de estados (2–12), com 14 dias de intervalo, o último na data de referência; cada par consecutivo recebe um briefing delta em deltas/",
    "c6.scale": "Volume dos registos por solução: s = só âncoras, m = demo realista, l = teste de stress",
    "c6.seed_default": "(aleatória)",
    "c6.seed": "Seed para saída reprodutível; a interface usa 42",
    "c6.art_profiles": "Controlos por ART em JSON, p. ex. {\"Alpha-1\": {\"mean_cycle_days\": 30, \"pattern\": \"cluster\", \"pattern_strength\": 80}}. Campos: issue_count, mean_cycle_days, std_cycle_days, completion_rate, todo_rate, backflow_prob, pattern, pattern_strength, pi_duration_weeks, realism. As sobreposições aplicam-se em todos os estados; o resto mantém o valor da história.",
    "c6.off": "desligado",
    "c6.ai_drafts": "Escrever rascunhos de IA mock com marca em ai_drafts/",
    "c6.lang_default": "idioma da suite, senão en",
    "c6.lang": "Idioma da interface, da consola e dos textos gerados",
    "c6.continue": "Continuar uma sala de dados existente até à data (capítulo 7)",
    "c6.web": "Iniciar a interface no browser: servidor local em 127.0.0.1 (porta 0 = aleatória livre), chave de acesso no link; --no-browser só imprime o link. Termina com Ctrl+C.",
    "c6.dataspace": "Iniciar a janela da sala de dados — os mesmos três passos sem servidor",
    "c6.ex.h": "Exemplos",
    "c6.ex.1": "Situação padrão, como no tutorial e nos manuais",
    "c6.ex.2": "Escalada em oito estados, teste de stress, textos em alemão",
    "c6.ex.3": "Estrutura própria, um evento desligado, exercício de IA ligado",
    "c6.ex.4": "Cinco portefólios, 49 ARTs — demora sensivelmente",
    "c6.hint_default_lang": "Sem --lang e sem definição no launcher, consola e textos gerados ficam em inglês. "
                            "Para português, passe --lang pt ou mude o launcher.",

    # 7 -------------------------------------------------------------------
    "c7.h": "7  Continuar uma sala de dados",
    "c7.p1": "Uma sala de dados pode ser continuada até uma data posterior — como uma segunda extração do "
             "Jira: o passado fica, os itens abertos avançam, novos juntam-se.",
    "c7.p2": "O gerador continua no local as exportações Jira, IssueTimes/Transitions/CFD, configurações e "
             "a configuração de PI; o antigo snapshot_now passa a snapshot_prev, o novo estado a "
             "snapshot_now, e o README recebe uma nota com a data de referência antiga e nova e o número "
             "de novos itens. Os registos ficam inalterados. Os controlos vêm do registo do gerador nos "
             "ficheiros; o idioma segue " + _c("--lang") + ".",
    "c7.hint": "O cartão de resultado mostra o comando certo em «Depois». Para uma única exportação Jira "
               "existe --continue OLD.json (capítulo 8).",

    # 8 -------------------------------------------------------------------
    "c8.h": "8  Um único ART (gerador clássico)",
    "c8.p": "O caminho clássico produz <b>um</b> ficheiro de exportação Jira em formato REST API a partir "
            "de um ficheiro de fluxo de trabalho: os itens percorrem os estágios, permanecem tempos "
            "variáveis, recuam ocasionalmente e fecham a uma taxa ajustável. O ficheiro entra diretamente "
            "no transform_data e no build_reports. Os controlos de cycle time e padrões de fluxo são os "
            "mesmos que a sala de dados sobrepõe por ART através de --art-profiles.",
    "c8.win.h": "8.1  A janela",
    "c8.win.p": "TestdataGenerator.bat (ou " + _c("python -m testdata_generator") + " sem opções) abre a "
                "janela com campos para todos os parâmetros. Só o ficheiro de fluxo de trabalho é "
                "obrigatório; o resto tem valores padrão. A área «Portefólio demo» em baixo constrói a "
                "situação padrão com um clique — a sala de dados do capítulo 3 faz mais.",
    "c8.win.fig": "Fig. 2: Janela do gerador clássico para um único ART",
    "c8.wf.h": "8.2  O ficheiro de fluxo de trabalho",
    "c8.wf.p": "O ficheiro de fluxo de trabalho define os estágios do seu quadro Jira e é o único campo "
               "obrigatório. Tem o mesmo formato que no transform_data — um ficheiro serve os dois módulos. "
               "Cada linha descreve um estágio; os aliases (nomes alternativos de estado na exportação "
               "Jira) separam-se por dois pontos. Duas linhas especiais marcam o início e o fim do trabalho ativo:",
    "c8.wf.pre": "NomeCanonico:Alias1:Alias2\n<First>PrimeiroEstagioAtivo\n<Closed>EstagioFechado",
    "c8.wf.col_line": "Linha",
    "c8.wf.col_meaning": "Significado",
    "c8.wf.alias": "Estágio com um ou mais nomes alternativos de estado Jira",
    "c8.wf.plain_name": "Nome (sem :)",
    "c8.wf.plain": "Estágio sem aliases",
    "c8.wf.first": "Primeiro estágio ativo — o cycle time começa aqui",
    "c8.wf.closed": "Estágio fechado — marca um item como concluído",
    "c8.wf.example": "O exemplo fornecido " + _c("workflow_ART_A.txt") + " modela um fluxo SAFe ART típico:",
    "c8.wf.notes": "«Funnel» tem quatro aliases — os quatro estados Jira normalizam-se para Funnel. Analysis "
                   "é o primeiro estágio ativo (o cycle time começa aqui). Releasing conta como fechado; "
                   "Done (depois de Releasing) acolhe também itens cancelados.",
    "c8.par.h": "8.3  Referência de parâmetros",
    "c8.par.p": "Todos os parâmetros existem na janela e na linha de comandos.",
    "c8.par.col_param": "Parâmetro",
    "c8.par.col_default": "Padrão",
    "c8.par.col_desc": "Descrição",
    "c8.par.workflow": "Ficheiro de definição do fluxo de trabalho (.txt)",
    "c8.par.output": "Caminho do ficheiro de saída",
    "c8.par.project": "Chave do projeto Jira dos itens gerados",
    "c8.par.issues": "Número de itens",
    "c8.par.from": "Data de criação mais antiga",
    "c8.par.to": "Data de transição mais recente",
    "c8.par.types": "Tipos de item com pesos (a soma não precisa de ser 1)",
    "c8.par.completion": "Proporção de itens que atingem o estágio fechado (0–1)",
    "c8.par.todo": "Proporção de itens abertos que ficam em estágios iniciais (0–1)",
    "c8.par.backflow": "Probabilidade de um passo atrás por transição (0–1)",
    "c8.par.realism": "Desordem dos percursos de estado: saltos, cancelamentos, estacionamentos, ciclos, reaberturas; cerca de 70 é como um ART real",
    "c8.par.seed": "Seed para saída reprodutível",
    "c8.par.mean": "Cycle time médio em dias (lognormal); ativa o controlo de cycle time",
    "c8.par.std_default": "30 % da média",
    "c8.par.std": "Desvio padrão do cycle time em dias",
    "c8.par.pattern": "Padrão de fluxo: none / triangle / flat_triangle / cluster / batch (ver 8.4)",
    "c8.par.pi": "Duração do PI em semanas (para cluster e batch)",
    "c8.par.strength": "Intensidade do padrão (0 = subtil, 50 = padrão, 100 = forte)",
    "c8.par.continue": "Continuar uma extração anterior até --to-date: o passado fica byte a byte, os itens abertos avançam, novos juntam-se; requer --workflow",
    "c8.par.learn": "Aprender um perfil de transição a partir de um ficheiro real de transições (só contagens e horas); --transition-profile gera com ele",
    "c8.pat.h": "8.4  Padrões de fluxo",
    "c8.pat.p": "O gerador simula anti-padrões de fluxo típicos da literatura de Vacanti e Singh. Combine "
                "--mean-cycle-days com --pattern; a janela oferece botões de opção e cursores.",
    "c8.pat.col_pattern": "Padrão",
    "c8.pat.col_look": "Scatterplot",
    "c8.pat.col_desc": "Descrição",
    "c8.pat.none.look": "Nuvem de pontos uniforme",
    "c8.pat.none.desc": "Cycle time aleatório sem tendência — comportamento padrão",
    "c8.pat.triangle.look": "Triângulo, ângulo reto em baixo à direita",
    "c8.pat.triangle.desc": "O cycle time sobe linearmente com o tempo (cerca de 1–4× na intensidade padrão). Um processo que abranda cada vez mais.",
    "c8.pat.flat.look": "Triângulo, subida achata",
    "c8.pat.flat.desc": "Como triangle, a subida achata para o fim. Uma deterioração que estabiliza.",
    "c8.pat.cluster.look": "Aglomerados verticais no fim do PI",
    "c8.pat.cluster.desc": "O cycle time mantém-se estável, mas a maioria dos itens fecha nas duas últimas semanas antes do fim do PI. Comportamento movido por prazos.",
    "c8.pat.batch.look": "Colunas de altura variável no fim do PI",
    "c8.pat.batch.desc": "Como cluster, mas com cycle time muito variável (0,1× a 3× a média). Tarefas curtas e muito longas são empurradas juntas para o fim do PI.",
    "c8.pat.hint": "--pattern requer --mean-cycle-days; sem ele o padrão é ignorado. "
                   "--std-cycle-days controla a dispersão, --pi-duration-weeks a duração do PI para cluster e batch.",
    "c8.ex.h": "8.5  ART_A — exemplo completo",
    "c8.ex.p": "Do gerador ao relatório pronto no projeto fictício ART_A:",
    "c8.ex.s1": "Passo 1: Gerar dados de teste",
    "c8.ex.s2": "Passo 2: Processar com transform_data",
    "c8.ex.s3": "Passo 3: Criar o relatório com build_reports",
    "c8.ex.expect": "<b>O que esperar (seed 42, 200 itens):</b><br/>"
                    "- Chaves ART_A-0001 a ART_A-0200<br/>"
                    "- Tipos cerca de 120 Feature, 40 Bug, 40 Enabler<br/>"
                    "- Cerca de 150 itens em Releasing ou Done<br/>"
                    "- Datas de criação distribuídas por 2025<br/>"
                    "- Passos atrás ocasionais (backflow-prob 0.08 = cerca de 8 %)",

    # 9 -------------------------------------------------------------------
    "c9.h": "9  Perguntas frequentes",
    "c9.q1": "Janela ou browser — qual devo usar?",
    "c9.a1": "A janela. Produz a mesma sala de dados e não abre nenhuma porta de rede. A página do browser "
             "só num computador privado; em computadores de empresa o software de segurança bloqueia e "
             "reporta servidores locais.",
    "c9.q2": "Porque é que a minha sala de dados está em inglês, embora eu fale português?",
    "c9.a2": "Sem indicação de idioma, o gerador usa o idioma da suite do launcher, senão inglês. Ponha o "
             "launcher em português, mude no canto superior direito ou passe --lang pt.",
    "c9.q3": "A pasta de destino não está vazia — o que acontece?",
    "c9.a3": "O gerador pergunta. «Gerar mesmo assim» sobrescreve ficheiros com o mesmo nome e deixa o "
             "resto; «Escolher outra pasta» desiste.",
    "c9.q4": "A geração demora muito.",
    "c9.a4": "A partir de 30 ARTs, ou com âmbito L e vários portefólios, a caixa «O que se produz» avisa. "
             "Para formação chegam a estrutura padrão e o âmbito M (cerca de 10 segundos).",
    "c9.q5": "Dados de teste ou dados reais?",
    "c9.a5": "Para demonstrações, formação e testes de instalação, os dados de teste são a melhor escolha — "
             "sem questões de privacidade. Análises de fluxo e decisões reais precisam de dados reais; a "
             "exportação manual está descrita no manual do Get Data.",
    "c9.q6": "Posso configurar ARTs individuais de forma diferente?",
    "c9.a6": "Sim, através de --art-profiles FICHEIRO.json na linha de comandos (capítulo 6). O separador "
             "para isso na interface segue numa beta posterior.",

    # 10 ------------------------------------------------------------------
    "c10.h": "10  Glossário",
    "c10.col_term": "Termo",
    "c10.col_expl": "Explicação",
    "g.art.t": "ART",
    "g.art.e": "Agile Release Train — várias equipas que entregam em conjunto no SAFe",
    "g.dataspace.t": "Sala de dados",
    "g.dataspace.e": "Uma pasta com tudo o que um quadro de situação de portefólio precisa: configurações, exportações, registos, estados, briefings — autónoma e movível",
    "g.delta.t": "Briefing delta",
    "g.delta.e": "«O que mudou?» entre dois estados — débito, confiança, costuras, novos riscos",
    "g.conference.t": "Pasta de conferência",
    "g.conference.e": "A pasta para a value stream conference: problemas de fluxo que sobrevivem a conferências, com o quadro de situação",
    "g.seam.t": "Costura",
    "g.seam.e": "Uma dependência entre ARTs ou soluções onde a pressão se mostra — dentro de uma solução ou entre value streams",
    "g.register.t": "Registo",
    "g.register.e": "Uma lista por solução: riscos, dependências, pressupostos, NFR, runway, SLO, DORA, capacidades, temas, problemas de fluxo …",
    "g.stand.t": "Estado",
    "g.stand.e": "Um snapshot congelado do quadro de situação numa data; os estados distam 14 dias",
    "g.seed.t": "Seed",
    "g.seed.e": "Valor inicial do gerador aleatório — mesma seed, mesma saída",
    "g.solution.t": "Solução",
    "g.solution.e": "Um grupo de ARTs que entrega uma solução em conjunto; na sala de dados, o nível com registos próprios",
    "g.stage_map.t": "Stage map",
    "g.stage_map.e": "Agrupamento próprio dos estágios do fluxo de trabalho de uma solução (p. ex. preparação/implementação/concluído) em vez do caminho padrão",
    "g.value_stream.t": "Value stream",
    "g.value_stream.e": "O fluxo da necessidade ao valor; representado na sala de dados pelas soluções",
    "g.workflow.t": "Fluxo de trabalho",
    "g.workflow.e": "Sequência ordenada de estágios que um item percorre; descrita como ficheiro de texto",
    "g.realism.t": "Realismo",
    "g.realism.e": "Grau de desordem dos percursos de estado: saltos, cancelamentos, estacionamentos, ciclos, reaberturas",
    "g.cfd.t": "CFD",
    "g.cfd.e": "Cumulative Flow Diagram — stock por estágio ao longo do tempo, acumulado",
}

_M["fr"] = {
    # 1 -------------------------------------------------------------------
    "c1.h": "1  Qu'est-ce que le Générateur de données de test ?",
    "c1.p1": "Le <b>Générateur de données de test</b> produit des données inventées mais réalistes pour "
             "SituationReport — pour démontrer, apprendre et tester le rapport de portefeuille, le "
             "briefing delta, le dossier de conférence et les registres sans toucher à de vraies données "
             "de projet. Aucune personne n'apparaît ; la même graine donne le même espace de données.",
    "c1.p2": "Le générateur a deux voies. L'<b>espace de données</b> est la voie par défaut de la bêta : "
             "en trois étapes naît un dossier de portefeuille complet avec structure, histoire, exports "
             "Jira par ART, registres, données brutes des fournisseurs, une série d'états et les "
             "briefings delta déjà rendus. L'<b>ART seul</b> est la voie classique : un fichier d'export "
             "Jira à partir d'un fichier de workflow, avec tous les réglages de cycle time et de motifs "
             "de flux (chapitre 8).",
    "c1.ways": "<b>Quelle voie, quand ?</b><br/>"
               "- <b>Espace de données (fenêtre ou navigateur) :</b> formation, présentation, tutoriels, "
               "tests de la chaîne de portefeuille — tout ce qui demande une image de situation entière.<br/>"
               "- <b>ART seul :</b> un export Jira pour transform_data et build_reports, des motifs de flux "
               "ciblés pour la formation aux nuages de points de cycle time, la poursuite d'un extrait antérieur.",
    "c1.p3": "Ce manuel décrit d'abord l'espace de données (chapitres 2 à 7), puis le générateur "
             "classique d'ART seul (chapitre 8). Qui ne cherche que la minute jusqu'au premier rapport de "
             "portefeuille prend le tutoriel « Espace de données démo en une minute » "
             "(docs/tutorials/demo-data-room.md, aussi en PDF).",
    "c1.uses": "<b>Usages typiques :</b><br/>"
               "- <b>Tester une nouvelle installation :</b> la chaîne tourne-t-elle des données brutes au rapport de portefeuille ?<br/>"
               "- <b>Démos et présentations :</b> une situation avec valeur aberrante, source faible et coutures, sans question de confidentialité<br/>"
               "- <b>Formation :</b> la même histoire pour tous les participants, reproductible par la graine<br/>"
               "- <b>Développement :</b> test de charge avec une grande structure (échelle L, jusqu'à 49 ARTs)",
    "c1.beta": "État : bêta, octobre 2026. L'interface de l'espace de données est nouvelle ; l'onglet des "
               "profils par ART dans l'interface manque encore (ligne de commande : --art-profiles).",

    # 2 -------------------------------------------------------------------
    "c2.h": "2  Démarrage",
    "c2.pkg.h": "2.1  Paquet portable (recommandé)",
    "c2.pkg.p": "Le paquet portable embarque Python — rien à installer. Après décompression, quatre "
                "fichiers de démarrage du générateur sont prêts :",
    "c2.pkg.col_file": "Fichier de démarrage (Windows)",
    "c2.pkg.col_what": "Ce qu'il ouvre",
    "c2.pkg.window": "<b>Espace de données en fenêtre</b> — la voie par défaut. Trois étapes, aucun port "
                     "réseau, fonctionne aussi sur les ordinateurs d'entreprise.",
    "c2.pkg.launcher": "Le lanceur avec tous les modules ; il porte les cartes « Espace de données (fenêtre) » "
                       "et « Espace de données (navigateur) » ainsi que « Testdata Generator » pour l'ART seul.",
    "c2.pkg.browser": "<b>Espace de données dans le navigateur</b> — les mêmes trois étapes en page web. "
                      "Démarre un serveur local sur 127.0.0.1 avec une clé aléatoire dans le lien. "
                      "Ordinateurs privés seulement : le logiciel de sécurité des ordinateurs d'entreprise "
                      "bloque et signale les serveurs locaux.",
    "c2.pkg.single": "<b>ART seul</b> — la fenêtre classique avec fichier de workflow, réglages et motifs de "
                     "flux (chapitre 8).",
    "c2.pkg.unix": "macOS : les mêmes noms en .command (clic droit → Ouvrir). Linux : en .sh (python3 et "
                   "python3-tk requis). Le premier démarrage installe une fois un environnement Python — "
                   "il faut Internet pour cela.",
    "c2.pkg.defender": "Note pour Windows : si le démarrage signale que Python est introuvable, Windows avait "
                       "bloqué le fichier ZIP. Clic droit sur le ZIP → Propriétés → Sécurité → Débloquer → "
                       "OK → décompresser à nouveau.",
    "c2.src.h": "2.2  Depuis le code source (Python requis)",
    "c2.src.p": "Les trois interfaces correspondent à trois appels : fenêtre, navigateur, ART seul.",
    "c2.wvb.h": "2.3  Fenêtre ou navigateur ?",
    "c2.wvb.p": "Les deux montrent les mêmes trois étapes avec les mêmes réglages et produisent le même "
                "espace de données. La fenêtre est une fenêtre de programme ordinaire (tkinter) et n'a besoin "
                "de rien d'autre. La page du navigateur est un peu plus agréable à lire mais passe par un "
                "serveur local — sur un ordinateur d'entreprise, la sécurité des postes l'a bloqué et "
                "signalé au premier test. D'où la règle : la fenêtre d'abord, le navigateur seulement en privé.",
    "c2.lang.h": "2.4  Langues",
    "c2.lang.p": "Interface, histoire, README, progression, journal et les briefings delta générés existent en "
                 "allemand, anglais, roumain, portugais et français. Le générateur démarre dans la langue "
                 "réglée dans le lanceur ; le sélecteur en haut à droite de la fenêtre et de la page la change "
                 "— les saisies sont conservées. Une exécution a une langue : interface et textes générés "
                 "concordent. Sans réglage du lanceur et sans " + _c("--lang") + ", la langue est l'anglais. "
                 "Le roumain, le portugais et le français sont des ébauches encore à relire par des locuteurs natifs.",

    # 3 -------------------------------------------------------------------
    "c3.h": "3  L'espace de données en trois étapes",
    "c3.p": "Fenêtre et page du navigateur guident à travers trois étapes : <b>Scénario</b> (quelle "
            "situation), <b>Périmètre &amp; sources</b> (quelle taille, quelle durée, quel réalisme) et "
            "<b>Générer</b> (où, et c'est parti). Les valeurs par défaut produisent la situation démo "
            "qu'utilisent aussi les tutoriels et manuels des modules de portefeuille.",
    "c3.fig": "Fig. 1 : Étape 1 « Scénario » dans la fenêtre de l'espace de données — modèles à gauche, "
              "événements en dessous, structure à droite (interface allemande)",
    "c3.s1.h": "3.1  Étape 1 — Scénario",
    "c3.s1.p": "À gauche, vous choisissez un <b>modèle</b> d'histoire. Les événements se lient aux rôles de "
               "la structure à droite — valeur aberrante, source faible, coutures — et non à des noms fixes.",
    "c3.s1.col_tpl": "Modèle",
    "c3.s1.col_tells": "Ce qu'il raconte",
    "c3.s1.col_stands": "États",
    "tpl.calm": "Calme",
    "tpl.calm.desc": "Aucun retournement, toutes les équipes dans le cadre. Pour la première formation et la "
                     "lecture d'une image tranquille. Qui donne l'alarme ici a mal lu l'image.",
    "tpl.standard": "Situation standard",
    "c3.s1.rec": "(recommandé)",
    "tpl.standard.desc": "Valeur aberrante, source faible, rupture de SLO et motifs silencieux dès le début ; "
                         "les retournements arrivent avec le dernier état. Pour présentations et tutoriels.",
    "tpl.escalation": "Escalade",
    "tpl.escalation.desc": "La pression monte état après état : rupture de SLO tôt, couture bloquée au "
                           "milieu, dégradation et coutures inter-solutions tard. Pour l'exercice de conférence.",
    "tpl.recovery": "Rétablissement",
    "tpl.recovery.desc": "Commence mal et guérit : coutures résolues, le SLO tient, la valeur aberrante trouve "
                         "son rythme. Pour le briefing delta : qu'est-ce qui a changé ?",
    "c3.s1.events": "<b>Événements du modèle.</b> Le tableau en dessous indique pour chaque événement quand il "
                    "s'applique (tous les états, à partir de l'état n, dernier état), ce qui se passe et sous "
                    "quelle forme il devient visible dans le rapport. Chaque événement a une case à cocher ; "
                    "les événements désactivés sont absents de l'espace de données. Un événement dont le "
                    "prérequis est désactivé reste désactivé, avec une note. La fenêtre d'un événement suit "
                    "le nombre d'états de l'étape 2. Le chapitre 5 explique les dix événements.",
    "c3.s1.structure": "<b>Structure de l'espace de données (droite).</b> Un modèle de structure — Petite "
                       "(1 portefeuille · 1 solution · 2 ARTs), Standard (1 · 2 · 3 chacune), Grande "
                       "(5 portefeuilles · 3–4 solutions · 1–6 ARTs) — ou la vôtre : ajouter ou retirer des "
                       "portefeuilles et des solutions, compter les ARTs par solution, changer les noms (les "
                       "noms d'ART suivent la solution). Par solution, vous choisissez le workflow classique ou "
                       "une stage map propre. Au moins un ART par solution.",
    "c3.s1.yields": "<b>Ce qui est produit.</b> L'encadré en bas à droite fait le compte : exports Jira, "
                    "classeurs, registres, états et briefings delta pour la structure choisie (standard : "
                    "6 exports, 18 classeurs, 22 registres, 6 états, 5 deltas). À partir de 30 ARTs il "
                    "avertit : la génération prend alors nettement plus de temps.",
    "c3.s2.h": "3.2  Étape 2 — Périmètre &amp; sources",
    "c3.s2.p": "Les valeurs par défaut suffisent pour la formation et la présentation.",
    "c3.s2.col_setting": "Réglage",
    "c3.s2.col_default": "Défaut",
    "c3.s2.col_meaning": "Signification",
    "ui.stands": "États",
    "ui.scale": "Périmètre",
    "ui.realism": "Réalisme",
    "ui.seed": "Graine",
    "ui.reference": "Dernier état",
    "ui.lang": "Langue des textes",
    "c3.s2.stands": "2 à 12 états espacés de 14 jours ; chaque état est un instantané figé, chaque paire "
                    "consécutive un briefing delta prêt. Le modèle « Calme » en propose 3.",
    "c3.s2.scale": "S = ancres de l'histoire seulement, registres courts ; M = registres réalistes ; L = test "
                   "de charge avec registres pleins (heatmap dense, matrice de feuille de route complète). Les "
                   "ancres et leurs histoires sont identiques à chaque niveau.",
    "c3.s2.realism": "Désordre des parcours de statut : sauts, abandons, mises en attente, boucles, "
                     "réouvertures. 0 = lisse, 100 = comme en vrai ; 60 est un ART typique.",
    "c3.s2.seed": "Même graine, même structure et même date de référence donnent le même espace de données — "
                  "idéal quand tous les participants doivent voir la même chose.",
    "c3.s2.today": "aujourd'hui",
    "c3.s2.reference": "Date du dernier état ; les autres se situent 14 jours avant, chacun. Le feu de qualité "
                       "du rapport de portefeuille classe ainsi les données comme actuelles.",
    "c3.s2.ui_lang": "langue de l'interface",
    "c3.s2.lang": "Langue de l'histoire, du README et des briefings delta ; suit l'interface.",
    "c3.s2.details": "<b>Détails pour analystes.</b> Cycle times, motifs de flux et longueur de PI peuvent être "
                     "surchargés par ART — les mêmes réglages que pour l'ART seul. Dans cette bêta, cela passe "
                     "par la ligne de commande avec " + _c("--art-profiles FICHIER.json") +
                     " (chapitre 6) ; le tableau dans l'interface suivra avec l'onglet ART.",
    "c3.s2.sources": "<b>Sources livrées avec l'espace.</b> Toujours incluses : exports Jira par ART (sans "
                     "personnes), réponses SLO Prometheus, déploiements/PR/incidents GitHub pour la première "
                     "solution, valeurs DORA quotidiennes GitLab pour la seconde, mesures de qualité SonarQube "
                     "et un CSV de SLO pour la voie manuelle — données brutes au format de chaque système avec "
                     "les mêmes chiffres que les registres, de sorte que " + _c("sources fetch") +
                     " tourne dans l'espace de données sans réseau.",
    "c3.s2.ai": "<b>Ébauches IA (interrupteur, désactivé par défaut).</b> Un exposé de situation factice, trois "
                "réponses, un lot de prompts et une réponse d'exercice aux chiffres faux arrivent dans "
                "ai_drafts/ — tous avec le marqueur IA, aucun approuvé. Vous y exercez l'approbation et " +
                _c("llm check") + " sans installer de modèle.",
    "c3.s2.estimate": "La ligne <b>Estimation</b> à la fin indique exports Jira, registres, états et deltas pour "
                      "vos réglages ; le pied de page résume modèle, périmètre, états, réalisme et graine.",
    "c3.s3.h": "3.3  Étape 3 — Générer",
    "c3.s3.target": "<b>Dossier cible.</b> Il est créé. S'il n'est pas vide, le générateur demande — « Générer "
                    "quand même » écrase les fichiers de même nom, « Choisir un autre dossier » revient en "
                    "arrière. « Parcourir … » ouvre le sélecteur de dossier ; là où il n'y en a pas, saisissez le chemin.",
    "c3.s3.progress": "<b>Progression.</b> « Générer l'espace de données » lance neuf étapes ; chacune affiche "
                      "en cours, terminé ou sauté, avec un détail. La durée va de quelques secondes à quelques "
                      "minutes selon le périmètre (situation standard environ 10 secondes).",
    "c3.s3.col_step": "Étape",
    "c3.s3.col_makes": "Ce qui est produit",
    "step.story": "Structure et histoire",
    "step.arts": "Exports Jira et classeurs",
    "step.registers": "Registres",
    "step.configs": "Configurations",
    "step.sources": "Données brutes des fournisseurs",
    "step.readme": "README",
    "step.stands": "Série d'états",
    "step.deltas": "Briefings delta",
    "step.ai_drafts": "Ébauches IA (factices)",
    "c3.s3.st.story": "structure.json et story.json : rôles liés, événements fixés",
    "c3.s3.st.arts": "par ART un export Jira sous raw/ et IssueTimes/Transitions/CFD sous solutions/…/arts/",
    "c3.s3.st.registers": "par solution les registres (risques, dépendances, NFR, SLO, DORA, capacités, thèmes …)",
    "c3.s3.st.configs": "portfolio.json, solution.json par solution, pi_config.json",
    "c3.s3.st.sources": "sources/&lt;solution&gt;/ avec fichiers de relecture et configurations sources",
    "c3.s3.st.readme": "README.md avec structure, histoire, états et autres voies",
    "c3.s3.st.stands": "snapshots/snapshot_&lt;nn&gt;_&lt;date&gt;.json par état, stands.json, prev/now",
    "c3.s3.st.deltas": "deltas/delta_&lt;nn&gt;-&lt;nn+1&gt;.md et .html par paire consécutive",
    "c3.s3.st.ai_drafts": "ai_drafts/ — seulement avec l'interrupteur, sinon « sauté »",
    "c3.s3.cancel": "<b>Annuler</b> s'arrête après l'étape en cours ; le dossier contient ce qui a été construit "
                    "jusque-là. Une erreur apparaît avec son message dans la liste.",
    "c3.s3.result": "<b>Carte de résultat.</b> Après la dernière étape apparaît « Espace de données prêt » avec "
                    "durée et graine, quatre chiffres (tickets et ARTs, registres et solutions, états, types de "
                    "sources), l'histoire en trois phrases et des boutons : Ouvrir le rapport de portefeuille, "
                    "Dossier de conférence, Dernier delta, README, Ouvrir le dossier, Ébauches IA (si générées). "
                    "Les rapports sont rendus au premier clic et ouverts dans le navigateur.",
    "c3.s3.compare": "<b>Comparer un delta.</b> Choisir deux états (par exemple 3 → 4) et « Ouvrir le briefing "
                     "delta » — toutes les paires consécutives sont prêtes sous deltas/.",
    "c3.s3.after": "<b>Ensuite.</b> « Nouvel espace de données avec un autre modèle … » revient à l'étape 1 ; la "
                   "ligne en dessous montre la commande de poursuite (chapitre 7).",

    # 4 -------------------------------------------------------------------
    "c4.h": "4  Ce que contient le dossier",
    "c4.p": "Le dossier cible est un <b>espace de données de portefeuille</b> : tous les chemins des "
            "configurations sont relatifs à leur fichier de configuration. Le dossier peut être déplacé, "
            "copié ou compressé d'un bloc.",
    "c4.col_path": "Chemin",
    "c4.col_content": "Contenu",
    "c4.structure": "Structure en données : portefeuilles → solutions → ARTs, workflow par solution",
    "c4.story": "Histoire en données : modèle, rôles liés, événements avec interrupteur et fenêtre d'états, notes",
    "c4.readme": "Description de la structure, de l'histoire, des états, des sources et des autres voies — dans la langue de l'exécution",
    "c4.portfolio": "Point d'entrée : configuration de portefeuille sur toutes les solutions",
    "c4.pi": "Intervalles de PI sur la période des données",
    "c4.solutions": "par solution solution.json (stage_map propre si choisie), arts/ avec IssueTimes, Transitions et CFD par ART, registers/ avec les registres sous leurs noms standard",
    "c4.raw": "Exports Jira par ART au format REST API — en même temps matière démo pour get_data",
    "c4.sources": "Données brutes des fournisseurs en fichiers de relecture (Prometheus, GitHub ou GitLab, SonarQube, CSV) plus configurations sources",
    "c4.snapshots": "snapshot_&lt;nn&gt;_&lt;date&gt;.json par état, index stands.json, snapshot_prev/now.json = les deux derniers",
    "c4.deltas": "delta_&lt;nn&gt;-&lt;nn+1&gt;.md et .html par paire consécutive — déjà rendus",
    "c4.ai_drafts": "seulement avec l'interrupteur : exposé factice, réponses, lot de prompts, réponse d'exercice — tous avec le marqueur IA",
    "c4.use": "Le dossier est directement utilisable — rapport de portefeuille, briefing delta de n'importe "
              "quelle paire, dossier de conférence, " + _c("sources fetch") + " sans réseau sur les fichiers "
              "de relecture (dans sources/&lt;solution&gt;/) et le contrôle d'export de get_data :",
    "c4.multi": "Avec plusieurs portefeuilles (modèle « Grande » ou structure propre), chaque portefeuille "
                "devient son propre espace de données dans un sous-dossier ; un README dans le dossier "
                "principal y renvoie. Une image de situation sur plusieurs portefeuilles n'est pas une "
                "fonction aujourd'hui — les données pour cela sont déjà côte à côte.",

    # 5 -------------------------------------------------------------------
    "c5.h": "5  Comprendre l'histoire",
    "c5.p": "Chaque modèle raconte la même situation depuis tous les registres : risques, dépendances, "
            "hypothèses, SLO et alarmes pointent vers les mêmes endroits. Les événements se lient à des "
            "<b>rôles</b> qui découlent de la structure — l'histoire reste ainsi cohérente avec votre propre structure.",
    "c5.roles": "<b>Les rôles :</b><br/>"
                "- <b>Première solution</b> (« hôte ») : paraît saine, porte les motifs silencieux ; son "
                "<b>dernier ART est la valeur aberrante</b> ; entre ses ARTs se trouvent la dépendance bloquée "
                "et la couture récurrente.<br/>"
                "- <b>Seconde solution :</b> son <b>dernier ART est la source de données faible</b> ; c'est ici que "
                "l'« Order Sync API » rompt son SLO et qu'apparaît le nouveau risque de sécurité.<br/>"
                "- <b>Couture inter-solutions :</b> le premier ART de la seconde solution dépend du premier ART "
                "de la première — visible seulement dans le rapport de portefeuille.<br/>"
                "- Les autres solutions et portefeuilles reçoivent le jeu de base généré par la graine, sans ancres d'histoire.",
    "c5.notices": "Ce que la structure ne fournit pas tombe avec une <b>note</b> (à l'étape 1 et dans "
                  "story.json) : avec une seule solution, il n'y a ni source faible, ni rupture de SLO, ni "
                  "couture inter-solutions ; si la première solution n'a qu'un ART, la valeur aberrante, la "
                  "dépendance bloquée et la couture récurrente manquent. Les dix événements :",
    "c5.col_id": "N°",
    "c5.col_what": "Ce qui se passe",
    "c5.col_visible": "Visible comme",
    "ev.E1.title": "L'ART aberrant a environ trois fois le cycle time.",
    "ev.E1.effect": "Rapport de comparaison : médiane/P95 en rouge ; alarme « P85 au-dessus de 30 jours » déclenchée ; image de livraison rare et lente ; une capacité at risk.",
    "ev.E2.title": "La source faible livre des données faibles : pas de CFD, presque pas de first dates, données vieilles de 60 jours.",
    "ev.E2.effect": "Confiance medium ; un risque vieillit (50 jours) ; une capacité critique ; un problème de flux survit à quatre conférences ; une hypothèse dépasse sa date de revue ; DORA/qualité low.",
    "ev.E3.title": "La dépendance entre deux ARTs de la première solution est bloquée et en retard.",
    "ev.E3.effect": "Dépendance at_risk → blocked ; heatmap en rouge ; alarme « deux bloquées » juste sous le seuil.",
    "ev.E4.title": "La couture inter-solutions passe sous pression ; les value streams tirent l'un sur l'autre.",
    "ev.E4.effect": "Plusieurs dépendances glissent de on_track à blocked en passant par at_risk — visible seulement dans le rapport de portefeuille ; base de l'indicateur de points de décision.",
    "ev.E5.title": "La même couture ouvre pour la troisième fois une solution area sur le même sujet (environnement de test).",
    "ev.E5.effect": "Deux solution areas fermées, une nouvelle — le signal EA : vérifier le découpage ou l'architecture, pas les équipes.",
    "ev.E6.title": "L'« Order Sync API » de la seconde solution rompt son SLO.",
    "ev.E6.effect": "Registre SLO : breached ; NFR « API response time » violé ; un écart de runway en retard.",
    "ev.E7.title": "La première solution paraît saine — avec les motifs silencieux.",
    "ev.E7.effect": "Un risque owned depuis 45 jours (aging) ; un thème sans epic (« declared &amp; forgotten ») ; un problème de flux survit à trois conférences ; une capacité sans ART ; SLO « Checkout » at risk.",
    "ev.E8.title": "La qualité des données de la source faible se dégrade encore.",
    "ev.E8.effect": "La part de tickets sans first date monte à 80 % — confiance medium → low, couverture visible dans le titre.",
    "ev.E9.title": "Nouveau risque dans la seconde solution : security review non planifiée.",
    "ev.E9.effect": "Un risque élevé, atténué, apparaît — nouveau dans le briefing delta.",
    "ev.E10.title": "Feuilles de route mises à jour.",
    "ev.E10.effect": "Un epic perd son thème (initiative zombie) ; un epic de la seconde solution est tiré de P2 vers P1.",
    "c5.windows": "<b>Fenêtres d'états.</b> Chaque modèle fixe dans quels états un événement s'applique. "
                  "Situation standard : valeur aberrante, source faible, rupture de SLO et motifs silencieux "
                  "dans tous les états, les retournements (blocage, coutures, dégradation, nouveau risque, "
                  "feuilles de route) seulement dans le dernier. L'Escalade les échelonne sur la série, le "
                  "Rétablissement les inverse : l'état 1 montre tout, puis les choses guérissent l'une après "
                  "l'autre. Le README de l'espace de données liste la fenêtre de chaque événement ; avant et "
                  "après, la série montre la situation sans lui.",

    # 6 -------------------------------------------------------------------
    "c6.h": "6  L'espace de données en ligne de commande",
    "c6.p": "Tout ce que contiennent les trois étapes existe aussi comme option de " +
            _c("python -m testdata_generator --scenario portfolio") + ". Avant de construire, la ligne de "
            "commande affiche structure, interrupteurs et estimation ; après, dossier, états et durée.",
    "c6.col_opt": "Option",
    "c6.col_default": "Défaut",
    "c6.col_meaning": "Signification",
    "c6.folder_word": "DOSSIER",
    "c6.required": "(obligatoire)",
    "c6.scenario": "Générer un espace de données au lieu d'un ART seul",
    "c6.output": "Dossier cible (il est créé)",
    "c6.structure": "Modèle de structure ou structure.json propre (portefeuilles → solutions → ARTs, workflow par solution)",
    "c6.arts": "Un portefeuille à partir du nombre d'ARTs par solution, p. ex. 3,4s,1 — trois solutions avec 3, 4 et 1 ARTs ; un s final donne à la solution une stage map propre. Non combinable avec --structure.",
    "c6.story": "Modèle d'histoire (calm, standard, escalation, recovery)",
    "c6.event": "Activer ou désactiver un événement, p. ex. --event E3=off --event E9=on ; répétable. Un événement dont le prérequis est désactivé reste désactivé, avec une note.",
    "c6.stands_default": "6 (calm 3)",
    "c6.stands": "Nombre d'états (2–12), espacés de 14 jours, le dernier à la date de référence ; chaque paire consécutive reçoit un briefing delta sous deltas/",
    "c6.scale": "Volume des registres par solution : s = ancres seulement, m = démo réaliste, l = test de charge",
    "c6.seed_default": "(aléatoire)",
    "c6.seed": "Graine pour une sortie reproductible ; l'interface prend 42",
    "c6.art_profiles": "Réglages par ART en JSON, p. ex. {\"Alpha-1\": {\"mean_cycle_days\": 30, \"pattern\": \"cluster\", \"pattern_strength\": 80}}. Champs : issue_count, mean_cycle_days, std_cycle_days, completion_rate, todo_rate, backflow_prob, pattern, pattern_strength, pi_duration_weeks, realism. Les surcharges valent dans tous les états ; le reste garde sa valeur d'histoire.",
    "c6.off": "désactivé",
    "c6.ai_drafts": "Écrire des ébauches IA factices avec marqueur dans ai_drafts/",
    "c6.lang_default": "langue de la suite, sinon en",
    "c6.lang": "Langue de l'interface, de la console et des textes générés",
    "c6.continue": "Poursuivre un espace de données existant jusqu'à la date (chapitre 7)",
    "c6.web": "Lancer l'interface navigateur : serveur local sur 127.0.0.1 (port 0 = libre aléatoire), clé d'accès dans le lien ; --no-browser n'affiche que le lien. Fin par Ctrl+C.",
    "c6.dataspace": "Lancer la fenêtre de l'espace de données — les mêmes trois étapes sans serveur",
    "c6.ex.h": "Exemples",
    "c6.ex.1": "Situation standard, comme dans le tutoriel et les manuels",
    "c6.ex.2": "Escalade sur huit états, test de charge, textes en allemand",
    "c6.ex.3": "Structure propre, un événement désactivé, exercice IA activé",
    "c6.ex.4": "Cinq portefeuilles, 49 ARTs — nettement plus long",
    "c6.hint_default_lang": "Sans --lang et sans réglage du lanceur, console et textes générés sont en anglais. "
                            "Pour le français, passez --lang fr ou changez le lanceur.",

    # 7 -------------------------------------------------------------------
    "c7.h": "7  Poursuivre un espace de données",
    "c7.p1": "Un espace de données peut être poursuivi jusqu'à une date ultérieure — comme un second extrait "
             "de Jira : le passé reste, les tickets ouverts avancent, de nouveaux s'ajoutent.",
    "c7.p2": "Le générateur poursuit sur place les exports Jira, IssueTimes/Transitions/CFD, les configurations "
             "et la configuration de PI ; l'ancien snapshot_now devient snapshot_prev, le nouvel état "
             "snapshot_now, et le README reçoit une note avec l'ancienne et la nouvelle date de référence et "
             "le nombre de nouveaux tickets. Les registres restent inchangés. Les réglages viennent de "
             "l'enregistrement du générateur dans les fichiers ; la langue suit " + _c("--lang") + ".",
    "c7.hint": "La carte de résultat montre la commande adéquate sous « Ensuite ». Pour un seul export Jira, il "
               "existe --continue OLD.json (chapitre 8).",

    # 8 -------------------------------------------------------------------
    "c8.h": "8  Un seul ART (générateur classique)",
    "c8.p": "La voie classique produit <b>un</b> fichier d'export Jira au format REST API à partir d'un fichier "
            "de workflow : les tickets traversent les étapes, y séjournent des durées variables, reculent "
            "parfois et se ferment à un taux réglable. Le fichier entre directement dans transform_data et "
            "build_reports. Les réglages de cycle time et de motifs de flux sont ceux que l'espace de données "
            "surcharge par ART via --art-profiles.",
    "c8.win.h": "8.1  La fenêtre",
    "c8.win.p": "TestdataGenerator.bat (ou " + _c("python -m testdata_generator") + " sans option) ouvre la "
                "fenêtre avec des champs pour tous les paramètres. Seul le fichier de workflow est "
                "obligatoire ; le reste a des valeurs par défaut. La zone « Portefeuille démo » en bas "
                "construit la situation standard d'un clic — l'espace de données du chapitre 3 fait davantage.",
    "c8.win.fig": "Fig. 2 : Fenêtre du générateur classique pour un seul ART",
    "c8.wf.h": "8.2  Le fichier de workflow",
    "c8.wf.p": "Le fichier de workflow définit les étapes de votre tableau Jira et est le seul champ "
               "obligatoire. Il a le même format que dans transform_data — un fichier sert aux deux modules. "
               "Chaque ligne décrit une étape ; les alias (noms de statut alternatifs dans l'export Jira) sont "
               "séparés par des deux-points. Deux lignes spéciales marquent le début et la fin du travail actif :",
    "c8.wf.pre": "NomCanonique:Alias1:Alias2\n<First>PremiereEtapeActive\n<Closed>EtapeFermee",
    "c8.wf.col_line": "Ligne",
    "c8.wf.col_meaning": "Signification",
    "c8.wf.alias": "Étape avec un ou plusieurs noms de statut Jira alternatifs",
    "c8.wf.plain_name": "Nom (sans :)",
    "c8.wf.plain": "Étape sans alias",
    "c8.wf.first": "Première étape active — le cycle time commence ici",
    "c8.wf.closed": "Étape fermée — marque un ticket comme terminé",
    "c8.wf.example": "L'exemple fourni " + _c("workflow_ART_A.txt") + " modélise un workflow SAFe ART typique :",
    "c8.wf.notes": "« Funnel » a quatre alias — les quatre statuts Jira se normalisent en Funnel. Analysis est la "
                   "première étape active (le cycle time commence ici). Releasing compte comme fermé ; Done "
                   "(après Releasing) accueille aussi les tickets annulés.",
    "c8.par.h": "8.3  Référence des paramètres",
    "c8.par.p": "Tous les paramètres existent dans la fenêtre et en ligne de commande.",
    "c8.par.col_param": "Paramètre",
    "c8.par.col_default": "Défaut",
    "c8.par.col_desc": "Description",
    "c8.par.workflow": "Fichier de définition du workflow (.txt)",
    "c8.par.output": "Chemin du fichier de sortie",
    "c8.par.project": "Clé du projet Jira des tickets générés",
    "c8.par.issues": "Nombre de tickets",
    "c8.par.from": "Date de création la plus ancienne",
    "c8.par.to": "Date de transition la plus tardive",
    "c8.par.types": "Types de tickets avec pondérations (la somme n'a pas à faire 1)",
    "c8.par.completion": "Part des tickets atteignant l'étape fermée (0–1)",
    "c8.par.todo": "Part des tickets ouverts restant dans les premières étapes (0–1)",
    "c8.par.backflow": "Probabilité d'un pas en arrière par transition (0–1)",
    "c8.par.realism": "Désordre des parcours de statut : sauts, abandons, mises en attente, boucles, réouvertures ; environ 70 comme un vrai ART",
    "c8.par.seed": "Graine pour une sortie reproductible",
    "c8.par.mean": "Cycle time moyen en jours (log-normal) ; active le pilotage du cycle time",
    "c8.par.std_default": "30 % de la moyenne",
    "c8.par.std": "Écart-type du cycle time en jours",
    "c8.par.pattern": "Motif de flux : none / triangle / flat_triangle / cluster / batch (voir 8.4)",
    "c8.par.pi": "Longueur du PI en semaines (pour cluster et batch)",
    "c8.par.strength": "Intensité du motif (0 = subtil, 50 = défaut, 100 = fort)",
    "c8.par.continue": "Poursuivre un extrait antérieur jusqu'à --to-date : le passé reste octet pour octet, les tickets ouverts avancent, de nouveaux s'ajoutent ; nécessite --workflow",
    "c8.par.learn": "Apprendre un profil de transition depuis un vrai fichier de transitions (comptages et heures seulement) ; --transition-profile génère avec",
    "c8.pat.h": "8.4  Motifs de flux",
    "c8.pat.p": "Le générateur simule des anti-motifs de flux typiques issus des travaux de Vacanti et Singh. "
                "Combinez --mean-cycle-days avec --pattern ; la fenêtre offre des boutons radio et des curseurs.",
    "c8.pat.col_pattern": "Motif",
    "c8.pat.col_look": "Nuage de points",
    "c8.pat.col_desc": "Description",
    "c8.pat.none.look": "Nuage de points régulier",
    "c8.pat.none.desc": "Cycle time aléatoire sans tendance — comportement par défaut",
    "c8.pat.triangle.look": "Triangle, angle droit en bas à droite",
    "c8.pat.triangle.desc": "Le cycle time monte linéairement dans le temps (environ 1–4× à l'intensité par défaut). Un processus qui ralentit de plus en plus.",
    "c8.pat.flat.look": "Triangle, la montée s'aplatit",
    "c8.pat.flat.desc": "Comme triangle, la montée s'aplatit vers la fin. Une dégradation qui se stabilise.",
    "c8.pat.cluster.look": "Amas verticaux en fin de PI",
    "c8.pat.cluster.desc": "Le cycle time reste stable, mais la plupart des tickets se ferment dans les deux dernières semaines avant la fin du PI. Comportement dicté par l'échéance.",
    "c8.pat.batch.look": "Colonnes de hauteur variable en fin de PI",
    "c8.pat.batch.desc": "Comme cluster, mais avec un cycle time très variable (0,1× à 3× la moyenne). Tâches courtes et très longues sont poussées ensemble en fin de PI.",
    "c8.pat.hint": "--pattern exige --mean-cycle-days ; sans lui le motif est ignoré. "
                   "--std-cycle-days règle la dispersion, --pi-duration-weeks la longueur du PI pour cluster et batch.",
    "c8.ex.h": "8.5  ART_A — exemple complet",
    "c8.ex.p": "Du générateur au rapport fini sur le projet fictif ART_A :",
    "c8.ex.s1": "Étape 1 : Générer les données de test",
    "c8.ex.s2": "Étape 2 : Traiter avec transform_data",
    "c8.ex.s3": "Étape 3 : Créer le rapport avec build_reports",
    "c8.ex.expect": "<b>À quoi s'attendre (graine 42, 200 tickets) :</b><br/>"
                    "- Clés ART_A-0001 à ART_A-0200<br/>"
                    "- Types environ 120 Feature, 40 Bug, 40 Enabler<br/>"
                    "- Environ 150 tickets en Releasing ou Done<br/>"
                    "- Dates de création réparties sur 2025<br/>"
                    "- Pas en arrière occasionnels (backflow-prob 0.08 = environ 8 %)",

    # 9 -------------------------------------------------------------------
    "c9.h": "9  Questions fréquentes",
    "c9.q1": "Fenêtre ou navigateur — lequel prendre ?",
    "c9.a1": "La fenêtre. Elle produit le même espace de données et n'ouvre aucun port réseau. La page du "
             "navigateur seulement sur un ordinateur privé ; sur les ordinateurs d'entreprise, le logiciel de "
             "sécurité bloque et signale les serveurs locaux.",
    "c9.q2": "Pourquoi mon espace de données est-il en anglais alors que je parle français ?",
    "c9.a2": "Sans indication de langue, le générateur prend la langue de la suite du lanceur, sinon "
             "l'anglais. Réglez le lanceur sur le français, basculez en haut à droite ou passez --lang fr.",
    "c9.q3": "Le dossier cible n'est pas vide — que se passe-t-il ?",
    "c9.a3": "Le générateur demande. « Générer quand même » écrase les fichiers de même nom et laisse le reste ; "
             "« Choisir un autre dossier » abandonne.",
    "c9.q4": "La génération prend du temps.",
    "c9.a4": "À partir de 30 ARTs, ou au périmètre L avec plusieurs portefeuilles, l'encadré « Ce qui est "
             "produit » avertit. Pour la formation, la structure standard et le périmètre M suffisent "
             "(environ 10 secondes).",
    "c9.q5": "Données de test ou vraies données ?",
    "c9.a5": "Pour les démos, la formation et les tests d'installation, les données de test sont le meilleur "
             "choix — sans question de confidentialité. Les vraies analyses de flux et les décisions "
             "demandent de vraies données ; l'export manuel est décrit dans le manuel Get Data.",
    "c9.q6": "Puis-je régler certains ARTs différemment ?",
    "c9.a6": "Oui, via --art-profiles FICHIER.json en ligne de commande (chapitre 6). L'onglet correspondant "
             "dans l'interface suivra dans une bêta ultérieure.",

    # 10 ------------------------------------------------------------------
    "c10.h": "10  Glossaire",
    "c10.col_term": "Terme",
    "c10.col_expl": "Explication",
    "g.art.t": "ART",
    "g.art.e": "Agile Release Train — plusieurs équipes qui livrent ensemble dans SAFe",
    "g.dataspace.t": "Espace de données",
    "g.dataspace.e": "Un dossier avec tout ce dont une image de situation de portefeuille a besoin : configurations, exports, registres, états, briefings — autonome et déplaçable",
    "g.delta.t": "Briefing delta",
    "g.delta.e": "« Qu'est-ce qui a changé ? » entre deux états — débit, confiance, coutures, nouveaux risques",
    "g.conference.t": "Dossier de conférence",
    "g.conference.e": "Le dossier pour la value stream conference : problèmes de flux qui survivent aux conférences, avec l'image de situation",
    "g.seam.t": "Couture",
    "g.seam.e": "Une dépendance entre ARTs ou solutions où la pression se montre — au sein d'une solution ou entre value streams",
    "g.register.t": "Registre",
    "g.register.e": "Une liste par solution : risques, dépendances, hypothèses, NFR, runway, SLO, DORA, capacités, thèmes, problèmes de flux …",
    "g.stand.t": "État",
    "g.stand.e": "Un instantané figé de l'image de situation à une date ; les états sont espacés de 14 jours",
    "g.seed.t": "Graine",
    "g.seed.e": "Valeur de départ du générateur aléatoire — même graine, même sortie",
    "g.solution.t": "Solution",
    "g.solution.e": "Un groupe d'ARTs qui livrent ensemble une solution ; dans l'espace de données, le niveau avec ses propres registres",
    "g.stage_map.t": "Stage map",
    "g.stage_map.e": "Regroupement propre des étapes de workflow d'une solution (p. ex. amont/réalisation/terminé) au lieu du chemin par défaut",
    "g.value_stream.t": "Value stream",
    "g.value_stream.e": "Le flux du besoin à la valeur ; représenté dans l'espace de données par les solutions",
    "g.workflow.t": "Workflow",
    "g.workflow.e": "Suite ordonnée d'étapes qu'un ticket traverse ; décrite dans un fichier texte",
    "g.realism.t": "Réalisme",
    "g.realism.e": "Degré de désordre des parcours de statut : sauts, abandons, mises en attente, boucles, réouvertures",
    "g.cfd.t": "CFD",
    "g.cfd.e": "Cumulative Flow Diagram — stock par étape au fil du temps, cumulé",
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

OUTPUTS = {"de": OUTPUT_DE, "en": OUTPUT_EN, "ro": OUTPUT_RO, "pt": OUTPUT_PT, "fr": OUTPUT_FR}


def main() -> None:
    st = make_styles()
    for lang, output in OUTPUTS.items():
        story = [NextPageTemplate("normal")] + build_content(st, lang)
        doc = _TDGDoc(str(output), lang=lang)
        doc.multiBuild(story)
        print(f"PDF erstellt: {output}")


if __name__ == "__main__":
    main()
