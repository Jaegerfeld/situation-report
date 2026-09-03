# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Optionaler LIVE-Test gegen ein lokal laufendes Ollama (Phase 0 auf
#   Roberts Rechner: Ollama installieren, `ollama pull mistral-nemo`).
#   Standardmäßig deselektiert (pyproject addopts); Aufruf:
#       python -m pytest tests/llm/live -m ollama_live
#   Prüft den echten Pfad: Vervollständigung, Kennzeichnung, Audit.
# =============================================================================

from __future__ import annotations

import json

import pytest

from llm.narrate import narrate

pytestmark = pytest.mark.ollama_live

_BRIEFING = (
    "# Delta Briefing - Demo (2026-08-16 -> 2026-08-30, 14 Tage)\n"
    "- Solution Alpha - Completed: 60 -> 75\n"
    "- [Alpha] AD-1: Plattform-Team liefert API - at_risk -> blocked\n"
    "- [Beta] R-2: Lasttest-Umgebung fehlt - ROAM: owned -> resolved\n")


def test_live_narration_labeled_and_audited(tmp_path) -> None:
    audit = tmp_path / "llm_audit.jsonl"
    try:
        narration = narrate(_BRIEFING, provider_id="ollama",
                            audit_path=audit)
    except RuntimeError as exc:
        pytest.skip(f"Ollama not usable here: {exc}")
    assert len(narration.text) > 50
    assert "mistral-nemo" in narration.banner
    assert "local" in narration.banner
    record = json.loads(audit.read_text(encoding="utf-8"))
    assert record["deployment_class"] == "local"
    assert record["guard_passed"] is True
