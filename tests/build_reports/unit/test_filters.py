# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für filters.py. Prüft Datum-, Projekt- und Issuetype-Filter
#   isoliert sowie in Kombination. Stellt sicher, dass ReportData nicht
#   mutiert wird und dass CFD-Einträge korrekt nach Datum gefiltert werden.
# =============================================================================

from datetime import date, datetime

import pytest

from build_reports.filters import FilterConfig, apply_filters
from build_reports.loader import CfdRecord, IssueRecord, ReportData


def _issue(key: str, project: str = "A", issuetype: str = "Feature",
           closed: datetime | None = None) -> IssueRecord:
    """Helper: create a minimal IssueRecord."""
    return IssueRecord(
        project=project, key=key, issuetype=issuetype, status="Done",
        created=datetime(2025, 1, 1), component="", first_date=datetime(2025, 1, 2),
        implementation_date=None, closed_date=closed, stage_minutes={}, resolution="",
    )


def _cfd(day: date) -> CfdRecord:
    """Helper: create a minimal CfdRecord."""
    return CfdRecord(day=day, stage_counts={"Funnel": 1})


@pytest.fixture
def sample_data() -> ReportData:
    return ReportData(
        issues=[
            _issue("A-1", project="ART_A", closed=datetime(2025, 3, 1)),
            _issue("A-2", project="ART_A", closed=datetime(2025, 6, 15)),
            _issue("B-1", project="ART_B", closed=datetime(2025, 9, 1)),
            _issue("X-1", project="ART_A", issuetype="Bug", closed=datetime(2025, 4, 1)),
            _issue("N-1", project="ART_A", closed=None),
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
    def test_empty_config_returns_all_issues(self, sample_data):
        result = apply_filters(sample_data, FilterConfig())
        assert len(result.issues) == len(sample_data.issues)

    def test_empty_config_returns_all_cfd(self, sample_data):
        result = apply_filters(sample_data, FilterConfig())
        assert len(result.cfd) == len(sample_data.cfd)

    def test_stages_preserved(self, sample_data):
        result = apply_filters(sample_data, FilterConfig())
        assert result.stages == sample_data.stages

    def test_source_prefix_preserved(self, sample_data):
        result = apply_filters(sample_data, FilterConfig())
        assert result.source_prefix == "TEST"

    def test_original_data_not_mutated(self, sample_data):
        original_count = len(sample_data.issues)
        apply_filters(sample_data, FilterConfig(projects=["ART_A"]))
        assert len(sample_data.issues) == original_count


class TestDateFilter:
    def test_from_date_excludes_earlier(self, sample_data):
        cfg = FilterConfig(from_date=date(2025, 5, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-1" not in keys   # closed 2025-03-01

    def test_to_date_excludes_later(self, sample_data):
        cfg = FilterConfig(to_date=date(2025, 5, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-2" not in keys   # closed 2025-06-15
        assert "B-1" not in keys   # closed 2025-09-01

    def test_date_range_inclusive_bounds(self, sample_data):
        cfg = FilterConfig(from_date=date(2025, 3, 1), to_date=date(2025, 6, 15))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "A-1" in keys
        assert "A-2" in keys

    def test_no_closed_date_excluded_when_range_set(self, sample_data):
        cfg = FilterConfig(from_date=date(2025, 1, 1))
        result = apply_filters(sample_data, cfg)
        keys = {i.key for i in result.issues}
        assert "N-1" not in keys

    def test_cfd_filtered_by_date(self, sample_data):
        cfg = FilterConfig(from_date=date(2025, 3, 1), to_date=date(2025, 7, 1))
        result = apply_filters(sample_data, cfg)
        assert len(result.cfd) == 1
        assert result.cfd[0].day == date(2025, 6, 1)


class TestProjectFilter:
    def test_single_project(self, sample_data):
        cfg = FilterConfig(projects=["ART_B"])
        result = apply_filters(sample_data, cfg)
        assert all(i.project == "ART_B" for i in result.issues)
        assert len(result.issues) == 1

    def test_multiple_projects(self, sample_data):
        cfg = FilterConfig(projects=["ART_A", "ART_B"])
        result = apply_filters(sample_data, cfg)
        projects = {i.project for i in result.issues}
        assert projects == {"ART_A", "ART_B"}


class TestIssuetypeFilter:
    def test_single_type(self, sample_data):
        cfg = FilterConfig(issuetypes=["Bug"])
        result = apply_filters(sample_data, cfg)
        assert len(result.issues) == 1
        assert result.issues[0].key == "X-1"

    def test_combined_project_and_type(self, sample_data):
        cfg = FilterConfig(projects=["ART_A"], issuetypes=["Feature"])
        result = apply_filters(sample_data, cfg)
        assert all(i.project == "ART_A" and i.issuetype == "Feature"
                   for i in result.issues)
