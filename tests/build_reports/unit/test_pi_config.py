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
    """Write a dict as JSON to a temp file and return its Path."""
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_pi_config — date mode
# ---------------------------------------------------------------------------

class TestLoadPiConfigDateMode:
    def test_loads_two_intervals(self, tmp_path):
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
        cfg = _write_json(tmp_path, {
            "mode": "date",
            "intervals": [
                {"name": "Sprint 1", "from": "2025-01-01", "to": "2025-01-14"},
            ],
        })
        intervals = load_pi_config(cfg)
        assert intervals[0].name == "Sprint 1"

    def test_from_and_to_dates(self, tmp_path):
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
        """mode key is optional; omitting it defaults to date mode."""
        cfg = _write_json(tmp_path, {
            "intervals": [
                {"name": "PI", "from": "2025-01-01", "to": "2025-12-31"},
            ],
        })
        intervals = load_pi_config(cfg)
        assert intervals[0].from_date == date(2025, 1, 1)

    def test_empty_intervals_returns_empty_list(self, tmp_path):
        cfg = _write_json(tmp_path, {"mode": "date", "intervals": []})
        assert load_pi_config(cfg) == []


# ---------------------------------------------------------------------------
# load_pi_config — week mode
# ---------------------------------------------------------------------------

class TestLoadPiConfigWeekMode:
    def test_from_date_is_monday_of_from_week(self, tmp_path):
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
    def test_single_quarter_within_range(self):
        intervals = default_quarter_intervals(date(2025, 2, 1), date(2025, 2, 28))
        assert len(intervals) == 1
        assert intervals[0].name == "2025 Q1"

    def test_covers_full_year(self):
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 12, 31))
        assert len(intervals) == 4
        names = [iv.name for iv in intervals]
        assert names == ["2025 Q1", "2025 Q2", "2025 Q3", "2025 Q4"]

    def test_q1_starts_jan_1(self):
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert intervals[0].from_date == date(2025, 1, 1)

    def test_q1_ends_mar_31(self):
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert intervals[0].to_date == date(2025, 3, 31)

    def test_q4_ends_dec_31(self):
        intervals = default_quarter_intervals(date(2025, 10, 1), date(2025, 12, 31))
        assert intervals[-1].to_date == date(2025, 12, 31)

    def test_spans_year_boundary(self):
        intervals = default_quarter_intervals(date(2025, 11, 1), date(2026, 2, 28))
        names = [iv.name for iv in intervals]
        assert "2025 Q4" in names
        assert "2026 Q1" in names

    def test_returns_pi_interval_objects(self):
        intervals = default_quarter_intervals(date(2025, 1, 1), date(2025, 3, 31))
        assert all(isinstance(iv, PIInterval) for iv in intervals)


# ---------------------------------------------------------------------------
# assign_pi
# ---------------------------------------------------------------------------

class TestAssignPi:
    @pytest.fixture
    def intervals(self):
        return [
            PIInterval("Q1", date(2025, 1, 1), date(2025, 3, 31)),
            PIInterval("Q2", date(2025, 4, 1), date(2025, 6, 30)),
        ]

    def test_date_in_first_interval(self, intervals):
        assert assign_pi(date(2025, 2, 15), intervals) == "Q1"

    def test_date_in_second_interval(self, intervals):
        assert assign_pi(date(2025, 5, 1), intervals) == "Q2"

    def test_on_from_date_boundary(self, intervals):
        assert assign_pi(date(2025, 1, 1), intervals) == "Q1"

    def test_on_to_date_boundary(self, intervals):
        assert assign_pi(date(2025, 3, 31), intervals) == "Q1"

    def test_on_interval_boundary(self, intervals):
        assert assign_pi(date(2025, 4, 1), intervals) == "Q2"

    def test_date_before_all_intervals_returns_none(self, intervals):
        assert assign_pi(date(2024, 12, 31), intervals) is None

    def test_date_after_all_intervals_returns_none(self, intervals):
        assert assign_pi(date(2025, 7, 1), intervals) is None

    def test_empty_intervals_returns_none(self):
        assert assign_pi(date(2025, 1, 1), []) is None
