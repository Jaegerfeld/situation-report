# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt das Tutorial „KI-Funktionen der Phase 4 in der Praxis"
#   (D1 Executive Summary, D6 mehrsprachige Ausleitung, D5
#   Red-Team-Fragen) als PDF — Schritt für Schritt am Demo-Portfolio,
#   mit echten Bildschirmfotos aus der GUI und echten Modellausgaben
#   (mistral-nemo, lokal, inkl. eines echten Wächter-Treffers). Die
#   Bilder liegen unter docs/tutorial_assets/phase4/ und sind
#   mitversioniert, damit das PDF ohne laufende GUI reproduzierbar ist.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS))
sys.path.insert(0, str(DOCS.parent))

from _font_config import setup as _setup_fonts  # noqa: E402

try:
    from version import __version__ as _VERSION
except ImportError:  # pragma: no cover
    _VERSION = "?"

FN, FB, FI, _FBI = _setup_fonts()

ASSETS = DOCS / "tutorial_assets" / "phase4"
CONTENT_WIDTH = 175 * mm

ACCENT = colors.HexColor("#2b5b84")
BLUE = colors.HexColor("#1a3a56")
MUTED = colors.HexColor("#555555")
LIGHT = colors.HexColor("#eef3f8")

TITLE = ParagraphStyle("t", fontName=FB, fontSize=21, leading=25,
                       textColor=ACCENT)
SUB = ParagraphStyle("s", fontName=FI, fontSize=11, leading=15,
                     textColor=MUTED, spaceAfter=4)
H1 = ParagraphStyle("h1", fontName=FB, fontSize=15, leading=19,
                    spaceBefore=14, spaceAfter=6, textColor=ACCENT)
H2 = ParagraphStyle("h2", fontName=FB, fontSize=11.5, leading=15,
                    spaceBefore=10, spaceAfter=3, textColor=BLUE)
BODY = ParagraphStyle("b", fontName=FN, fontSize=9.9, leading=13.8,
                      spaceAfter=5)
BULLET = ParagraphStyle("li", fontName=FN, fontSize=9.9, leading=13.4,
                        leftIndent=13, spaceAfter=3)
STEP = ParagraphStyle("st", fontName=FN, fontSize=9.9, leading=13.6,
                      leftIndent=16, spaceAfter=4)
CODE = ParagraphStyle("c", fontName="Courier", fontSize=8.4, leading=11.4,
                      backColor=colors.HexColor("#f4f4f4"), borderPadding=6,
                      leftIndent=2, spaceBefore=3, spaceAfter=7)
CAPTION = ParagraphStyle("cap", fontName=FI, fontSize=8.6, leading=11.5,
                         textColor=MUTED, spaceBefore=3, spaceAfter=10)
BOXTXT = ParagraphStyle("bx", fontName=FN, fontSize=9.4, leading=13)
CELL = ParagraphStyle("cell", fontName=FN, fontSize=8.8, leading=11.6)
CELLH = ParagraphStyle("cellh", fontName=FB, fontSize=8.8, leading=11.6)


def P(text: str) -> Paragraph:
    return Paragraph(text, BODY)


def LI(text: str) -> Paragraph:
    return Paragraph("•&nbsp;&nbsp;" + text, BULLET)


def NUM(n: int, text: str) -> Paragraph:
    return Paragraph(f"<b>{n}.</b>&nbsp;&nbsp;{text}", STEP)


def H(text: str) -> Paragraph:
    return Paragraph(text, H1)


def H_(text: str) -> Paragraph:
    return Paragraph(text, H2)


def C(text: str) -> Preformatted:
    return Preformatted(text, CODE)


def BOX(text: str) -> Table:
    tbl = Table([[Paragraph(text, BOXTXT)]], colWidths=[CONTENT_WIDTH])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def TBL(rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(c, CELLH if r == 0 else CELL) for c in row]
            for r, row in enumerate(rows)]
    tbl = Table(data, colWidths=widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.4, MUTED),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def SHOT(name: str, caption: str, width_mm: float = 165) -> KeepTogether:
    """Screenshot mit Bildunterschrift, proportional skaliert."""
    from PIL import Image as PILImage

    path = ASSETS / f"{name}.png"
    with PILImage.open(path) as img:
        ratio = img.height / img.width
    width = width_mm * mm
    flow = Image(str(path), width=width, height=width * ratio)
    flow.hAlign = "LEFT"
    return KeepTogether([flow, Paragraph(caption, CAPTION)])


