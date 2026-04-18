# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für pi_config.py: load_pi_config (date- und week-Modus),
#   default_quarter_intervals und assign_pi. Alle Tests verwenden synthetische
#   Fixtures und keine externen Ressourcen.
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from build_reports.pi_config import (
    PIInterval, assign_pi, default_quarter_intervals, load_pi_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(tmp_path: Path, data: dict, name: str = "pi.json") -> Path:
    """Write a dict as JSON to a temp file and return its Path.

    Args:
        tmp_path: pytest temporary directory.
        data:     Dict to serialise as JSON.
        name:     Filename within tmp_path (default 'pi.json').

    Returns:
        Path to the written JSON file.
    """
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_pi_config — date mode
# ---------------------------------------------------------------------------

class TestLoadPiConfigDateMode:
    """Tests for load_pi_config() in 'date' mode — ISO date strings for interval bounds."""

    def test_loads_two_intervals(self, tmp_path):
        """Two intervals defined in the config file produce two PIInterval objects."""
        cfg = _write_json(tmp_path, {
            "mode": "date",
            "intervals": [
                {"name": "PI 1", "from": "2025-01-01", "to": "2025-03-31"},
                {"name": "PI 2", "from": "2025-04-01", "to": "2025-06-30"},
            ],
        })
        intervals = load_pi_config(cfg)
        assert len(intervals) == 2

    def test_interval_names(self, tmp_path):
        """Interval name is read correctly from the config JSON."""
        cfg = _write_json(tmp_path, {
            "mode": "date",
            "intervals": [
                {"name": "Sprint 1", "from": "2025-01-01", "to": "2025-01-14"},
            ],
        })
        intervals = load_pi_config(cfg)
        assert intervals[0].name == "Sprint 1"

    def test_from_and_to_dates(self, tmp_path):
        """from_date and to_date are parsed to the correct date objects."""
        cfg = _write_json(tmp_path, {
            "mode": "date",
            "intervals": [
                {"name": "Q1", "from": "2025-01-01", "to": "2025-03-31"},
            ],
        })
        iv = load_pi_config(cfg)[0]
        assert iv.from_date == date(2025, 1, 1)
        assert iv.to_date == date(2025, 3, 31)

    def test_default_mode_is_date(self, tmp_path):
        """Omitting the 'mode' key defaults to date mode."""
        cfg = _write_json(tmp_path, {
            "intervals": [
                {"name": "PI", "from": "2025-01-01", "to": "2025-12-31"},
            ],
        })
        intervals = load_pi_config(cfg)
        assert intervals[0].from_date == date(2025, 1, 1)

    def test_empty_intervals_returns_empty_list(self, tmp_path):
        """An empty 'intervals' array produces an empty list."""
        cfg = _write_json(tmp_path, {"mode": "date", "intervals": []})
        assert load_pi_config(cfg) == []


# ---------------------------------------------------------------------------
# load_pi_config — week mode
# ---------------------------------------------------------------------------

class TestLoadPiConfigWeekMode:
    """Tests for load_pi_config() in 'week' mode — ISO week strings for interval bounds."""

    def test_from_date_is_monday_of_from_week(self, tmp_path):
        """from_date is set to the Monday of the specified ISO from-week."""
        cfg = _write_json(tmp_path, {
            "mode": "week",
            "intervals": [
                {"name": "PI 1", "from": "2025.02", "to": "2025.13"},
            ],
        })
        iv = load_pi_config(cfg)[0]
        # ISO week 2 of 2025 starts on Monday 2025-01-06
        assert iv.from_date == date(2025, 1, 6)

    def test_to_date_is_sunday_of_to_week(self, tmp_path):
        """to_date is set to the Sunday of the specified ISO to-week."""
        cfg = _write_json(tmp_path, {
            "mode": "week",
            "intervals": [
                {"name": "PI 1", "from": "2025.02", "to": "2025.13"},
            ],
        })
        iv = load_pi_config(cfg)[0]
        # ISO week 13 of 2025 ends on Sunday 2025-03-30
        assert iv.to_date == date(2025, 3, 30)

    def test_invalid_week_format_raises_value_error(self, tmp_path):
        """An invalid week string (e.g. using '-' instead of '.') raises an error."""
        cfg = _write_json(tmp_path, {
            "mode": "week",
            "intervals": [
                {"name": "PI 1", "from": "2025-02", "to": "2025-13"},
            ],
        })
        with pytest.raises((ValueError, Exception)):
            load_pi_config(cfg)


# ---------------------------------------------------------------------------
# default_quarter_intervals
# ---------------------------------------------------------------------------

class TestDefaultQuarterIntervals:
    """Tests for default_quarter_intervals() — automatic quarterly PI generation."""

    def test_single_quarter_within_range(self):
        """A range within one quarter produces exactly one interval."""
        intervals = default_quarter_intervals(date(2025, 2, 1), date(2025, 2, 28))
        assert len(intervals) == 1
        assert intervals[0].name == "2025 Q1"

    def test_covers_full_year(self):
        """A full-year range produces four quarterly intervals."""
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 12, 31))
        assert len(intervals) == 4
        names = [iv.name for iv in intervals]
        assert names == ["2025 Q1", "2025 Q2", "2025 Q3", "2025 Q4"]

    def test_q1_starts_jan_1(self):
        """Q1 from_date is always January 1st."""
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert intervals[0].from_date == date(2025, 1, 1)

    def test_q1_ends_mar_31(self):
        """Q1 to_date is always March 31st."""
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert intervals[0].to_date == date(2025, 3, 31)

    def test_q4_ends_dec_31(self):
        """Q4 to_date is always December 31st."""
        intervals = default_quarter_intervals(date(2025, 10, 1), date(2025, 12, 31))
        assert intervals[-1].to_date == date(2025, 12, 31)

    def test_spans_year_boundary(self):
        """Ranges crossing a year boundary produce intervals for both years."""
        intervals = default_quarter_intervals(date(2025, 11, 1), date(2026, 2, 28))
        names = [iv.name for iv in intervals]
        assert "2025 Q4" in names
        assert "2026 Q1" in names

    def test_returns_pi_interval_objects(self):
        """All returned items are PIInterval instances."""
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert all(isinstance(iv, PIInterval) for iv in intervals)


