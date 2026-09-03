# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prüfung eines Jira-Exports (Roadmap C3, Export-Weg): Der manuelle
#   Export bleibt ein gleichwertiger Erhebungsweg neben dem REST-Abruf —
#   diese Prüfung sagt VOR transform_data, ob eine Export-Datei vollständig
#   und brauchbar ist: Pflichtfelder vorhanden, Changelog dabei (sonst
#   fehlen die Statusübergänge), keine vergessenen Folgeseiten (der
#   Klassiker: nur Seite 1 exportiert — total > geladene Issues).
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: Fields transform_data requires per issue (manual section 1.4).
REQUIRED_PATHS = (
    ("key",),
    ("fields", "issuetype", "name"),
    ("fields", "created"),
    ("fields", "status", "name"),
)


@dataclass
class ExportCheck:
    """Result of validating one export file."""
    issue_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the export is usable (warnings allowed)."""
        return not self.errors


def _get_path(issue: dict, path: tuple[str, ...]) -> Any:
    node: Any = issue
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def validate_export(data: Any) -> ExportCheck:
    """
    Validate an already-parsed Jira export.

    Accepts both the standard envelope ({..., "issues": [...]}) and a bare
    issue list (as some scripts produce). Errors make the export unusable;
    warnings flag quality gaps the report will surface later anyway.

    Args:
        data: Parsed JSON of the export.

    Returns:
        A populated ExportCheck.
    """
    check = ExportCheck()

    if isinstance(data, list):
        issues, claimed_total = data, None
    elif isinstance(data, dict) and isinstance(data.get("issues"), list):
        issues = data["issues"]
        claimed_total = data.get("total")
    else:
        check.errors.append(
            "Not a Jira export: expected an object with an 'issues' list "
            "(or a bare issue list).")
        return check

    check.issue_count = len(issues)
    if not issues:
        check.errors.append("Export contains no issues.")
        return check

    missing, no_changelog, duplicates = _scan_issues(issues, check)
    if check.errors:
        return check

    for path_name, count in sorted(missing.items()):
        check.errors.append(
            f"{count}/{len(issues)} issues are missing required field "
            f"'{path_name}'.")

    if no_changelog == len(issues):
        check.errors.append(
            "No issue carries a changelog — the export was made without "
            "expand=changelog; status transitions are missing entirely.")
    elif no_changelog:
        check.warnings.append(
            f"{no_changelog}/{len(issues)} issues have no changelog entries "
            f"(no status transitions for them).")

    if duplicates:
        check.warnings.append(
            f"{duplicates} duplicate issue keys — pages merged twice? "
            f"The helper removes duplicates (python -m helper ...).")

    if isinstance(claimed_total, int) and claimed_total > len(issues):
        check.errors.append(
            f"Export claims total={claimed_total} but contains only "
            f"{len(issues)} issues — follow-up pages are missing. Fetch the "
            f"remaining pages and merge them (python -m helper ...).")

    return check


def _scan_issues(
    issues: list, check: ExportCheck
) -> tuple[dict[str, int], int, int]:
    """Per-issue scan: missing required fields, changelog gaps, duplicates."""
    missing: dict[str, int] = {}
    no_changelog = 0
    seen: set[str] = set()
    duplicates = 0
    for issue in issues:
        if not isinstance(issue, dict):
            check.errors.append("Export contains a non-object issue entry.")
            return missing, no_changelog, duplicates
        for path in REQUIRED_PATHS:
            if _get_path(issue, path) in (None, ""):
                missing[".".join(path)] = missing.get(".".join(path), 0) + 1
        if not _get_path(issue, ("changelog", "histories")):
            no_changelog += 1
        key = str(issue.get("key", ""))
        if key:
            if key in seen:
                duplicates += 1
            seen.add(key)
    return missing, no_changelog, duplicates


def validate_export_file(path: Path) -> ExportCheck:
    """
    Read and validate one export file.

    Read/parse problems become errors on the returned check rather than
    exceptions, so callers (CLI/GUI) can present them uniformly.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        return ExportCheck(errors=[f"Cannot read file: {exc}"])
    except json.JSONDecodeError as exc:
        return ExportCheck(errors=[f"Not valid JSON: {exc}"])
    return validate_export(raw)
