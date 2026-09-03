# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Betreiber-Nachweis der KI-Schicht (Rechts-Leitplanke c): Jede
#   Anfrage wird als JSON-Zeile protokolliert — Provider, Modell,
#   Deployment-Klasse, Prompt-Version, Dauer und SHA-256-Hashes von
#   Eingabe und Ausgabe. NUR Hashes, keine Volltexte (Entscheidung
#   Robert 03.09.2026); Tokens/Schlüssel erscheinen nie.
# =============================================================================

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .base import LlmResult
from .prompts import PROMPT_VERSION

AUDIT_FILENAME = "llm_audit.jsonl"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def append_audit(path: Path, result: LlmResult, source_text: str,
                 purpose: str, guard_passed: bool) -> None:
    """
    Append one operator-evidence record (JSONL) for an LLM call.

    Args:
        path:        Audit file (created/appended; parents created).
        result:      The completion incl. provider/model/deployment.
        source_text: The deterministic input (hashed, never stored).
        purpose:     What the call was for (e.g. "d2_narration").
        guard_passed: Whether the numbers guard accepted the output.
    """
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "purpose": purpose,
        "provider": result.provider_id,
        "model": result.model,
        "deployment_class": result.deployment_class,
        "prompt_version": PROMPT_VERSION,
        "input_sha256": _sha256(source_text),
        "output_sha256": _sha256(result.text),
        "duration_s": round(result.duration_s, 2),
        "guard_passed": guard_passed,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
