# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Überblicksdokument „Testdaten-Generator 3" für ein Fachgespräch (Beta,
#   30.10.2026): vierzehn Querformat-Seiten als PDF — warum es den Generator
#   gibt, was ein Datenraum ist, die drei Schritte mit Screenshots beider
#   Oberflächen, Geschichten, Struktur, Stände, Rohdaten, KI-Entwürfe, die
#   Lehre aus dem Tester-Lauf und die Fragen an den Gesprächspartner.
#   Jede Seite trägt unten einen Gesprächsimpuls; das Dokument soll
#   besprechbar sein, nicht vollständig.
#
#   Aufruf: .venv/Scripts/python.exe docs/beta/generate_generator_overview.py
#   Ausgabe: docs/beta/Ueberblick_Testdaten-Generator_2026-10-30.pdf
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepInFrame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
sys.path.insert(0, str(DOCS))
sys.path.insert(0, str(DOCS.parent))
from _font_config import setup as _setup_fonts  # noqa: E402

from testdata_generator.scenario import _solution_tags  # noqa: E402
from testdata_generator.story import (  # noqa: E402
    STORY_TEMPLATES,
    SUGGESTED_STANDS,
    TEMPLATE_TITLES,
    bind_roles,
    story_for,
)
from testdata_generator.structure import structure_template  # noqa: E402

FN, FB, FI, _FBI = _setup_fonts()
PAGE = landscape(A4)
W, H = PAGE
MARGIN = 16 * mm
ACCENT = colors.HexColor("#1f6fa8")
DARK = colors.HexColor("#174f78")
INK = colors.HexColor("#23303e")
MUTED = colors.HexColor("#5b6b7c")
SOFT = colors.HexColor("#e3eef7")
LINE = colors.HexColor("#d9dee6")
OUT = HERE / "Ueberblick_Testdaten-Generator_2026-10-30.pdf"
STAND = "Beta-Stand 30.10.2026 · Branch beta/ux-redesign"

S = {
    "cover": ParagraphStyle("cover", fontName=FB, fontSize=30, leading=36, textColor=DARK),
    "cover_sub": ParagraphStyle("cover_sub", fontName=FN, fontSize=15, leading=20, textColor=MUTED),
    "h": ParagraphStyle("h", fontName=FB, fontSize=20, leading=24, textColor=DARK, spaceAfter=4),
    "lead": ParagraphStyle("lead", fontName=FN, fontSize=12, leading=16, textColor=MUTED, spaceAfter=8),
    "body": ParagraphStyle("body", fontName=FN, fontSize=11.5, leading=15.5, textColor=INK, spaceAfter=5),
    "li": ParagraphStyle("li", fontName=FN, fontSize=11.5, leading=15.5, textColor=INK, leftIndent=12,
                         bulletIndent=2, spaceAfter=3),
    "small": ParagraphStyle("small", fontName=FN, fontSize=9.5, leading=12.5, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName=FN, fontSize=9.5, leading=12.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=9.5, leading=12.5, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName=FB, fontSize=10, leading=13, textColor=DARK),
    "big": ParagraphStyle("big", fontName=FB, fontSize=24, leading=28, textColor=DARK),
    "biglbl": ParagraphStyle("biglbl", fontName=FN, fontSize=10, leading=13, textColor=MUTED),
    "impulse": ParagraphStyle("impulse", fontName=FI, fontSize=11.5, leading=15, textColor=DARK),
    "key": ParagraphStyle("key", fontName=FB, fontSize=14, leading=19, textColor=INK,
                          backColor=SOFT, borderPadding=10, spaceBefore=6, spaceAfter=10),
}


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def LI(text: str) -> Paragraph:
    return Paragraph(text, S["li"], bulletText="•")


