# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Erzeugt die Installationsanleitung „Ollama auf Windows 11" als
#   separate PDF (DE + EN) — der Phase-0-Schritt der KI-Narration: ein
#   lokales Sprachmodell (Standard mistral-nemo) betriebsbereit machen,
#   ohne dass Daten den Rechner verlassen. Inhalt parallel zur
#   mkdocs-Seite docs/tutorials/install-ollama.md; Befehls-Blöcke sind
#   geteilte Konstanten, damit beide Sprachfassungen identisch bleiben.
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

_ACCENT = HexColor("#2b5b84")
_MUTED = HexColor("#555555")

_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=19,
                        leading=23, textColor=_ACCENT)
_TAGLINE = ParagraphStyle("tagline", fontName="Helvetica-Oblique",
                          fontSize=10, leading=13.5, textColor=_MUTED)
_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=13.5,
                     leading=17, spaceBefore=14, spaceAfter=4,
                     textColor=_ACCENT)
_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.6,
                       leading=13, spaceAfter=3)
_CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.4, leading=11,
                       backColor=HexColor("#f4f4f4"), borderPadding=6,
                       leftIndent=4, spaceBefore=4, spaceAfter=6)
_FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, leading=10,
                       textColor=_MUTED)

# ── Geteilte Befehls-Blöcke (in beiden Sprachfassungen identisch) ───────────

CODE_VERIFY = "ollama --version"

CODE_PULL = ("ollama pull mistral-nemo\n\n"
             "# Alternative fuer Rechner mit 8 GB RAM / for 8 GB machines:\n"
             "ollama pull mistral")

CODE_SMOKE = ('ollama run mistral-nemo "Antworte mit einem Satz: '
              'Was ist ein Lagebild?"\n'
              "# Chat beenden / leave the chat: /bye")

CODE_WIRING = ("python -m llm providers\n"
               "python -m llm test\n"
               "python -m llm test --lang en --model mistral")

CODE_USE = ("python -m portfolio --delta prev.json now.json --narrate "
            "--output delta.html --browser\n\n"
            "# Anderes Modell / different model:\n"
            "python -m portfolio --delta prev.json now.json --narrate "
            "--llm-model mistral --output delta.html")

CODE_MODELS_DIR = ('# Modelle auf D: statt C: ablegen / store models on D:\n'
                   'setx OLLAMA_MODELS "D:\\ollama-models"\n'
                   "# danach Ollama beenden und neu starten / then restart "
                   "Ollama")

# ── Inhalte je Sprache: (kind, text) mit kind in h1/p/li/code ───────────────

