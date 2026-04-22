# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       22.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für filters.py. Prüft Datum-, Projekt-, Issuetype- und
#   Ausschluss-Filter (Status/Resolution) isoliert sowie in Kombination.
#   Stellt sicher, dass ReportData nicht mutiert wird und dass CFD-Einträge
#   korrekt nach Datum gefiltert werden.
# =============================================================================

from datetime import date, datetime

import pytest

from build_reports.filters import FilterConfig, apply_filters
from build_reports.loader import CfdRecord, IssueRecord, ReportData


def _issue(key: str, project: str = "A", issuetype: str = "Feature",
           closed: datetime | None = None, status: str = "Done",
           resolution: str = "") -> IssueRecord:
    """Create a minimal IssueRecord with optional closed date.

    Args:
        key:        Unique issue key.
        project:    Project key string (default 'A').
        issuetype:  Issue type string (default 'Feature').
        closed:     Closed datetime, or None for open issues.
        status:     Jira status string (default 'Done').
        resolution: Jira resolution string (default '').

    Returns:
        IssueRecord with minimal non-null fields.
    """
    return IssueRecord(
        project=project, key=key, issuetype=issuetype, status=status,
        created=datetime(2025, 1, 1), component="", first_date=datetime(2025, 1, 2),
        implementation_date=None, closed_date=closed, stage_minutes={}, resolution=resolution,
    )


def _cfd(day: date) -> CfdRecord:
    """Create a minimal CfdRecord for a given calendar day.

    Args:
        day: The date of this CFD snapshot.

    Returns:
        CfdRecord with a single 'Funnel' stage count of 1.
    """
    return CfdRecord(day=day, stage_counts={"Funnel": 1})


@pytest.fixture
def sample_data() -> ReportData:
    """ReportData with 7 issues across two projects and 3 CFD records.

    Issues: A-1 (closed Mar), A-2 (closed Jun), B-1 (closed Sep),
            X-1 (Bug, closed Apr), N-1 (open, no closed date),
            C-1 (Canceled status), W-1 (Won't Do resolution).
    CFD records: Jan, Jun, Dec 2025.
    """
    return ReportData(
        issues=[
            _issue("A-1", project="ART_A", closed=datetime(2025, 3, 1)),
            _issue("A-2", project="ART_A", closed=datetime(2025, 6, 15)),
            _issue("B-1", project="ART_B", closed=datetime(2025, 9, 1)),
            _issue("X-1", project="ART_A", issuetype="Bug", closed=datetime(2025, 4, 1)),
            _issue("N-1", project="ART_A", closed=None),
            _issue("C-1", project="ART_A", closed=datetime(2025, 5, 1),
                   status="Canceled"),
            _issue("W-1", project="ART_A", closed=datetime(2025, 5, 1),
                   resolution="Won't Do"),
        ],
        cfd=[
            _cfd(date(2025, 1, 1)),
            _cfd(date(2025, 6, 1)),
            _cfd(date(2025, 12, 1)),
        ],
        stages=["Funnel"],
        source_prefix="TEST",
    )


class TestNoFilter:
    """Tests for apply_filters() with an empty FilterConfig — no records removed."""

    def test_empty_config_returns_all_issues(self, sample_data):
        """All issues are preserved when no filter criteria are set."""
        result = apply_filters(sample_data, FilterConfig())
        assert len(result.issues) == len(sample_data.issues)

    def test_empty_config_returns_all_cfd(self, sample_data):
        """All CFD records are preserved when no filter criteria are set."""
        result = apply_filters(sample_data, FilterConfig())
        assert len(result.cfd) == len(sample_data.cfd)

    def test_stages_preserved(self, sample_data):
        """Stages list is passed through unchanged by apply_filters."""
        result = apply_filters(sample_data, FilterConfig())
        assert result.stages == sample_data.stages

    def test_source_prefix_preserved(self, sample_data):
        """source_prefix is passed through unchanged by apply_filters."""
        result = apply_filters(sample_data, FilterConfig())
        assert result.source_prefix == "TEST"

    def test_original_data_not_mutated(self, sample_data):
        """apply_filters does not mutate the source ReportData object."""
        original_count = len(sample_data.issues)
        apply_filters(sample_data, FilterConfig(projects=["ART_A"]))
        assert len(sample_data.issues) == original_count