# ---------------------------------------------------------------------------
# assign_pi
# ---------------------------------------------------------------------------

class TestAssignPi:
    """Tests for assign_pi() — mapping a date to its PI interval name."""

    @pytest.fixture
    def intervals(self) -> list[PIInterval]:
        """Two consecutive quarterly PIInterval objects for 2025 H1."""
        return [
            PIInterval("Q1", date(2025, 1, 1), date(2025, 3, 31)),
            PIInterval("Q2", date(2025, 4, 1), date(2025, 6, 30)),
        ]

    def test_date_in_first_interval(self, intervals):
        """A date within Q1 returns 'Q1'."""
        assert assign_pi(date(2025, 2, 15), intervals) == "Q1"

    def test_date_in_second_interval(self, intervals):
        """A date within Q2 returns 'Q2'."""
        assert assign_pi(date(2025, 5, 1), intervals) == "Q2"

    def test_on_from_date_boundary(self, intervals):
        """A date exactly on an interval's from_date is included (inclusive)."""
        assert assign_pi(date(2025, 1, 1), intervals) == "Q1"

    def test_on_to_date_boundary(self, intervals):
        """A date exactly on an interval's to_date is included (inclusive)."""
        assert assign_pi(date(2025, 3, 31), intervals) == "Q1"

    def test_on_interval_boundary(self, intervals):
        """A date on the first day of Q2 is correctly assigned to Q2."""
        assert assign_pi(date(2025, 4, 1), intervals) == "Q2"

    def test_date_before_all_intervals_returns_none(self, intervals):
        """A date before all intervals returns None."""
        assert assign_pi(date(2024, 12, 31), intervals) is None

    def test_date_after_all_intervals_returns_none(self, intervals):
        """A date after all intervals returns None."""
        assert assign_pi(date(2025, 7, 1), intervals) is None

    def test_empty_intervals_returns_none(self):
        """An empty interval list always returns None."""
        assert assign_pi(date(2025, 1, 1), []) is None