def impulse(text: str) -> Table:
    """The discussion prompt at the foot of a page."""
    t = Table([[Paragraph("Zum Besprechen", S["cellh"]), Paragraph(text, S["impulse"])]],
              colWidths=[34 * mm, W - 2 * MARGIN - 34 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def two_columns(left: list, right: list, split: float = 0.5) -> Table:
    width = W - 2 * MARGIN
    lw = width * split
    t = Table([[left, right]], colWidths=[lw, width - lw])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 10),
                           ("LEFTPADDING", (1, 0), (1, 0), 10), ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    return t


def shot(name: str, width_mm: float, caption: str) -> list:
    path = HERE / name
    from PIL import Image as PILImage
    with PILImage.open(path) as img:
        ratio = img.height / img.width
    width = width_mm * mm
    return [Image(str(path), width=width, height=width * ratio), Spacer(1, 3), P(caption, "small")]


def grid(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(h, S["cellh"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, S["cellb"] if i == 0 else S["cell"]) for i, c in enumerate(row)])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def numbers(items: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(n, S["big"]) for n, _ in items], [Paragraph(label, S["biglbl"]) for _, label in items]]
    t = Table(data, colWidths=[(W - 2 * MARGIN) / len(items)] * len(items))
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
                           ("TOPPADDING", (0, 1), (-1, 1), 0)]))
    return t


_SCENARIO_LEAD = {
    "calm": "Die Nullmessung: ein Portfolio ohne Wendungen. Die Übung ist, ein ruhiges Bild als ruhig zu erkennen.",
    "standard": "Die Demo-Geschichte: stille Muster von Anfang an, die Wendungen mit dem letzten Stand.",
    "escalation": "Druck baut sich Stand für Stand auf — die Übung ist, den Zeitpunkt zu finden, an dem gehandelt werden musste.",
    "recovery": "Beginnt schlecht und heilt — die Übung ist, Wirkung von Maßnahmen im Delta zu lesen.",
}
_SCENARIO_PROMPT = {
    "calm": "Wie sieht in Ihrer Erfahrung „ruhig“ wirklich aus — und woran erkennt ein Stab, dass Ruhe trügt?",
    "standard": "Welche dieser stillen Muster kennen Sie aus Krisen, die lange vorher sichtbar waren? Welches fehlt?",
    "escalation": "Wie eskaliert eine Lage in Wirklichkeit — linear, in Sprüngen, mit Kaskaden? Wo läge der letzte gute Entscheidungszeitpunkt?",
    "recovery": "Woran erkennt man, dass eine Maßnahme wirkt und nicht nur die Zahl sich beruhigt? Welche Rückfälle fehlen hier?",
}


def _window(event, last: int) -> str:
    if event.stand_from <= 1 and (event.stand_to is None or event.stand_to >= last):
        return "alle Stände"
    if event.stand_to is None or event.stand_to >= last:
        return f"ab Stand {event.stand_from}" if event.stand_from < last else "letzter Stand"
    if event.stand_from == event.stand_to:
        return f"Stand {event.stand_from}"
    return f"Stand {event.stand_from}–{event.stand_to}"


def scenario_pages() -> list:
    """One page per story template, events and windows taken from the code itself."""
    portfolio = structure_template("standard").portfolios[0]
    binding = bind_roles(portfolio)
    tags = _solution_tags(portfolio)
    out: list = []
    for template in STORY_TEMPLATES:
        stands = SUGGESTED_STANDS[template]
        story = story_for(template, binding, tags, stands)
        rows = []
        for e in story.events:
            window = _window(e, stands) if e.enabled else "aus"
            rows.append([e.event_id, window, e.title, e.effect])
        # Ten events with their effects are tall: shrink to fit so the prompt stays on the page.
        content = [grid(["Nr.", f"Fenster ({stands} Stände)", "Was passiert", "Sichtbar als"], rows,
                        [12, 32, 92, 116])]
        body = [KeepInFrame(W - 2 * MARGIN, H - 28 * mm - 150, content, mode="shrink")]
        out += page(f"Szenario „{TEMPLATE_TITLES[template]}“",
                    _SCENARIO_LEAD[template] + " " + " ".join(story.summary), body,
                    _SCENARIO_PROMPT[template])
    return out


def page(title: str, lead: str, body: list, prompt: str) -> list:
    return [P(title, "h"), P(lead, "lead"), *body, Spacer(1, 8), impulse(prompt), PageBreak()]


