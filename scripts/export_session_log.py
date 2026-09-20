# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Einmal-Skript zum Export aller wesentlichen Interaktionen aus den
#   Claude-Code-Konversationen des SituationReport-Projekts.
#   Erzeugt eine lesbare Textdatei mit User-Prompts und Claude-Antworten
#   (ohne einfache Bestätigungen und ohne Code-Blöcke).
# =============================================================================

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JSONL_DIR = Path(r"C:\Users\rober\.claude\projects"
                 r"\C--Users-rober-OneDrive-Documents-ClaudeProjects-SituationReport")
OUTPUT_FILE = Path(__file__).parent.parent / "session_log_2026-05-03.txt"

# Only include sessions that started on or after this date (UTC)
CUTOFF_DATE = datetime(2026, 4, 12, tzinfo=UTC)

# Local timezone offset for display (CEST = UTC+2)
LOCAL_TZ = timezone(timedelta(hours=2))

# User messages shorter than this (stripped) are treated as simple confirmations
MIN_USER_MSG_LEN = 20

# Simple confirmation messages to skip regardless of length
SKIP_MESSAGES: set[str] = {
    "ja", "ok", "nein", "gut", "danke", "weiter", "setze fort", "fortfahren",
    "ja genau", "perfekt", "passt", "stimmt", "yes", "no", "go", "continue",
    "/compact", "super", "prima", "alles klar", "klar", "richtig", "genau",
    "mach weiter", "weiter machen", "fortsetzen",
}

# Assistant text blocks shorter than this (after code removal) are skipped
MIN_ASSISTANT_TEXT_LEN = 50

# Regex to strip fenced code blocks (``` ... ```), including indented variants
_CODE_BLOCK_RE = re.compile(r"[ \t]*```[^\n]*\n.*?[ \t]*```", re.DOTALL)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_ts(ts_str: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp string into a timezone-aware datetime."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def _to_local(dt: datetime) -> str:
    """Format a UTC datetime as a local-time string (DD.MM.YYYY HH:MM)."""
    local = dt.astimezone(LOCAL_TZ)
    return local.strftime("%d.%m.%Y %H:%M")


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks from assistant text, preserving surrounding prose."""
    stripped = _CODE_BLOCK_RE.sub("[Code-Block entfernt]", text)
    # Collapse runs of blank lines left by removed blocks
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.strip()


def _is_simple_confirmation(text: str) -> bool:
    """Return True if the user message is a short, content-free confirmation."""
    t = text.strip().lower()
    if t in SKIP_MESSAGES:
        return True
    if len(t) < MIN_USER_MSG_LEN and not any(c.isalpha() and c not in "jankgodpqvwxyz" for c in t):
        return True
    return len(text.strip()) < MIN_USER_MSG_LEN


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _extract_messages(jsonl_path: Path) -> list[dict]:
    """
    Extract user and assistant messages from a single JSONL conversation file.

    Args:
        jsonl_path: Path to the JSONL file.

    Returns:
        List of dicts with keys: role ('user'|'assistant'), text, timestamp.
    """
    messages: list[dict] = []

    with open(jsonl_path, encoding="utf-8") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            msg = entry.get("message", {})
            role = msg.get("role") if isinstance(msg, dict) else None
            ts_str = entry.get("timestamp", "")

            # ---- User message ----
            if entry_type == "user" and role == "user":
                content = msg.get("content", "")
                # List content = tool results bundled back to Claude → skip
                if not isinstance(content, str):
                    continue
                content = content.strip()
                # Skip empty, confirmations, system-generated XML messages,
                # and line-numbered file-read outputs
                if not content:
                    continue
                if content.startswith("<"):
                    continue
                if re.match(r"^\d+\t", content):
                    continue
                if _is_simple_confirmation(content):
                    continue
                messages.append({
                    "role": "user",
                    "text": content,
                    "timestamp": _parse_ts(ts_str) if ts_str else None,
                })

            # ---- Assistant message ----
            elif entry_type == "assistant" and role == "assistant":
                content_blocks = msg.get("content", [])
                if not isinstance(content_blocks, list):
                    continue
                text_parts = [
                    block["text"]
                    for block in content_blocks
                    if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
                ]
                if not text_parts:
                    continue
                raw_text = "\n".join(text_parts)
                clean_text = _strip_code_blocks(raw_text)
                if len(clean_text) < MIN_ASSISTANT_TEXT_LEN:
                    continue
                messages.append({
                    "role": "assistant",
                    "text": clean_text,
                    "timestamp": _parse_ts(ts_str) if ts_str else None,
                })

    return messages


def _session_start_ts(jsonl_path: Path) -> datetime | None:
    """Read the timestamp of the first entry in a JSONL file."""
    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                ts = entry.get("timestamp")
                if ts:
                    return _parse_ts(ts)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Collect all qualifying sessions, extract messages, write the log file."""

    # 1. Gather JSONL files directly in the project directory (no subdirs)
    jsonl_files = sorted(JSONL_DIR.glob("*.jsonl"))

    # 2. Filter by cutoff date and sort chronologically
    sessions: list[tuple[datetime, Path]] = []
    for p in jsonl_files:
        ts = _session_start_ts(p)
        if ts and ts >= CUTOFF_DATE:
            sessions.append((ts, p))
    sessions.sort(key=lambda x: x[0])

    if not sessions:
        print("Keine Konversationen im angegebenen Zeitraum gefunden.")
        return

    # 3. Build output
    lines: list[str] = []
    sep_major = "=" * 77
    sep_minor = "─" * 77

    today = datetime.now(tz=LOCAL_TZ).strftime("%d.%m.%Y")
    lines.append(sep_major)
    lines.append("SITUATION REPORT – SESSION LOG")
    lines.append(f"Zeitraum: 12. April 2026 – 03. Mai 2026  |  Erstellt: {today}")
    lines.append(sep_major)

    total_msgs = 0
    for session_ts, jsonl_path in sessions:
        messages = _extract_messages(jsonl_path)
        if not messages:
            continue

        session_label = session_ts.astimezone(LOCAL_TZ).strftime("%d.%m.%Y")
        lines.append("")
        lines.append(sep_minor)
        lines.append(f"Session: {session_label}  [{jsonl_path.stem[:8]}…]")
        lines.append(sep_minor)

        for msg in messages:
            ts_str = _to_local(msg["timestamp"]) if msg["timestamp"] else "??"
            role_label = "USER" if msg["role"] == "user" else "CLAUDE"
            lines.append("")
            lines.append(f"[{ts_str}] {role_label}:")
            lines.append(msg["text"])
            total_msgs += 1

    lines.append("")
    lines.append(sep_major)
    lines.append("HINWEIS: Die aktuelle laufende Session (03.05.2026) ist noch nicht")
    lines.append("in einer JSONL-Datei gespeichert und daher hier nicht enthalten.")
    lines.append(sep_major)

    # 4. Write UTF-8 with BOM (Windows-friendly)
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"Exportiert: {OUTPUT_FILE}")
    print(f"Sessions: {len(sessions)}  |  Nachrichten: {total_msgs}")


if __name__ == "__main__":
    main()
