# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prompt-Export (Auftrag Robert 13.10.2026): An jeder KI-Stelle soll sich
#   der komplette Prompt — Systemprompt plus deterministischer Contract —
#   in eine Datei und die Zwischenablage legen lassen, statt ein Modell
#   aufzurufen. So lässt er sich zusammen mit einem Export des Dokuments
#   auf einem anderen Rechner oder Modell ausführen; die Antwort wird dann
#   von Hand in die Entwurfsdatei eingefügt und wie jeder Entwurf redigiert.
#   Hier steht das Bündel-Format; der Provider "export" (llm/providers/
#   export.py) benutzt es und ist damit an allen Stellen verfügbar, die über
#   llm.narrate laufen (D1, D2, D5, D6, D8, P3).
# =============================================================================

from __future__ import annotations

from datetime import datetime
from pathlib import Path

BUNDLE_SCHEMA = "prompt-export/1"

_HEAD = {
    "de": (
        "# Prompt-Export — {purpose} — {stamp}\n\n"
        "Erzeugt von SituationReport ({schema}). Kein Modell wurde aufgerufen.\n\n"
        "**So geht es weiter:** (1) Den Abschnitt „Systemprompt“ als Systemanweisung des "
        "Modells setzen. (2) Den Abschnitt „Eingabe“ als Nutzer-Nachricht senden — er ist "
        "der vollständige Contract, mehr darf das Modell nicht wissen. (3) Die Antwort in "
        "die Entwurfsdatei neben der Ausgabe einfügen (`{draft}`) und wie jeden KI-Entwurf "
        "redigieren, bevor sie verwendet wird. Zahlen in der Antwort müssen wörtlich in der "
        "Eingabe stehen — ein Modell, das rechnet, ist hier falsch.\n\n"
        "Sprache des Entwurfs: {lang}.\n"
    ),
    "en": (
        "# Prompt export — {purpose} — {stamp}\n\n"
        "Produced by SituationReport ({schema}). No model was called.\n\n"
        "**Next steps:** (1) Use the section “System prompt” as the model's system "
        "instruction. (2) Send the section “Input” as the user message — it is the complete "
        "contract, the model must know nothing beyond it. (3) Paste the answer into the "
        "draft file next to the output (`{draft}`) and edit it like every AI draft before "
        "use. Numbers in the answer must appear verbatim in the input — a model that "
        "computes is wrong here.\n\n"
        "Draft language: {lang}.\n"
    ),
}
_SECTIONS = {
    "de": ("## Systemprompt", "## Eingabe (Contract)"),
    "en": ("## System prompt", "## Input (contract)"),
}


def build_bundle(system: str, prompt: str, purpose: str, lang: str = "de",
                 draft_name: str = "<ausgabe>.narration.md",
                 stamp: datetime | None = None) -> str:
    """The exported text: instructions, system prompt, input contract."""
    key = "de" if lang == "de" else "en"
    stamp = stamp or datetime.now()
    head = _HEAD[key].format(purpose=purpose, stamp=stamp.strftime("%Y-%m-%d %H:%M"),
                             schema=BUNDLE_SCHEMA, draft=draft_name, lang=lang)
    sys_h, in_h = _SECTIONS[key]
    return (f"{head}\n{sys_h}\n\n```text\n{system.strip()}\n```\n\n"
            f"{in_h}\n\n```markdown\n{prompt.strip()}\n```\n")


def bundle_filename(purpose: str, stamp: datetime | None = None) -> str:
    stamp = stamp or datetime.now()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in purpose) or "prompt"
    return f"prompt_{safe}_{stamp.strftime('%Y%m%d-%H%M%S')}.md"


def write_bundle(directory: Path, purpose: str, text: str,
                 stamp: datetime | None = None) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / bundle_filename(purpose, stamp)
    target.write_text(text, encoding="utf-8")
    return target


def copy_to_clipboard(text: str) -> bool:
    """
    Put the text on the system clipboard via tkinter; False when no display
    or clipboard is available (headless runs, some terminals). The file is
    the reliable channel, the clipboard the convenient one.
    """
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()           # hand the content to the clipboard owner
        root.destroy()
        return True
    except Exception:  # noqa: BLE001 - any failure means "not copied", nothing more
        return False
