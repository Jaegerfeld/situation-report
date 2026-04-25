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
           resolution: str = "",
           first_date: datetime | None = datetime(2025, 1, 2)) -> IssueRecord:
    """Create a minimal IssueRecord with optional closed date.

    Args:
        key:        Unique issue key.
        project:    Project key string (default 'A').
        issuetype:  Issue type string (default 'Feature').
        closed:     Closed datetime, or None for open issues.
        status:     Jira status string (default 'Done').
        resolution: Jira resolution string (default '').
        first_date: First Date datetime (default 2025-01-02).

    Returns:
        IssueRecord with minimal non-null fields.
    """
    return IssueRecord(
        project=project, key=key, issuetype=issuetype, status=status,
        created=datetime(2025, 1, 1), component="", first_date=first_date,
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

    def test_open_issues_pass_through_date_filter(self, sample_data):
        """Issues without a Closed Date are always included, even when a date range is active."""
        cfg = FilterConfig(from_date=date(2025, 1, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "N-1" in keys

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
        """Exclusion and date filters are applied conjunctively; open issues are retained."""
        cfg = FilterConfig(
            from_date=date(2025, 1, 1),
            excluded_statuses=["Canceled"],
        )
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "C-1" not in keys   # removed by status exclusion
        assert "N-1" in keys       # open issue: passes date filter regardless


class TestZeroDayFilter:
    """Tests for apply_filters() with exclude_zero_day / zero_day_threshold_minutes."""

    def _zd_issue(self, key: str, first: datetime, closed: datetime) -> IssueRecord:
        """Issue with explicit first_date and closed_date for zero-day testing."""
        return _issue(key, first_date=first, closed=closed)

    def test_zero_day_excluded_when_enabled(self):
        """An issue with CT < threshold minutes is excluded when exclude_zero_day is True."""
        t0 = datetime(2025, 5, 16, 15, 50, 0)
        t1 = datetime(2025, 5, 16, 15, 50, 8)  # 8 seconds — well below 5 min
        data = ReportData(
            issues=[self._zd_issue("Z-1", t0, t1)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=5)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 0

    def test_zero_day_not_excluded_when_disabled(self):
        """An issue with CT < threshold is kept when exclude_zero_day is False."""
        t0 = datetime(2025, 5, 16, 15, 50, 0)
        t1 = datetime(2025, 5, 16, 15, 50, 8)
        data = ReportData(
            issues=[self._zd_issue("Z-1", t0, t1)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=False)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 1

    def test_zero_day_threshold_respected(self):
        """An issue with CT >= threshold minutes is retained."""
        t0 = datetime(2025, 5, 16, 15, 50, 0)
        t1 = datetime(2025, 5, 16, 15, 55, 0)  # exactly 5 minutes — not below threshold
        data = ReportData(
            issues=[self._zd_issue("Z-1", t0, t1)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=5)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 1

    def test_zero_day_without_first_date_not_excluded(self):
        """An issue without a first_date is never removed by the zero-day filter."""
        data = ReportData(
            issues=[_issue("Z-1", first_date=None, closed=datetime(2025, 5, 16, 15, 50, 8))],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=5)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 1

    def test_zero_day_without_closed_date_not_excluded(self):
        """An issue without a closed_date is never removed by the zero-day filter."""
        data = ReportData(
            issues=[_issue("Z-1", first_date=datetime(2025, 5, 16, 15, 50, 0), closed=None)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=5)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 1

    def test_zero_day_custom_threshold(self):
        """The threshold is configurable — a 10-minute issue passes a 5 min threshold."""
        t0 = datetime(2025, 5, 16, 15, 50, 0)
        t1 = datetime(2025, 5, 16, 16, 0, 0)  # 10 minutes
        data = ReportData(
            issues=[self._zd_issue("Z-1", t0, t1)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=5)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 1  # 10 min >= 5 min threshold

    def test_zero_day_custom_threshold_excludes(self):
        """A 10-minute issue is excluded when the threshold is set to 15 minutes."""
        t0 = datetime(2025, 5, 16, 15, 50, 0)
        t1 = datetime(2025, 5, 16, 16, 0, 0)  # 10 minutes
        data = ReportData(
            issues=[self._zd_issue("Z-1", t0, t1)],
            cfd=[], stages=[], source_prefix="T",
        )
        cfg = FilterConfig(exclude_zero_day=True, zero_day_threshold_minutes=15)
        result = apply_filters(data, cfg)
        assert len(result.issues) == 0  # 10 min < 15 min threshold


class TestWorkflowMarkerPassthrough:
    """apply_filters() must forward first_stage and closed_stage to the filtered ReportData."""

    def test_first_stage_preserved(self):
        """first_stage survives apply_filters unchanged."""
        data = ReportData(issues=[], cfd=[], stages=["A", "B"], source_prefix="T",
                         first_stage="B", closed_stage="A")
        result = apply_filters(data, FilterConfig())
        assert result.first_stage == "B"

    def test_closed_stage_preserved(self):
        """closed_stage survives apply_filters unchanged."""
        data = ReportData(issues=[], cfd=[], stages=["A", "B"], source_prefix="T",
                         first_stage="B", closed_stage="A")
        result = apply_filters(data, FilterConfig())
        assert result.closed_stage == "A"

    def test_none_markers_preserved(self):
        """None markers (no workflow file) remain None after filtering."""
        data = ReportData(issues=[], cfd=[], stages=["A", "B"], source_prefix="T")
        result = apply_filters(data, FilterConfig())
        assert result.first_stage is None
        assert result.closed_stage is None
