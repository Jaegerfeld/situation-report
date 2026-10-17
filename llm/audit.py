# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       11.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Betreiber-Nachweis der KI-Schicht (Rechts-Leitplanke c): Jede
#   Anfrage wird als JSON-Zeile protokolliert — Provider, Modell,
#   Deployment-Klasse, Prompt-Version, Dauer und SHA-256-Hashes von
#   Eingabe, Ausgabe und (seit D9) der Zieladresse. NUR Hashes, keine
#   Volltexte (Entscheidung Robert 03.09.2026) und keine Adresse im
#   Klartext (Entscheidung Robert 11.10.2026): Der Betreiber kann jede
#   behauptete Adresse prüfen, die Datei verrät die Infrastruktur nicht.
#   Tokens/Schlüssel erscheinen nie.
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


def append_approval(path: Path, file_name: str, reviewed_by: str,
                    original_sha256: str, approved_text: str, edited: bool | None,
                    purpose: str = "") -> None:
    """
    Append the approval of an AI draft (R3): who released which file, whether
    the text was edited before, and the hashes of draft and release. Hashes
    only - the texts stay in the file.
    """
    record: dict[str, object] = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "purpose": "approval",
        "draft_purpose": purpose,
        "file": file_name,
        "reviewed_by": reviewed_by,
        "edited": edited,
        "draft_sha256": original_sha256,
        "approved_sha256": _sha256(approved_text),
        "prompt_version": PROMPT_VERSION,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_audit(path: Path, result: LlmResult, source_text: str,
                 purpose: str, guard_passed: bool,
                 contract_warnings: int = 0) -> None:
    """
    Append one operator-evidence record (JSONL) for an LLM call.

    Args:
        path:        Audit file (created/appended; parents created).
        result:      The completion incl. provider/model/deployment.
        source_text: The deterministic input (hashed, never stored).
        purpose:     What the call was for (e.g. "d2_narration").
        guard_passed: Whether the numbers guard accepted the output.
        contract_warnings: Contract lines that read like instructions
                     (Leitplanke e) - recorded when > 0.
    """
    record: dict[str, object] = {
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
    if contract_warnings:
        record["contract_warnings"] = contract_warnings
    if result.endpoint:
        # Normalised the way resolve_base_url does, so "box:11434/" and
        # "http://box:11434" hash alike and a check by the operator succeeds.
        endpoint = result.endpoint.strip().rstrip("/")
        if "://" not in endpoint:
            endpoint = f"http://{endpoint}"
        record["endpoint_sha256"] = _sha256(endpoint)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
