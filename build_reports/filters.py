# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Definiert die Filterkriterien für Reports (Zeitraum, Projekte, Issuetype)
#   und wendet sie auf ReportData an. Issues werden nach Closed Date gefiltert,
#   CFD-Einträge nach dem Tagesdatum. Leere Filterlisten bedeuten "kein Filter".
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .loader import CfdRecord, IssueRecord, ReportData


@dataclass
class FilterConfig:
    """
    Criteria used to restrict ReportData before metric computation.

    All fields are optional — None or empty list means no restriction.

    Attributes:
        from_date:   Include only issues closed on or after this date.
        to_date:     Include only issues closed on or before this date.
        projects:    Restrict to these project keys (empty = all projects).
        issuetypes:  Restrict to these issue types (empty = all types).
    """
    from_date: date | None = None
    to_date: date | None = None
    projects: list[str] = field(default_factory=list)
    issuetypes: list[str] = field(default_factory=list)


def _issue_passes(issue: IssueRecord, cfg: FilterConfig) -> bool:
    """
    Check whether a single issue matches the filter criteria.

    Date filtering is based on closed_date. Issues with no closed_date
    are excluded when a date range is specified.

    Args:
        issue: The issue record to evaluate.
        cfg:   Active filter configuration.

    Returns:
        True if the issue satisfies all filter criteria.
    """
    if cfg.projects and issue.project not in cfg.projects:
        return False
    if cfg.issuetypes and issue.issuetype not in cfg.issuetypes:
        return False
    if cfg.from_date is not None or cfg.to_date is not None:
        if issue.closed_date is None:
            return False
        closed = issue.closed_date.date()
        if cfg.from_date is not None and closed < cfg.from_date:
            return False
        if cfg.to_date is not None and closed > cfg.to_date:
            return False
    return True


def _cfd_passes(record: CfdRecord, cfg: FilterConfig) -> bool:
    """
    Check whether a CFD day record falls within the configured date range.

    Args:
        record: The CFD record (one calendar day) to evaluate.
        cfg:    Active filter configuration.

    Returns:
        True if the day is within the configured date range.
    """
    if cfg.from_date is not None and record.day < cfg.from_date:
        return False
    if cfg.to_date is not None and record.day > cfg.to_date:
        return False
    return True


def apply_filters(data: ReportData, cfg: FilterConfig) -> ReportData:
    """
    Return a new ReportData containing only records that match the filter config.

    Issues are filtered by project, issuetype, and closed_date range.
    CFD records are filtered by date range only (no project/type dimension in CFD).
    The stages list and source_prefix are preserved unchanged.

    Args:
        data: Source ReportData (not mutated).
        cfg:  Filter criteria to apply.

    Returns:
        New ReportData with filtered issues and CFD records.
    """
    filtered_issues = [i for i in data.issues if _issue_passes(i, cfg)]
    filtered_cfd = [r for r in data.cfd if _cfd_passes(r, cfg)]

    return ReportData(
        issues=filtered_issues,
        cfd=filtered_cfd,
        stages=data.stages,
        source_prefix=data.source_prefix,
    )
