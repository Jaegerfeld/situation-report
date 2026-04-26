# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       26.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Definiert die Filterkriterien für Reports (Zeitraum, Projekte, Issuetype,
#   Ausschlüsse nach Status/Resolution, Zero-Day-Ausschluss) und wendet sie auf
#   ReportData an. Issues werden nach Closed Date gefiltert, CFD-Einträge nach
#   dem Tagesdatum. Leere Filterlisten bedeuten "kein Filter".
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .loader import CfdRecord, IssueRecord, ReportData


@dataclass
class FilterConfig:
    """
    Criteria used to restrict ReportData before metric computation.

    All fields are optional — None or empty list means no restriction.

    Attributes:
        from_date:                Include only issues closed on or after this date.
        to_date:                  Include only issues closed on or before this date.
        projects:                 Restrict to these project keys (empty = all projects).
        issuetypes:               Restrict to these issue types (empty = all types).
        excluded_statuses:        Remove issues whose current status is in this list.
        excluded_resolutions:     Remove issues whose resolution is in this list.
        exclude_zero_day:         Remove issues whose cycle time (First → Closed Date)
                                  is below zero_day_threshold_minutes.
        zero_day_threshold_minutes: Threshold in minutes for zero-day detection (default 5).
    """
    from_date: date | None = None
    to_date: date | None = None
    projects: list[str] = field(default_factory=list)
    issuetypes: list[str] = field(default_factory=list)
    excluded_statuses: list[str] = field(default_factory=list)
    excluded_resolutions: list[str] = field(default_factory=list)
    exclude_zero_day: bool = False
    zero_day_threshold_minutes: int = 5


def _issue_passes(issue: IssueRecord, cfg: FilterConfig) -> bool:
    """
    Check whether a single issue matches the filter criteria.

    Date filtering is based on closed_date and only applies to issues that
    have a closed_date. Open issues (no closed_date) are always passed through
    the date filter so that Flow Load and Flow Distribution can work correctly
    even when a date range is active. Issues whose status or resolution appears
    in the exclusion lists are always removed.

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
    if issue.closed_date is not None:
        closed = issue.closed_date.date()
        if cfg.from_date is not None and closed < cfg.from_date:
            return False
        if cfg.to_date is not None and closed > cfg.to_date:
            return False
    if cfg.excluded_statuses and issue.status in cfg.excluded_statuses:
        return False
    if cfg.excluded_resolutions and issue.resolution in cfg.excluded_resolutions:
        return False
    if (cfg.exclude_zero_day
            and issue.first_date is not None
            and issue.closed_date is not None):
        delta_minutes = (issue.closed_date - issue.first_date).total_seconds() / 60
        if delta_minutes < cfg.zero_day_threshold_minutes:
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
        transitions=data.transitions,
        stages=data.stages,
        source_prefix=data.source_prefix,
        first_stage=data.first_stage,
        closed_stage=data.closed_stage,
    )