class TestDateFilter:
    """Tests for apply_filters() with date range criteria."""

    def test_from_date_excludes_earlier(self, sample_data):
        """Issues closed before from_date are excluded."""
        cfg = FilterConfig(from_date=date(2025, 5, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-1" not in keys   # closed 2025-03-01

    def test_to_date_excludes_later(self, sample_data):
        """Issues closed after to_date are excluded."""
        cfg = FilterConfig(to_date=date(2025, 5, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-2" not in keys   # closed 2025-06-15
        assert "B-1" not in keys   # closed 2025-09-01

    def test_date_range_inclusive_bounds(self, sample_data):
        """Issues closed exactly on from_date or to_date are included."""
        cfg = FilterConfig(from_date=date(2025, 3, 1), to_date=date(2025, 6, 15))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-1" in keys
        assert "A-2" in keys

    def test_no_closed_date_excluded_when_range_set(self, sample_data):
        """Issues without a Closed Date are excluded when a date range is active."""
        cfg = FilterConfig(from_date=date(2025, 1, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "N-1" not in keys

    def test_cfd_filtered_by_date(self, sample_data):
        """CFD records outside the date range are removed."""
        cfg = FilterConfig(from_date=date(2025, 3, 1), to_date=date(2025, 7, 1))
        result = apply_filters(sample_data, cfg)
        assert len(result.cfd) == 1
        assert result.cfd[0].day == date(2025, 6, 1)


class TestProjectFilter:
    """Tests for apply_filters() with project key criteria."""

    def test_single_project(self, sample_data):
        """Only issues belonging to the specified project are retained."""
        cfg = FilterConfig(projects=["ART_B"])
        result = apply_filters(sample_data, cfg)
        assert all(i.project == "ART_B" for i in result.issues)
        assert len(result.issues) == 1

    def test_multiple_projects(self, sample_data):
        """Issues from all listed projects are retained."""
        cfg = FilterConfig(projects=["ART_A", "ART_B"])
        result = apply_filters(sample_data, cfg)
        projects = {i.project for i in result.issues}
        assert projects == {"ART_A", "ART_B"}


class TestIssuetypeFilter:
    """Tests for apply_filters() with issuetype criteria."""

    def test_single_type(self, sample_data):
        """Only issues of the specified type are retained."""
        cfg = FilterConfig(issuetypes=["Bug"])
        result = apply_filters(sample_data, cfg)
        assert len(result.issues) == 1
        assert result.issues[0].key == "X-1"

    def test_combined_project_and_type(self, sample_data):
        """Project and issuetype filters are applied conjunctively."""
        cfg = FilterConfig(projects=["ART_A"], issuetypes=["Feature"])
        result = apply_filters(sample_data, cfg)
        assert all(i.project == "ART_A" and i.issuetype == "Feature"
                   for i in result.issues)


class TestExclusionFilter:
    """Tests for apply_filters() with excluded_statuses / excluded_resolutions."""

    def test_excluded_status_removes_issue(self, sample_data):
        """Issues whose status is in excluded_statuses are completely removed."""
        cfg = FilterConfig(excluded_statuses=["Canceled"])
        result = apply_filters(sample_data, cfg)
        assert all(i.key != "C-1" for i in result.issues)

    def test_excluded_resolution_removes_issue(self, sample_data):
        """Issues whose resolution is in excluded_resolutions are completely removed."""
        cfg = FilterConfig(excluded_resolutions=["Won't Do"])
        result = apply_filters(sample_data, cfg)
        assert all(i.key != "W-1" for i in result.issues)

    def test_non_excluded_status_retained(self, sample_data):
        """Issues whose status is not in the exclusion list are retained."""
        cfg = FilterConfig(excluded_statuses=["Canceled"])
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-1" in keys
        assert "A-2" in keys

    def test_empty_excluded_lists_no_effect(self, sample_data):
        """Empty exclusion lists do not remove any issues."""
        cfg = FilterConfig(excluded_statuses=[], excluded_resolutions=[])
        result = apply_filters(sample_data, cfg)
        assert len(result.issues) == len(sample_data.issues)

    def test_combined_status_and_resolution_exclusion(self, sample_data):
        """Both excluded_statuses and excluded_resolutions are applied together."""
        cfg = FilterConfig(excluded_statuses=["Canceled"], excluded_resolutions=["Won't Do"])
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "C-1" not in keys
        assert "W-1" not in keys

    def test_exclusion_combined_with_date_filter(self, sample_data):
        """Exclusion and date filters are applied conjunctively."""
        cfg = FilterConfig(
            from_date=date(2025, 1, 1),
            excluded_statuses=["Canceled"],
        )
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "C-1" not in keys
        assert "N-1" not in keys  # excluded by date filter (no closed date)
