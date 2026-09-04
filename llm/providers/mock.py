# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Mock-Provider — die deterministische Attrappe: erzeugt ohne jedes
#   Modell einen klar als Attrappe gekennzeichneten Beispieltext. Zweck:
#   Tests ohne Netz/LLM und der Demo-Weg (das Szenario zeigt den
#   kompletten Narrations-Fluss, ohne dass jemand Ollama installiert).
#   Bewusst ohne Zahlen, damit der Zahlen-Wächter strukturell nie
#   anschlagen kann.
# =============================================================================

from __future__ import annotations

from typing import Any

from llm.base import DEPLOYMENT_MOCK, LlmResult

_TEXT_DE = (
    "[ATTRAPPE — kein Sprachmodell beteiligt] Auf Basis des Briefings: "
    "Die auffälligste Verschlechterung betrifft die im Briefing rot "
    "markierten Übergänge; dort ist vor der Konferenz eine Klärung der "
    "Zuständigkeit sinnvoll. Die übrigen Veränderungen entsprechen dem "
    "erwarteten Fortschritt. Details und alle Kennzahlen stehen im "
    "deterministischen Delta-Briefing darüber. Dieser Platzhaltertext "
    "demonstriert nur den Ablauf inklusive Kennzeichnung und Audit.")

_TEXT_EN = (
    "[MOCK — no language model involved] Based on the briefing: the most "
    "notable worsening concerns the transitions marked red in the "
    "briefing; clarifying ownership before the conference seems useful. "
    "The remaining changes match expected progress. Details and all "
    "figures are in the deterministic delta briefing above. This "
    "placeholder text only demonstrates the flow incl. labeling and "
    "audit.")


_QUESTIONS_DE = (
    "[ATTRAPPE — kein Sprachmodell beteiligt]\n\n"
    "## Beispiel-Eintrag\n"
    "- Welche stille Voraussetzung dieses Eintrags wurde nie geprüft?\n"
    "- Woran würde das betroffene Team ein Kippen zuerst erkennen?\n")

_QUESTIONS_EN = (
    "[MOCK — no language model involved]\n\n"
    "## Sample entry\n"
    "- Which silent precondition of this entry was never verified?\n"
    "- How would the owning team notice a flip first?\n")


class MockProvider:
    """Deterministic stand-in for tests and the installation-free demo."""

    provider_id = "mock"
    deployment_class = DEPLOYMENT_MOCK
    default_model = "mock-1"

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        """Return a fixed placeholder (language via config; the red-team
        prompt gets question-shaped output so the questions guard can
        pass structurally — still deliberately number-free)."""
        english = config.get("lang") == "en"
        if "remortem" in system:  # Premortem/premortem (D5)
            text = _QUESTIONS_EN if english else _QUESTIONS_DE
        else:
            text = _TEXT_EN if english else _TEXT_DE
        return LlmResult(text=text, provider_id=self.provider_id,
                         model=self.default_model,
                         deployment_class=self.deployment_class,
                         duration_s=0.0)


PROVIDER = MockProvider()