def on_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, H - 6 * mm, W, 6 * mm, stroke=0, fill=1)
    canvas.setFont(FN, 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 9 * mm, f"SituationReport · Testdaten-Generator 3 · {STAND}")
    canvas.drawRightString(W - MARGIN, 9 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def build() -> Path:
    story: list = []

    # 1 Cover
    story += [Spacer(1, 40 * mm), P("Testdaten-Generator 3", "cover"),
              P("Demo-Datenräume auf Knopfdruck — für Schulung, Präsentation und Test eines Lagebilds", "cover_sub"),
              Spacer(1, 14 * mm),
              P("Überblick für ein Fachgespräch · vierzehn Seiten · jede Seite endet mit einer Frage zum Besprechen", "lead"),
              P(STAND, "small"), PageBreak()]

    # 2 Warum
    story += page(
        "Warum es den Generator gibt",
        "Ein Lagebild lebt von Daten. Echte Daten sind vertraulich, unvollständig oder noch nicht da.",
        [P("Wer ein Lagebild schult, vorführt oder testet, braucht Daten, die eine <b>erzählbare Lage</b> zeigen: "
           "ein Team, das aus dem Takt läuft; eine Datenquelle, der man nicht trauen kann; eine Naht zwischen "
           "zwei Wertströmen, die unter Druck gerät; ein Dienst, der seine Zusage reißt. In echten Daten sind "
           "diese Muster selten gleichzeitig da — und wenn, darf man sie nicht herumreichen."),
         P("Der Generator erzeugt auf Knopfdruck einen vollständigen <b>Demo-Datenraum</b>: dieselbe Form wie "
           "ein echter, erfundene Teams, eine gewählte Geschichte. Drei Regeln gelten immer:"),
         LI("<b>Keine Personen.</b> Owner und Melder sind Teams, ARTs und Wertströme."),
         LI("<b>Reproduzierbar.</b> Gleicher Seed, gleiche Struktur, gleiche Geschichte — gleicher Datenraum."),
         LI("<b>Die Register sind die Wahrheit.</b> Rohdaten und Stände werden aus ihnen abgeleitet, nie umgekehrt."),
         P("<b>Der wichtigste Satz:</b> Der Generator baut keine Zahlen, er baut eine Lage — und die Zahlen folgen ihr.", "key")],
        "Welche Lagen aus Ihrer Lean- und Krisenpraxis müsste ein Übungs-Datenraum erzählen können, damit eine "
        "Schulung etwas taugt?")

    # 3 Was entsteht
    story += page(
        "Was entsteht: ein Datenraum",
        "Ein Ordner mit allem, was die Suite für ein Portfolio lesen kann — Demo und echt haben dieselbe Form.",
        [numbers([("6", "ARTs in 2 Solutions (Standard-Struktur)"), ("22", "Register, 11 je Solution"),
                  ("6", "Stände im 14-Tage-Takt"), ("5", "Delta-Briefings, fertig gerendert"),
                  ("4", "Quellen-Arten mit Rohdaten")]),
         Spacer(1, 8),
         grid(["Baustein", "Inhalt", "Wofür"],
              [["Jira-Exporte und Arbeitsmappen", "je ART ein Export im Jira-Format, daraus die Arbeitsmappen der Metrikkette", "Fluss-Kennzahlen je Team und Solution"],
               ["Register je Solution", "Risiken (ROAM), Abhängigkeiten, NFRs und Runway, Capabilities, Entscheidungen und Annahmen, SLOs, Delivery (DORA), Flussprobleme, Themes, Solution Areas, Wecker", "Das Lagebild aus jeder Richtung"],
               ["Stände und Deltas", "eingefrorene Snapshots, dazwischen „was hat sich geändert?“", "Lage über Zeit, Konferenz-Übung"],
               ["Rohdaten der Provider", "Prometheus, GitHub oder GitLab, SonarQube, CSV — im Format der Systeme", "Die Kette vom System bis zum Register vorführen"],
               ["Struktur und Geschichte", "zwei Dateien: wer gehört zu wem, was passiert wann", "Reproduzierbar, erklärbar, weitergebbar"],
               ["README", "Struktur, Geschichte, Stände, Quellen, Befehle", "Wer den Ordner weitergibt, gibt die Erklärung mit"]],
              [52, 130, 70])],
        "Fehlt ein Register, das in Ihrer Krisenarbeit zuerst auf dem Tisch liegt — Lieferanten, Kapazität, "
        "Kommunikation, Entscheidungsvorlagen?")

    # 4 Drei Schritte
    story += page(
        "Bedienung: drei Schritte, ein Knopf",
        "Szenario wählen, Umfang festlegen, erzeugen. In unter einer Minute steht der Datenraum.",
        [two_columns(
            shot("testdaten-generator_web_schritt1.jpg", 130,
                 "Schritt 1: Vorlage der Geschichte, ihre Ereignisse mit Schalter, rechts die Struktur des Datenraums."),
            shot("testdaten-generator_web_ergebnis.jpg", 130,
                 "Schritt 3: Ergebniskarte mit vier Zahlen, der Geschichte in drei Sätzen und den nächsten Aktionen."))],
        "Was müsste auf der Ergebniskarte stehen, damit ein Krisenmanager sofort weiß, wo er hinschaut?")

    # 5 Geschichten
    story += page(
        "Die Geschichte als Daten: vier Vorlagen, zehn Ereignisse",
        "Ereignisse hängen an Rollen (der Ausreißer, die schwache Quelle, die Naht), nicht an Namen — und haben ein Fenster in der Zeit.",
        [grid(["Vorlage", "Für wen", "Was die Stände zeigen"],
              [["Ruhig", "die erste Schulung", "keine Wendungen; die Übung ist, ein Bild zu lesen, das nichts Dramatisches sagt — wer hier Alarm schlägt, hat überlesen"],
               ["Standard-Lage", "Präsentation, Tutorials", "Ausreißer, schwache Quelle, SLO-Bruch und stille Muster von Anfang an; die Wendungen mit dem letzten Stand"],
               ["Eskalation", "die Konferenz-Übung", "Druck steigt Stand für Stand: SLO-Bruch früh, blockierte Naht in der Mitte, Verfall und Cross-Solution-Nähte spät, neues Risiko zuletzt"],
               ["Erholung", "das Delta-Briefing", "beginnt schlecht und heilt: Nähte gelöst, SLO hält, der Ausreißer findet seinen Takt, die Datenquelle zuletzt"]],
              [34, 44, 174]),
         Spacer(1, 6),
         P("Jedes der zehn Ereignisse — Ausreißer, schwache Quelle, blockierte Naht, Cross-Solution-Druck, wiederkehrende "
           "Solution Area, SLO-Bruch, stille Muster, Verfall der Datenqualität, neues Risiko, geänderte Roadmaps — lässt "
           "sich einzeln abschalten. Dann zeigt das Register seinen gesunden Zustand, nicht eine Lücke."),
         P("Was fehlt, ist ehrlich benannt: Die Vorlagen stammen aus der Portfolio-Praxis, nicht aus dem Krisenstab.", "small")],
        "Welche Eskalationsmuster kennen Sie aus Krisen, die hier fehlen — Kaskaden, verspätete Meldungen, "
        "widersprüchliche Lagebilder, Entscheidungen ohne Wirkung?")

    # 5a–5d: one page per scenario, generated from the story templates
    story += scenario_pages()

    # 6 Struktur
    story += page(
        "Die Struktur als Daten: beliebig viele Portfolios, Solutions, ARTs",
        "Die Organisation eines Kunden lässt sich nachbauen, ohne seine Daten zu berühren.",
        [LI("Portfolios → Solutions → ARTs, je Solution ein Workflow (klassisch oder eigene Stage-Map), mindestens ein ART je Solution."),
         LI("Drei Vorlagen: Klein (1 · 1 · 2), Standard (1 · 2 · 3), Groß (5 Portfolios, 3–4 Solutions, 1–6 ARTs, zusammen 49 ARTs). Namen sind Vorschläge und änderbar."),
         LI("Die Geschichte bindet an <b>Positionen</b>: Der Ausreißer ist der letzte ART der ersten Solution, die schwache Quelle der letzte ART der zweiten. Umbenennen verschiebt nichts."),
         LI("Was die Struktur nicht hergibt, entfällt mit Hinweis statt Fehler: Eine Solution allein hat keine Cross-Solution-Naht; eine dritte Solution trägt nur die Grundmenge."),
         LI("Mehrere Portfolios bekommen je einen eigenen Datenraum; ein Lagebild <i>über</i> Portfolios hinweg ist heute kein Feature — die Daten dafür liegen schon nebeneinander."),
         Spacer(1, 4),
         P("Die Schätzung „Was entsteht“ rechnet aus der Struktur und warnt ab 30 ARTs vor der Dauer — sie verweigert nichts.")],
        "Wie groß ist die Einheit, auf der in Ihrer Erfahrung Krisen entschieden werden — Team, Zug, Solution, "
        "Portfolio, Konzern? Und wer sieht dort was?")

    # 7 Stände
    story += page(
        "Die Lage über die Zeit: Stände und Delta-Briefings",
        "Sechs Stände im 14-Tage-Takt, zu jedem Folgepaar ein fertiges Briefing: was hat sich geändert, was ist neu überfällig, welcher Wecker hat ausgelöst.",
        [LI("Jeder Stand ist ein eingefrorener Snapshot; die Reihe erzählt die gewählte Geschichte Stand für Stand. Eine Schulung kann bei Stand 1 beginnen und die Lage aufdecken."),
         LI("Das Delta-Briefing ist deterministisch: Durchsatz, Konfidenz je Quelle, Statuswechsel in allen Registern, neu Überfälliges — ohne Modell, ohne Deutung."),
         LI("Wecker (vereinbarte Entscheidungspunkte) werden je Stand ausgewertet: Welche Schwelle wurde wann gerissen, und was war die vereinbarte Reaktion?"),
         LI("Ehrlich benannt: Die Stände sind Aggregat-Reihen einer Geschichte, keine Vorgangs-Zeitreihe mit stabilen Schlüsseln — für Briefings, Wecker und Lagevortrag genau das, was gebraucht wird; für eine forensische Ticket-Historie nicht."),
         Spacer(1, 4),
         P("Ein Datenraum lässt sich fortschreiben: ein neuer Stand wird angehängt, das Delta dazu gerendert.")],
        "Welcher Rhythmus und welcher Blick zurück sind in einer Krise realistisch — täglich, wöchentlich, "
        "ereignisgetrieben? Was muss ein Delta-Briefing in 60 Sekunden sagen?")

    # 8 Rohdaten und KI
    story += page(
        "Die Kette vorführen: Rohdaten der Provider und KI-Entwürfe mit Leitplanken",
        "Vom Systemformat bis zum Register ohne Netz; KI-Texte nur als gekennzeichneter Entwurf.",
        [two_columns(
            [P("<b>Rohdaten im Format der Systeme</b>"),
             LI("Prometheus-Antworten, GitHub-Deployments und Pull Requests oder GitLab-DORA-Werte, SonarQube-Maße, eine SLO-CSV — so, wie die Systeme sie liefern würden."),
             LI("Die Provider der Suite lesen sie aus einer Aufzeichnung statt über das Netz; das Ergebnis gleicht dem Register. Wo ein Provider nur näherungsweise rechnet (GitHub), ist es benannt."),
             LI("Zweck: Die Kette „System → Abruf → Register → Lagebild“ ist in der Schulung sichtbar, ohne einen Zugang zu irgendeinem System.")],
            [P("<b>KI-Entwürfe (nur mit Schalter, standardmäßig aus)</b>"),
             LI("Lagevortrag-Entwurf, drei Antworten auf Fragen ans Lagebild, ein Prompt-Bündel und eine Übungsantwort mit absichtlich falschen Zahlen — erzeugt ohne Modell."),
             LI("Jeder Entwurf trägt den KI-Marker, keiner ist freigegeben; die Prüfung weist die falschen Zahlen zurück. So lassen sich Kennzeichnung, Freigabe und Rückweg üben."),
             LI("Eingabe (der Datenraum) und Ergebnis (die Entwürfe) liegen in getrennten Ordnern.")])],
        "Wo würden Sie in einem Krisenstab einem KI-Entwurf trauen — und wo nie? Was müsste die Prüfung zurückweisen?")

    # 9 Zwei Oberflächen, eine Lehre
    story += page(
        "Zwei Oberflächen, eine Dienstschicht — und eine Lehre aus dem ersten Test",
        "Browser-Seite und Fenster bedienen dieselbe Dienstschicht. Der erste Testlauf auf einem Firmenrechner entschied, welche der Standardweg ist.",
        [two_columns(
            shot("testdaten-generator_fenster_schritt1.jpg", 128,
                 "Das Fenster (tkinter): dieselben drei Schritte, ohne Server. Seit dem 30.10. der Standardweg."),
            [P("<b>Was der Test zeigte</b>"),
             LI("Die Browser-Seite läuft auf einem kleinen Server auf dem eigenen Rechner. Auf einem Firmenrechner wurde der Aufruf blockiert, danach meldete sich die Sicherheitsabteilung."),
             LI("Konsequenz innerhalb von vier Tagen: ein Fenster mit gleichem Funktionsumfang, nicht so schön, läuft überall, wo Python ist. Die Browser-Seite bleibt für private Rechner."),
             LI("Merke für die weitere Entwicklung: Kernfunktionen dürfen keinen lokalen Netzwerkport voraussetzen."),
             Spacer(1, 4),
             P("Was beide Oberflächen gemeinsam haben, ist der eigentliche Wert: eine Dienstschicht, die Anfrage, Schätzung, Lauf mit Fortschritt und Ergebnis kennt — jede künftige Oberfläche setzt darauf.", "small")],
            split=0.55)],
        "Welche Hürden kennen Sie aus Organisationen, bevor ein Werkzeug überhaupt auf den Tisch kommt — Sicherheit, "
        "Betriebsrat, Datenschutz, Lizenzen? Was müsste ein Werkzeug vorab beantworten?")

    # 10 Fragen und Ausblick
    story += [P("Woran wir arbeiten — und was wir von Ihnen lernen wollen", "h"),
              P("Offene Punkte der Beta und die Fragen, die den Nachmittag tragen sollen.", "lead"),
              two_columns(
                  [P("<b>Offen in der Beta</b>"),
                   LI("Schlankes Werkzeug für ein einzelnes Team (nach einem Nutzbarkeits-Audit)."),
                   LI("Weitere Nutzbarkeits-Audits der Suite, zuerst das Portfolio-Lagebild."),
                   LI("Rückmeldung der Tester zum Fenster auf Firmenrechnern."),
                   LI("Ein Einseiter DE/EN zum Generator für Entscheider."),
                   LI("Die Frage, ob und wie die ganze Suite eine neue Oberfläche bekommt — ohne lokale Netzwerkports.")],
                  [P("<b>Fragen an Sie</b>"),
                   LI("Welche <b>Lagen</b> aus Lean- und Krisenpraxis müsste der Generator erzählen können?"),
                   LI("Welche <b>Register</b> fehlen für einen Krisenstab — und welche sind Ballast?"),
                   LI("In welchem <b>Rhythmus</b> und mit welchem Rückblick wird in einer Krise entschieden?"),
                   LI("Was muss ein <b>Delta-Briefing</b> in 60 Sekunden sagen — und was darf es nie sagen?"),
                   LI("Wo ist ein <b>KI-Entwurf</b> im Stab hilfreich, wo gefährlich?"),
                   LI("Welche <b>Hürden</b> vor der Einführung kennen Sie, die wir heute nicht sehen?")]),
              Spacer(1, 10),
              P("Alles hier Gezeigte ist ein Beta-Stand; Zahlen und Screenshots stammen vom 26. und 30.10.2026. "
                "Die Geschichten sind Vorlagen, keine Beobachtungen; Namen und Teams sind erfunden.", "small")]

    doc = BaseDocTemplate(str(OUT), pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=14 * mm, bottomMargin=14 * mm,
                          title="Testdaten-Generator 3 — Überblick", author="Robert Seebauer")
    frame = Frame(MARGIN, 14 * mm, W - 2 * MARGIN, H - 28 * mm, id="main",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
    doc.build(story)
    return OUT


if __name__ == "__main__":
    print(f"PDF erstellt: {build()}")