_DE = [
    ("h1", "1  Warum lokal?"),
    ("p", "Ollama betreibt Sprachmodelle vollständig auf dem eigenen "
          "Rechner. Für die KI-Narration des Lagebilds heißt das: Das "
          "Delta-Briefing verlässt nie das System, es braucht kein Konto, "
          "keinen API-Schlüssel und keine Konzern-Freigabe für externe "
          "Dienste. In Kennzeichnung und Betreiber-Nachweis erscheint "
          "dieser Weg als deployment_class „local“."),
    ("h1", "2  Voraussetzungen"),
    ("li", "Windows 11, 64-bit; keine Administratorrechte nötig (Ollama "
           "installiert sich ins Benutzerprofil)."),
    ("li", "Plattenplatz: ~4 GB für Ollama selbst plus Modell — "
           "mistral-nemo lädt rund 7 GB, mistral rund 4 GB."),
    ("li", "Arbeitsspeicher: 16 GB empfohlen für mistral-nemo (12B); mit "
           "8 GB das kleinere mistral (7B) wählen."),
    ("li", "Ohne Grafikkarte läuft alles auf der CPU — eine Narration "
           "dauert dann bis zu einer Minute; eine NVIDIA- oder AMD-GPU "
           "beschleunigt spürbar und wird automatisch genutzt."),
    ("h1", "3  Installieren"),
    ("li", "Im Browser ollama.com/download/windows öffnen und "
           "OllamaSetup.exe herunterladen."),
    ("li", "Die Datei per Doppelklick starten und dem Assistenten folgen — "
           "mehr Auswahl gibt es nicht."),
    ("li", "Danach läuft Ollama im Hintergrund; im Infobereich der "
           "Taskleiste erscheint das Lama-Symbol. Nach einem Neustart "
           "startet es automatisch mit."),
    ("p", "Prüfen, dass die Installation angekommen ist — PowerShell oder "
          "Eingabeaufforderung öffnen (Windows-Taste, „powershell“ "
          "tippen):"),
    ("code", CODE_VERIFY),
    ("h1", "4  Modell laden"),
    ("p", "Das Standardmodell der Narration ist mistral-nemo (12B, gutes "
          "Deutsch, Management-Ton). Der Download läuft einmalig:"),
    ("code", CODE_PULL),
    ("p", "Kurztest direkt in Ollama — die erste Antwort dauert am "
          "längsten, weil das Modell in den Speicher geladen wird:"),
    ("code", CODE_SMOKE),
    ("h1", "5  Verkabelungs-Check mit SituationReport"),
    ("p", "Im Repository- bzw. Release-Ordner zeigt die providers-Liste "
          "die entdeckten KI-Anbieter, und der test-Befehl macht eine "
          "erste gekennzeichnete Probe-Narration über Ollama:"),
    ("code", CODE_WIRING),
    ("h1", "6  Benutzen"),
    ("p", "CLI: --narrate ergänzt das Delta-Briefing um den Abschnitt "
          "„Narration (Entwurf)“ — inklusive KI-Kennzeichnung, "
          "Zahlen-Wächter und Betreiber-Nachweis (llm_audit.jsonl neben "
          "der Ausgabe). GUI: im Solutions-&-Portfolios-Fenster die "
          "Checkbox „KI-Narration (Entwurf)“ anhaken und daneben den "
          "Provider wählen, dann wie gewohnt „Delta-Briefing …“:"),
    ("code", CODE_USE),
    ("h1", "7  Wenn etwas hakt"),
    ("li", "„Could not reach Ollama“ / Verbindung abgelehnt: Ollama ist "
           "nicht gestartet — über das Startmenü „Ollama“ öffnen und auf "
           "das Lama-Symbol im Infobereich warten."),
    ("li", "„Ollama does not know model …“: das Modell fehlt noch — "
           "ollama pull mistral-nemo ausführen (Abschnitt 4)."),
    ("li", "Antwort dauert lange: auf reiner CPU ist bis zu einer Minute "
           "je Narration normal; mistral statt mistral-nemo halbiert die "
           "Wartezeit ungefähr."),
    ("li", "Platz auf C: knapp — Modellordner verlegen:"),
    ("code", CODE_MODELS_DIR),
    ("li", "Beenden: Rechtsklick auf das Lama-Symbol im Infobereich → "
           "„Quit Ollama“."),
    ("h1", "8  Datenschutz in einem Satz"),
    ("p", "Ollama lauscht nur auf dem eigenen Rechner "
          "(localhost:11434); weder Briefing noch Narration verlassen das "
          "System — der Unterschied zum externen Weg (Claude-API) bleibt "
          "über die deployment_class in Banner und Audit jederzeit "
          "sichtbar."),
]

