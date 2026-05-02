# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Kernlogik des JSON-Merger-Tools im helper-Modul. Fügt mehrere Jira-REST-API-
#   JSON-Dateien zu einer einzigen Ausgabedatei zusammen. Dedupliziert nach
#   Issue-ID und erzeugt einen korrekten Jira-API-Envelope (startAt, total,
#   maxResults). Die Ausgabe ist direkt mit transform_data verarbeitbar.
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path


def merge_json_files(
    inputs: list[Path],
    output: Path,
    deduplicate: bool = True,
    log: Callable[[str], None] = print,
) -> None:
    """
    Merge multiple Jira REST API JSON files into a single output file.

    Each input file must contain a top-level "issues" key (Jira REST API format).
    The output envelope uses startAt=0 and sets total/maxResults to the final
    issue count. The "expand" value is taken from the first file.

    Args:
        inputs:      List of input JSON file paths (at least one required).
        output:      Destination path for the merged JSON file.
        deduplicate: Remove duplicate issues by their "id" field (default: True).
                     Logs a warning for each duplicate found.
        log:         Callable for progress and warning messages.

    Raises:
        ValueError: If an input file is missing the required "issues" key.
    """
    if not inputs:
        raise ValueError("At least one input file is required.")

    all_issues: list[dict] = []
    expand_value = "schema,names"
    seen_ids: dict[str, str] = {}  # id → source filename, for dedup warnings

    for path in inputs:
        log(f"Reading: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if "issues" not in data:
            raise ValueError(f"File is missing required 'issues' key: {path}")

        if expand_value == "schema,names" and data.get("expand"):
            expand_value = data["expand"]

        file_issues: list[dict] = data["issues"]
        log(f"  {len(file_issues)} issues found.")

        for issue in file_issues:
            issue_id = issue.get("id", "")
            if deduplicate and issue_id in seen_ids:
                log(
                    f"  WARNING: Duplicate issue id '{issue_id}' "
                    f"(already seen in {seen_ids[issue_id]}) — skipped."
                )
                continue
            if deduplicate:
                seen_ids[issue_id] = path.name
            all_issues.append(issue)

    n = len(all_issues)
    merged: dict = {
        "expand": expand_value,
        "startAt": 0,
        "maxResults": n,
        "total": n,
        "issues": all_issues,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Merged {len(inputs)} file(s) → {n} issues → {output}")