def _page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FN, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 12 * mm,
                      f"SituationReport {_VERSION} · Tutorial Phase 4 "
                      f"(D1 · D6 · D5)")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Seite {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Inhalt
# ---------------------------------------------------------------------------

def _intro() -> list:
    return [
        Paragraph("KI-Funktionen in der Praxis", TITLE),
        Spacer(1, 2 * mm),
        Paragraph("Phase 4 am Beispiel-Portfolio: Executive Summary (D1), "
                  "mehrsprachige Ausleitung (D6), Red-Team-Fragen (D5)",
                  SUB),
        HRFlowable(width="100%", thickness=1, color=ACCENT),
        Spacer(1, 3 * mm),
        P("Dieses Tutorial führt die drei KI-Funktionen der Phase 4 vor — "
          "Schritt für Schritt an einem Demo-Portfolio, das Sie in zwei "
          "Minuten selbst erzeugen. Alle Bildschirmfotos stammen aus der "
          "laufenden Anwendung, alle Textausgaben aus einem echten Lauf mit "
          "dem lokalen Modell <b>mistral-nemo</b> — inklusive eines "
          "Wächter-Treffers, den Sie im Alltag ebenfalls erleben werden."),
        H("Was die drei Funktionen tun"),
        LI("<b>D1 — Executive Summary:</b> macht aus der "
           "Management-Summary-Tabelle des Reports sechs bis neun Sätze "
           "Management-Prosa. Sie steht als gekennzeichneter Entwurf direkt "
           "unter der Tabelle."),
        LI("<b>D6 — Mehrsprachige Ausleitung:</b> liefert einen "
           "Lagebild-Text in den fünf Haussprachen (de, en, ro, pt, fr) — "
           "typischerweise den vom Menschen redigierten, freigegebenen "
           "Wortlaut."),
        LI("<b>D5 — Red-Team-Fragen:</b> erzeugt aus dem Decision- und "
           "Assumption-Log Premortem- und Angriffsfragen als Rohmaterial "
           "für eine moderierte Session. Nur Fragen — nie Empfehlungen."),
        Spacer(1, 2 * mm),
        BOX("<b>Der Satz, der alles zusammenhält:</b> Das Sprachmodell "
            "<i>textet</i>, es <i>rechnet nicht</i>. Jede Zahl in jedem "
            "Entwurf stammt wörtlich aus dem deterministischen Datenpfad — "
            "das erzwingt der Zahlen-Wächter, nicht die Hoffnung."),
        H("Voraussetzungen"),
        LI("SituationReport ab Version 0.26 (Phase 4 vollständig)."),
        LI("Für echte Modellausgaben ein lokal laufendes <b>Ollama</b> mit "
           "<font name='Courier'>ollama pull mistral-nemo</font> — siehe "
           "die separate Anleitung „Ollama auf Windows 11 installieren“. "
           "Alternativ Claude über die API (Schlüssel ausschließlich in der "
           "Umgebungsvariablen ANTHROPIC_API_KEY)."),
        LI("Zum reinen Ausprobieren genügt der Provider <b>mock</b>: eine "
           "klar gekennzeichnete Attrappe, ohne installiertes Modell."),
        H("Aufbau dieses Tutorials"),
        TBL([["Kapitel", "Inhalt"],
             ["1", "Das Beispiel-Portfolio erzeugen"],
             ["2", "Gemeinsame Grundlagen: Provider, Wächter, Nachweis"],
             ["3", "D1 — Executive Summary (GUI, Ergebnis, CLI, Grenzen)"],
             ["4", "D6 — Mehrsprachige Ausleitung"],
             ["5", "D5 — Red-Team-Fragen"],
             ["6", "Zusammenspiel im Alltag und Fehlerbilder"]],
            [22 * mm, 153 * mm]),
        PageBreak(),
    ]


def _chapter1() -> list:
    return [
        H("1  Das Beispiel-Portfolio in zwei Minuten"),
        P("Alle drei Funktionen brauchen Daten. Der Testdaten-Generator "
          "erzeugt ein komplettes Demo-Portfolio: zwei Solutions mit je "
          "drei ARTs, alle neun Register und zwei Snapshots für das "
          "Delta-Briefing."),
        SHOT("02_testdatengenerator",
             "Abb. 1: Testdaten-Generator. Der Bereich „Demo-Portfolio“ "
             "unten erzeugt den kompletten Datenraum; „Umfang“ steuert die "
             "Registergröße (s = nur Story-Anker, m = Standard, "
             "l = Stresstest).", 148),
        H_("So gehen Sie vor"),
        NUM(1, "Testdaten-Generator öffnen (Launcher oder "
                "<font name='Courier'>python -m testdata_generator</font>)."),
        NUM(2, "Unten im Bereich „Demo-Portfolio“ den Umfang wählen "
                "(<b>m</b> ist der sinnvolle Standard) und auf "
                "<b>„Demo-Portfolio erzeugen…“</b> klicken."),
        NUM(3, "Zielordner wählen — dieser Ordner ist danach ein "
                "vollständiger <b>Datenraum</b> und lässt sich als Ganzes "
                "verschieben, kopieren oder weitergeben."),
        P("Auf der Kommandozeile ist das ein Einzeiler:"),
        C("python -m testdata_generator --scenario portfolio \\\n"
          "    --output demo/ --seed 42 --scale m"),
        H_("Optional: die ARTs feiner einstellen"),
        P("Über <b>„ART-Profile…“</b> stellen Sie je ART dieselben Regler "
          "ein wie bei der Einzel-ART-Erzeugung — durchschnittliche "
          "Cycle Time und Streuung, Quoten, Backflow, Fluss- bzw. "
          "Fehlermuster samt Stärke. Leere Felder bleiben Standard; die "
          "eingebauten Geschichten (Alpha-3 als Ausreißer, Beta-3 als "
          "schwache Quelle) ändern sich nur, wenn Sie deren Vorgaben "
          "bewusst überschreiben."),
        SHOT("02b_art_profile",
             "Abb. 2: Der Dialog „ART-Profile“, vorbefüllt mit den "
             "Standardwerten des Demo-Portfolios.", 148),
        PageBreak(),
    ]


def _chapter2() -> list:
    return [
        H("2  Gemeinsame Grundlagen aller drei Funktionen"),
        P("D1, D6 und D5 laufen über dieselbe KI-Schicht. Wer eine davon "
          "verstanden hat, kann alle drei bedienen — und alle drei "
          "unterliegen denselben Sicherungen."),
        H_("Wo Sie den Provider wählen"),
        P("Im Fenster „Solutions &amp; Portfolios“ sitzt unter dem "
          "Report-Modus eine eigene KI-Zeile: die Checkbox <b>„KI-Narration "
          "(Entwurf)“</b>, daneben die Provider-Auswahl und die beiden "
          "Knöpfe für Red-Team-Fragen und Übersetzung."),
        SHOT("01b_ki_zeile",
             "Abb. 3: Die KI-Zeile (vergrößert). Die Provider-Auswahl gilt "
             "für alle KI-Aktionen des Fensters: ollama (lokal), claude "
             "(extern), mock (Attrappe ohne Modell).", 170),
        H_("Die drei Wächter — in jeder Funktion identisch"),
        LI("<b>Zahlen-Wächter:</b> Jede Zahl im erzeugten Text muss "
           "wörtlich in der Vorlage stehen. Sonst wird der Text verworfen — "
           "lieber kein Entwurf als ein falscher."),
        LI("<b>Kennzeichnung (Art. 50 KI-VO):</b> Jeder Entwurf trägt "
           "sichtbar Modell, Deployment-Klasse und Prompt-Version und "
           "behauptet nie eine Freigabe. Die erteilt erst der Mensch, der "
           "redigiert."),
        LI("<b>Betreiber-Nachweis:</b> Jede Anfrage landet als Zeile in "
           "<font name='Courier'>llm_audit.jsonl</font> neben der Ausgabe — "
           "mit Zweck, Modell, Dauer und SHA-256-Hashes, nie mit Volltexten "
           "und nie mit Schlüsseln."),
        SHOT("40_audit",
             "Abb. 4: Der Nachweis eines Tutorial-Nachmittags. Zeile 1 zeigt "
             "einen echten Wächter-Treffer (Spalte „Wächter ok“ = NEIN): Das "
             "Modell hatte eine Zahl erfunden, der Entwurf wurde verworfen. "
             "Die letzte Zeile ist der erfolgreiche Neuversuch derselben "
             "Eingabe — erkennbar am identischen Eingabe-Hash.", 170),
        BOX("<b>Lokal oder extern?</b> Mit <b>ollama</b> verlässt kein "
            "Zeichen Ihren Rechner — kein Konto, kein Schlüssel, keine "
            "Konzern-Freigabe nötig. Mit <b>claude</b> geht der Text an die "
            "Anthropic-API; das steht sichtbar im Banner und im Nachweis "
            "(deployment_class „external_api“). Die Wahl ist Konfiguration, "
            "nicht Zufall."),
        PageBreak(),
    ]


def _chapter_d1() -> list:
    return [
        H("3  D1 — Die Executive Summary des Reports"),
        P("Die Management-Summary-Tabelle beantwortet „wie viel?“ in Zahlen. "
          "Die Executive Summary beantwortet dieselbe Frage in Sätzen — für "
          "Leser, die keine Tabellen lesen, und als Rohtext für Ihre eigene "
          "Berichterstattung."),
        H_("Was das Modell sieht (und was nicht)"),
        P("Eingabe ist ausschließlich ein <b>deterministischer "
          "Kennzahlen-Contract</b>, den derselbe Datenpfad erzeugt wie "
          "Report und Snapshots: gepoolte Kennzahlen, Kennzahlen je "
          "Einheit, Quell-Konfidenz und die Governance-Kopfzahlen als "
          "Statuszählungen. Ein Ausschnitt:"),
        C("# Executive-Summary-Contract - Demo Portfolio (portfolio)\n"
          "As of 2026-09-04; cycle-time target 90 days.\n"
          "\n"
          "## Overall (pooled)\n"
          "- Demo Portfolio: items 660, completed 420, open 240,\n"
          "  median CT 8.0 d, P85 18.1 d, P95 32.7 d, ...\n"
          "\n"
          "## Source confidence\n"
          "- ART Beta-3: low (data as of 2026-07-02)\n"
          "\n"
          "## Governance head counts\n"
          "- risks: 29 (accepted 4, mitigated 4, owned 11, resolved 10)"),
        BOX("<b>Personen kommen im Contract nicht vor.</b> Owner-Felder "
            "werden gar nicht erst übergeben — selbst wenn jemand in ein "
            "Register versehentlich einen Personennamen schreibt, erreicht "
            "er das Modell nie. Das ist keine Zusage, sondern durch einen "
            "Test abgesichert."),
        H_("So lösen Sie D1 in der GUI aus"),
        NUM(1, "„Solutions &amp; Portfolios“ öffnen und mit <b>„Laden …“</b> "
                "die <font name='Courier'>portfolio.json</font> aus Ihrem "
                "Demo-Ordner öffnen."),
        NUM(2, "In der KI-Zeile <b>„KI-Narration (Entwurf)“</b> ankreuzen "
                "und den Provider wählen (<b>ollama</b> für den echten "
                "Lauf, <b>mock</b> zum Ausprobieren)."),
        NUM(3, "Rechts auf <b>„Report erzeugen …“</b> klicken und einen "
                "Dateinamen mit der Endung <b>.html</b> wählen."),
        NUM(4, "Warten: Die Statuszeile meldet „KI-Narration wird erzeugt“. "
                "Lokale Modelle brauchen dafür 30 bis 120 Sekunden."),
        PageBreak(),
        SHOT("01_gui_geladen",
             "Abb. 5: Das geladene Demo-Portfolio. Unten die angehakte "
             "Checkbox mit Provider-Auswahl, rechts der Knopf „Report "
             "erzeugen …“. Die Statuszeile bestätigt die geladene "
             "Konfiguration.", 170),
        H_("Das Ergebnis im Report"),
        P("Der Abschnitt <b>„Executive Summary (Entwurf)“</b> steht direkt "
          "unter der Management-Summary-Tabelle — dort, wo der Leser die "
          "Zahlen gerade gesehen hat. Der gelbe Kasten ist die "
          "Pflicht-Kennzeichnung: Modell, Deployment-Klasse, "
          "Prompt-Version und der ausdrückliche Hinweis, dass ein Mensch "
          "redigieren und freigeben muss."),
        SHOT("10_report_execsummary",
             "Abb. 6: Echte Ausgabe von mistral-nemo (lokal). Jede Zahl im "
             "Text — 660, 420, 8.0, 100.0 % — steht wörtlich im Contract; "
             "der Zahlen-Wächter hat das vor dem Schreiben geprüft.", 170),
        PageBreak(),
        H_("Die Entwurfsdatei zum Redigieren"),
        P("Neben dem Report entsteht eine zweite Datei: "
          "<font name='Courier'>&lt;report&gt;.html.exec_summary.md</font>. "
          "Sie enthält denselben Text als Markdown — Ihr Arbeitsexemplar. "
          "Redigieren Sie dort: kürzen, gewichten, die "
          "Governance-Aufzählung streichen, wenn sie für den Adressaten "
          "irrelevant ist. Erst diese redigierte Fassung ist „freigegeben“ "
          "— und erst sie sollten Sie weitergeben oder übersetzen "
          "(Kapitel 4)."),
        SHOT("11_execsummary_md",
             "Abb. 7: Die Entwurfsdatei. Die erste Zeile trägt die "
             "Kennzeichnung als Zitat — sie bleibt stehen, bis ein Mensch "
             "den Text freigibt.", 170),
        H_("Dasselbe auf der Kommandozeile"),
        C("python -m portfolio demo/portfolio.json \\\n"
          "    --output report.html --narrate ollama --llm-lang de\n"
          "\n"
          "# erzeugt zusaetzlich:\n"
          "#   report.html.exec_summary.md   (Entwurf zum Redigieren)\n"
          "#   llm_audit.jsonl               (Betreiber-Nachweis)"),
        H_("Grenzen, die Sie kennen sollten"),
        LI("<b>Nur HTML.</b> Bei einem reinen PDF-Lauf gibt die CLI einen "
           "Hinweis aus und erzeugt keinen Entwurf — die Einbettung hängt "
           "an der HTML-Struktur."),
        LI("<b>Der Wächter kann zuschlagen.</b> Erfindet das Modell eine "
           "Zahl, wird der Entwurf verworfen; in der GUI entsteht der "
           "Report trotzdem (ohne Abschnitt), und die Statuszeile nennt den "
           "Grund. Ein zweiter Versuch hilft meist — siehe Kapitel 6."),
        LI("<b>Der Ton bleibt Ihre Verantwortung.</b> Das Modell referiert; "
           "es gewichtet nicht, was für Ihr Publikum wichtig ist. Genau "
           "dafür ist es ein Entwurf."),
        PageBreak(),
    ]


def _chapter_d6() -> list:
    return [
        H("4  D6 — Dieselbe Lage in fünf Sprachen"),
        P("Internationale Solutions brauchen dasselbe Lagebild in mehreren "
          "Sprachen. D6 leitet einen Text nach de, en, ro, pt oder fr aus — "
          "über denselben gewächterten Pfad wie alle anderen "
          "KI-Funktionen."),
        BOX("<b>Die Reihenfolge entscheidet über die Qualität:</b> erst "
            "redigieren und freigeben, <i>dann</i> ausleiten. So stammen "
            "alle Sprachfassungen vom selben freigegebenen Wortlaut — die "
            "gelebte Praxis der Handbücher dieses Projekts."),
        H_("Warum die Zahlen-Invariante hier besonders gut passt"),
        P("Eine Übersetzung darf per Definition keine neue Zahl enthalten. "
          "Genau das prüft der Zahlen-Wächter: Jede Zahl der Übersetzung "
          "muss wörtlich in der Vorlage vorkommen. Zusätzlich verlangt der "
          "Prompt, Eigennamen (Team-, ART-, Service-Namen) unübersetzt zu "
          "lassen und die Absatzstruktur zu erhalten."),
        H_("So lösen Sie D6 in der GUI aus"),
        NUM(1, "In der KI-Zeile den Provider wählen und auf "
                "<b>„Übersetzen …“</b> klicken."),
        NUM(2, "Die Textdatei wählen — typischerweise Ihre <b>redigierte</b> "
                "<font name='Courier'>…exec_summary.md</font> oder "
                "<font name='Courier'>…narration.md</font>."),
        NUM(3, "Im Dialog die Zielsprachen ankreuzen (Mehrfachauswahl "
                "möglich) und mit OK bestätigen."),
        NUM(4, "Je Sprache entsteht neben der Vorlage eine Datei "
                "<font name='Courier'>&lt;datei&gt;.&lt;lang&gt;.md</font>; "
                "die Statuszeile listet die fertigen Sprachen auf."),
        SHOT("03_dialog_sprachen",
             "Abb. 8: Die Zielsprachen-Auswahl. Mehrere Sprachen in einem "
             "Durchgang; jede bekommt einen eigenen Nachweis-Eintrag.", 62),
        PageBreak(),
        H_("Das Ergebnis"),
        SHOT("20_uebersetzungen",
             "Abb. 9: Englische und französische Fassung derselben Executive "
             "Summary (echte mistral-nemo-Ausgabe). Beachten Sie die "
             "Kennzeichnung: Sie steht jeweils in der ZIELsprache — "
             "„unreviewed draft“ bzw. „non relu“.", 174),
        H_("Dasselbe auf der Kommandozeile"),
        C("# Der Redaktions-Weg: eine freigegebene Datei ausleiten\n"
          "python -m llm translate report.html.exec_summary.md \\\n"
          "    --to en fr --llm ollama\n"
          "\n"
          "# Direkt am Lauf mitliefern (Entwurf bzw. Briefing):\n"
          "python -m portfolio --delta prev.json now.json --narrate \\\n"
          "    --translate en ro --output delta.html"),
        H_("Was wobei übersetzt wird"),
        TBL([["Lauf", "Übersetzt wird", "Dateiname"],
             ["Report mit --narrate", "die Executive Summary",
              "…exec_summary.&lt;lang&gt;.md"],
             ["Delta mit --narrate", "der Narrations-Entwurf",
              "…narration.&lt;lang&gt;.md"],
             ["Delta ohne --narrate",
              "das deterministische Briefing selbst",
              "….&lt;lang&gt;.md"],
             ["llm translate DATEI", "genau diese Datei",
              "&lt;datei&gt;.&lt;lang&gt;.md"]],
            [42 * mm, 78 * mm, 55 * mm]),
        Spacer(1, 4 * mm),
        P("Der dritte Fall ist der stärkste: Ein Briefing ohne KI ist "
          "vollständig deterministisch — die Übersetzung macht daraus einen "
          "Text, der in jeder Sprache dieselben Zahlen trägt, ohne dass je "
          "ein Modell etwas formuliert hätte."),
        PageBreak(),
    ]


def _chapter_d5() -> list:
    return [
        H("5  D5 — Red-Team-Fragen aus dem Decision-Log"),
        P("Gute Stäbe greifen ihre eigenen Entscheidungen und Annahmen an, "
          "bevor die Realität es tut. Nur fehlt dafür meist die Zeit — und "
          "der unbefangene Blick. D5 erzeugt aus dem Decision- und "
          "Assumption-Log (Register B4) Fragen, mit denen eine moderierte "
          "Session sofort starten kann."),
        H_("Zwei Blickrichtungen"),
        LI("<b>Für Entscheidungen: Premortem.</b> „Angenommen, diese "
           "Entscheidung ist in sechs Monaten gescheitert — wodurch?“ Die "
           "Frage kehrt die Beweislast um und macht stille Voraussetzungen "
           "sichtbar."),
        LI("<b>Für Annahmen: direkter Angriff.</b> „Was müsste wahr sein, "
           "damit die Annahme kippt — und woran würde man das früh "
           "erkennen?“ Das verwandelt eine Annahme in einen beobachtbaren "
           "Frühindikator."),
        H_("So lösen Sie D5 in der GUI aus"),
        NUM(1, "Die Solution oder das Portfolio laden, deren Log Sie "
                "angreifen wollen (die Config muss ein Decision-Log "
                "referenzieren — im Demo-Portfolio ist das der Fall)."),
        NUM(2, "In der KI-Zeile den Provider wählen und auf "
                "<b>„Red-Team-Fragen …“</b> klicken."),
        NUM(3, "Dateinamen bestätigen (vorgeschlagen wird "
                "<font name='Courier'>&lt;Name&gt;_RedTeam_"
                "&lt;Datum&gt;.md</font>)."),
        NUM(4, "Die Statuszeile meldet den fertigen Entwurf. Fehlt das "
                "Decision-Log, sagt die Meldung genau das — keine leere "
                "Datei."),
        H_("Das Ergebnis"),
        SHOT("30_redteam_md",
             "Abb. 10: Echte mistral-nemo-Ausgabe zum Demo-Log. Je "
             "Log-Eintrag eine Überschrift mit ID und Kontext, darunter ein "
             "bis drei Fragen — und ausschließlich Fragen.", 172),
        PageBreak(),
        H_("Der Fragen-Wächter: warum hier nie eine Empfehlung steht"),
        P("Die KI-Denkschrift ordnet D5 dem <b>Urteil</b> zu — und Urteile "
          "automatisiert dieses Werkzeug nicht. Damit das keine Absichts"
          "erklärung bleibt, prüft ein zweiter Wächter jede Ausgabe: Jede "
          "Zeile, die mit „- “ beginnt, muss mit einem Fragezeichen enden. "
          "Rutscht dem Modell eine Empfehlung durch, wird der gesamte "
          "Entwurf verworfen."),
        C("Red-team draft discarded: it contains list lines that are not\n"
          "questions — D5 delivers raw material for judgement, never\n"
          "judgements. Offending line(s): - Empfehlung: Entscheidung ..."),
        P("Das Werkzeug <i>kann</i> Ihnen also keine Handlungsempfehlung "
          "ausliefern, selbst wenn das Modell es versuchte. Was Sie "
          "bekommen, ist Material für Ihre Moderation — Auswahl, "
          "Reihenfolge und Antworten bleiben bei den Menschen im Raum."),
        H_("Dasselbe auf der Kommandozeile"),
        C("python -m portfolio demo/solutions/alpha/solution.json \\\n"
          "    --red-team fragen.md --narrate ollama --llm-lang de"),
        H_("Wie Sie die Fragen in einer Session einsetzen"),
        NUM(1, "Vor der Session erzeugen und <b>ungelesen</b> an die "
                "Moderation geben — so entsteht kein Anker durch die "
                "Vorauswahl einer Person."),
        NUM(2, "In der Session je Eintrag höchstens eine Frage stellen; "
                "die anderen sind Reserve, wenn die Diskussion stockt."),
        NUM(3, "Antworten gehören zurück ins Log — als neue Annahme mit "
                "Prüfdatum oder als Entscheidung, die eine ältere ersetzt. "
                "Das nächste Delta-Briefing zeigt die Bewegung dann von "
                "selbst."),
        PageBreak(),
    ]


def _chapter6() -> list:
    return [
        H("6  Zusammenspiel im Alltag"),
        P("Die drei Funktionen entfalten ihren Wert in einer festen "
          "Reihenfolge — sie bauen aufeinander auf:"),
        TBL([["Wann", "Was", "Womit"],
             ["Vor der Konferenz", "Fragen für den Angriff auf "
              "Entscheidungen und Annahmen", "D5 „Red-Team-Fragen …“"],
             ["Report erstellen", "Executive Summary als Entwurf",
              "D1 Checkbox + „Report erzeugen …“"],
             ["Nach der Redaktion", "freigegebenen Text in die "
              "Sprachen der Adressaten", "D6 „Übersetzen …“"]],
            [38 * mm, 80 * mm, 57 * mm]),
        Spacer(1, 4 * mm),
        BOX("<b>Freigabe zuletzt.</b> Kein Text dieser drei Funktionen "
            "verlässt Ihr Haus, ohne dass ein Mensch ihn gelesen, "
            "redigiert und bewusst freigegeben hat. Die Kennzeichnung im "
            "Entwurf sagt das ausdrücklich — sie zu entfernen ist der "
            "letzte Schritt Ihrer Redaktion, nicht der erste."),
        H("Fehlerbilder und was dahintersteckt"),
        TBL([["Meldung / Beobachtung", "Ursache und Abhilfe"],
             ["„Narration discarded: the model invented number(s) …“",
              "Der Zahlen-Wächter hat eine erfundene Zahl gefunden und den "
              "Entwurf verworfen — das System arbeitet korrekt. Lauf "
              "wiederholen; hilft das nicht, größeres Modell wählen oder "
              "den deterministischen Text ohne KI verwenden."],
             ["„Could not reach Ollama …“",
              "Ollama läuft nicht. Über das Startmenü starten und auf das "
              "Lama-Symbol im Infobereich warten."],
             ["„Ollama does not know model …“",
              "Modell fehlt: <font name='Courier'>ollama pull "
              "mistral-nemo</font>."],
             ["Der Entwurf kommt in der falschen Sprache",
              "Behoben ab v0.27: Die Prompts legen die Ausgabesprache "
              "ausdrücklich fest. In älteren Versionen antwortete das "
              "Modell mitunter Englisch, weil die Kennzahlen englisch "
              "beschriftet sind."],
             ["Der Lauf dauert „ewig“",
              "Lokale Modelle rechnen auf der CPU 30–120 Sekunden je "
              "Entwurf. Die Statuszeile weist darauf hin; die GUI bleibt "
              "bedienbar, weil die Erzeugung im Hintergrund läuft."],
             ["Red-Team-Fragen fehlen ganz",
              "Die Config referenziert kein Decision-Log. In „Datenquellen "
              "…“ das Register eintragen (im Demo-Portfolio bereits "
              "vorhanden)."]],
            [50 * mm, 125 * mm]),
        H("Was Sie mitnehmen sollten"),
        LI("Die KI ist <b>Zusatz, nie Voraussetzung</b>: Ohne Häkchen und "
           "ohne Knopfdruck bleibt jedes Artefakt exakt so, wie es der "
           "deterministische Kern erzeugt."),
        LI("<b>Jeder Entwurf ist gekennzeichnet</b> und jeder Lauf "
           "nachweisbar — auch der misslungene."),
        LI("<b>Zahlen kommen nie aus dem Modell.</b> Wo eine Zahl steht, "
           "steht sie so auch im Datenpfad."),
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=0.5, color=MUTED),
        Paragraph(
            f"SituationReport {_VERSION} · BSD-3-Clause · "
            f"github.com/Jaegerfeld/situation-report · Alle Bildschirmfotos "
            f"und Modellausgaben stammen aus einem echten Lauf am "
            f"Demo-Portfolio (Seed 42, Umfang m, mistral-nemo lokal).",
            CAPTION),
    ]


def content_de() -> list:
    return (_intro() + _chapter1() + _chapter2() + _chapter_d1()
            + _chapter_d6() + _chapter_d5() + _chapter6())


def main() -> None:
    out = DOCS / "Phase4_Tutorial_KI-Funktionen_DE.pdf"
    doc = SimpleDocTemplate(
        str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=17 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm,
        title="KI-Funktionen in der Praxis (D1, D6, D5)",
        author="Robert Seebauer")
    doc.build(content_de(), onFirstPage=_page, onLaterPages=_page)
    print(f"PDF erstellt: {out}")


if __name__ == "__main__":
    main()
