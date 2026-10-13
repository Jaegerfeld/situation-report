# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Provider "export" — ruft KEIN Modell auf. Er legt Systemprompt und
#   Contract als Bündel in eine Datei neben der Ausgabe (und in die
#   Zwischenablage) und gibt einen Platzhalter zurück, der sagt, wo das
#   Bündel liegt und wohin die Antwort gehört. Weil er über dieselbe
#   Schnittstelle läuft wie ollama/claude/mock, steht er automatisch in
#   jeder Provider-Auswahl (GUI) und jedem --narrate (CLI): D1 Executive
#   Summary, D2 Narration, D5 Red Team, D6 Übersetzung, D8 Konferenzmappe,
#   P3 Lesart. Wächter und Audit behandeln die Klasse "export" gesondert:
#   kein Zahlen-Wächter auf dem Platzhalter, Banner „kein Modell
#   aufgerufen", Nachweis mit Provider export.
# =============================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm.base import DEPLOYMENT_EXPORT, LlmResult
from llm.export import build_bundle, copy_to_clipboard, write_bundle

_PLACEHOLDER = {
    "de": ("[KEIN MODELL AUFGERUFEN] Der Prompt (Systemprompt + Contract) wurde exportiert: "
           "{path}{clip} Führe ihn auf dem anderen Rechner oder Modell aus und füge die "
           "Antwort in die Entwurfsdatei neben dieser Ausgabe ein; sie gilt dann als "
           "ungeprüfter KI-Entwurf und ist vor Verwendung zu redigieren."),
    "en": ("[NO MODEL CALLED] The prompt (system prompt + contract) was exported: "
           "{path}{clip} Run it on the other machine or model and paste the answer into "
           "the draft file next to this output; it then counts as an unreviewed AI draft "
           "and must be edited before use."),
}
_CLIP = {"de": " (auch in der Zwischenablage).", "en": " (also on the clipboard)."}
_NOCLIP = {"de": " (Zwischenablage nicht verfügbar).", "en": " (clipboard not available)."}


class ExportProvider:
    """Writes the prompt bundle instead of generating text."""

    provider_id = "export"
    deployment_class = DEPLOYMENT_EXPORT
    default_model = "none"

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        lang = "de" if config.get("lang", "de") == "de" else "en"
        purpose = str(config.get("purpose") or "prompt")
        directory = Path(config.get("export_dir") or ".")
        draft_name = str(config.get("draft_name") or "<ausgabe>.narration.md")
        text = build_bundle(system, prompt, purpose, lang=str(config.get("lang", "de")),
                            draft_name=draft_name)
        path = write_bundle(directory, purpose, text)
        copied = copy_to_clipboard(text) if config.get("clipboard", True) else False
        clip = (_CLIP if copied else _NOCLIP)[lang]
        placeholder = _PLACEHOLDER[lang].format(path=path, clip=clip)
        return LlmResult(text=placeholder, provider_id=self.provider_id,
                         model=self.default_model, deployment_class=self.deployment_class,
                         duration_s=0.0, endpoint=str(path))


PROVIDER = ExportProvider()
