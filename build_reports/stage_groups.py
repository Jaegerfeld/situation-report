# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       18.04.2026
# Geändert:       18.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Klassifiziert Workflow-Stages in die drei fachlichen Gruppen
#   "To Do", "In Progress" und "Done" anhand ihrer Position im Workflow
#   relativ zur First-Stage und Closed-Stage. Bestimmt außerdem die
#   Statusgruppe eines einzelnen Issues anhand seiner Übergangsdaten.
# =============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .loader import IssueRecord

GROUP_TODO = "To Do"
GROUP_IN_PROGRESS = "In Progress"
GROUP_DONE = "Done"


def classify_stages(
    stages: list[str],
    first_stage: str | None,
    closed_stage: str | None,
) -> dict[str, str]:
    """
    Map each workflow stage to its status group.

    Stages before first_stage are classified as To Do; from first_stage
    (inclusive) up to closed_stage (exclusive) as In Progress; closed_stage
    and all subsequent stages as Done.

    If first_stage is None or not present in stages, all stages are mapped
    to In Progress (no boundary information available).

    Args:
        stages:       Ordered list of workflow stage names from ReportData.
        first_stage:  Stage name marking the start of active work (First Date
                      boundary). May be None if unknown.
        closed_stage: Stage name marking completion (Closed Date boundary).
                      May be None; if absent all stages from first_stage on
                      are In Progress.

    Returns:
        Dict mapping each stage name to GROUP_TODO, GROUP_IN_PROGRESS, or
        GROUP_DONE. Empty dict when stages is empty.
    """
    if not stages:
        return {}

    if not first_stage or first_stage not in stages:
        return {s: GROUP_IN_PROGRESS for s in stages}

    first_idx = stages.index(first_stage)
    if closed_stage and closed_stage in stages:
        closed_idx = stages.index(closed_stage)
    else:
        closed_idx = len(stages)

    result: dict[str, str] = {}
    for i, stage in enumerate(stages):
        if i < first_idx:
            result[stage] = GROUP_TODO
        elif i < closed_idx:
            result[stage] = GROUP_IN_PROGRESS
        else:
            result[stage] = GROUP_DONE
    return result


def issue_stage_group(issue: "IssueRecord") -> str:
    """
    Determine the status group of an issue from its workflow transition dates.

    Uses closed_date and first_date as proxies for stage membership:
    issues with a Closed Date are Done; issues that have started (First Date
    set) but are not yet closed are In Progress; all others are To Do.

    Args:
        issue: IssueRecord with optional first_date and closed_date fields.

    Returns:
        GROUP_DONE if closed_date is set, GROUP_IN_PROGRESS if only first_date
        is set, or GROUP_TODO if neither date is present.
    """
    if issue.closed_date is not None:
        return GROUP_DONE
    if issue.first_date is not None:
        return GROUP_IN_PROGRESS
    return GROUP_TODO