_EN = [
    ("h1", "1  Why local?"),
    ("p", "Ollama runs language models entirely on your own machine. For "
          "the situation report's AI narration this means: the delta "
          "briefing never leaves the system, and you need no account, no "
          "API key and no corporate approval for external services. This "
          "path shows up as deployment_class \"local\" in the AI banner "
          "and the operator-evidence log."),
    ("h1", "2  Prerequisites"),
    ("li", "Windows 11, 64-bit; no administrator rights needed (Ollama "
           "installs into the user profile)."),
    ("li", "Disk space: ~4 GB for Ollama itself plus the model — "
           "mistral-nemo downloads about 7 GB, mistral about 4 GB."),
    ("li", "Memory: 16 GB recommended for mistral-nemo (12B); with 8 GB "
           "pick the smaller mistral (7B)."),
    ("li", "Without a GPU everything runs on the CPU — a narration then "
           "takes up to a minute; an NVIDIA or AMD GPU speeds things up "
           "noticeably and is used automatically."),
    ("h1", "3  Install"),
    ("li", "Open ollama.com/download/windows in the browser and download "
           "OllamaSetup.exe."),
    ("li", "Double-click the file and follow the wizard — there are no "
           "choices to make."),
    ("li", "Ollama then runs in the background; the llama icon appears in "
           "the taskbar's notification area. It starts automatically "
           "after a reboot."),
    ("p", "Verify the installation — open PowerShell or the command "
          "prompt (Windows key, type \"powershell\"):"),
    ("code", CODE_VERIFY),
    ("h1", "4  Pull the model"),
    ("p", "The narration's default model is mistral-nemo (12B, good "
          "multilingual quality, management tone). The download happens "
          "once:"),
    ("code", CODE_PULL),
    ("p", "Quick test directly in Ollama — the first answer takes longest "
          "because the model is loaded into memory:"),
    ("code", CODE_SMOKE),
    ("h1", "5  Wiring check with SituationReport"),
    ("p", "In the repository or release folder, the providers list shows "
          "the discovered AI backends, and the test command runs a first "
          "labeled sample narration through Ollama:"),
    ("code", CODE_WIRING),
    ("h1", "6  Use it"),
    ("p", "CLI: --narrate adds the \"Narration (Entwurf)\" section to the "
          "delta briefing — including the AI label, the numbers guard and "
          "the operator evidence (llm_audit.jsonl next to the output). "
          "GUI: in the Solutions & Portfolios window tick \"AI narration "
          "(draft)\", pick the provider next to it, then run \"Delta "
          "briefing …\" as usual:"),
    ("code", CODE_USE),
    ("h1", "7  Troubleshooting"),
    ("li", "\"Could not reach Ollama\" / connection refused: Ollama is "
           "not running — start \"Ollama\" from the Start menu and wait "
           "for the llama icon in the notification area."),
    ("li", "\"Ollama does not know model …\": the model is missing — run "
           "ollama pull mistral-nemo (section 4)."),
    ("li", "Answers are slow: on a pure CPU up to a minute per narration "
           "is normal; mistral instead of mistral-nemo roughly halves the "
           "wait."),
    ("li", "Low space on C: — relocate the model folder:"),
    ("code", CODE_MODELS_DIR),
    ("li", "Quit: right-click the llama icon in the notification area → "
           "\"Quit Ollama\"."),
    ("h1", "8  Privacy in one sentence"),
    ("p", "Ollama listens on your machine only (localhost:11434); "
          "neither briefing nor narration ever leaves the system — and "
          "the difference from the external path (Claude API) stays "
          "visible at all times via the deployment_class in banner and "
          "audit."),
]

_META = {
    "de": ("Ollama auf Windows 11 installieren",
           "Lokale KI für die Lagebild-Narration · Standardmodell "
           "mistral-nemo · ~15 Minuten plus Modell-Download · keine "
           "Admin-Rechte nötig",
           "ollama_Installationsanleitung_DE.pdf", _DE),
    "en": ("Installing Ollama on Windows 11",
           "Local AI for the situation-report narration · default model "
           "mistral-nemo · ~15 minutes plus model download · no admin "
           "rights needed",
           "ollama_Installationsanleitung_EN.pdf", _EN),
}


def _build(lang: str) -> Path:
    title, tagline, filename, content = _META[lang]
    path = Path(__file__).resolve().parent / filename
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=14 * mm,
        title=title, author="Robert Seebauer")
    story: list = [
        Paragraph(title, _TITLE),
        Spacer(1, 2 * mm),
        Paragraph(tagline, _TAGLINE),
        Spacer(1, 1 * mm),
        HRFlowable(width="100%", thickness=1, color=_ACCENT),
    ]
    for kind, text in content:
        if kind == "h1":
            story.append(Paragraph(text, _H1))
        elif kind == "p":
            story.append(Paragraph(text, _BODY))
        elif kind == "li":
            story.append(Paragraph(f"•  {text}", _BODY))
        elif kind == "code":
            story.append(Preformatted(text, _CODE))
    story += [
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=0.5, color=_MUTED),
        Paragraph(
            f"SituationReport {_VERSION} · BSD-3-Clause · "
            f"github.com/Jaegerfeld/situation-report · Online-Fassung: "
            f"jaegerfeld.github.io/situation-report", _FOOT),
    ]
    doc.build(story)
    return path


def main() -> None:
    for lang in _META:
        print(f"PDF erstellt: {_build(lang)}")


if __name__ == "__main__":
    main()
