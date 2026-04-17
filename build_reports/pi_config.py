# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.04.2026
# Geändert:       17.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Definiert PI-Intervalle (Planning Iterations) für die Flow Velocity Metrik.
#   Unterstützt zwei Konfigurationsmodi: tagesgenaue Datumsangaben (date) und
#   kalenderwochengenaue Angaben (week, Format YYYY.WW). Wenn keine Konfigdatei
#   angegeben wird, werden Quartale als Standard-PIs generiert.
#
#   Konfigdatei-Format (JSON):
#     date-Modus:   {"mode": "date", "intervals": [{"name": "PI 1",
#                      "from": "2025-01-06", "to": "2025-04-04"}, ...]}
#     week-Modus:   {"mode": "week", "intervals": [{"name": "PI 1",
#                      "from": "2025.02", "to": "2025.13"}, ...]}
# =============================================================================

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class PIInterval:
    """
    A named planning iteration interval.

    Attributes:
        name:      Human-readable label shown on the bar chart.
        from_date: First day of the interval (inclusive).
        to_date:   Last day of the interval (inclusive).
    """
    name: str
    from_date: date
    to_date: date


def _parse_week(week_str: str) -> tuple[int, int]:
    """
    Parse a 'YYYY.WW' string into a (year, week) tuple.

    Args:
        week_str: ISO week string in 'YYYY.WW' format.

    Returns:
        Tuple of (year, week) as integers.

    Raises:
        ValueError: If the format is not 'YYYY.WW'.
    """
    parts = week_str.split(".")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid week format: {week_str!r} — expected YYYY.WW (e.g. '2025.03')"
        )
    return int(parts[0]), int(parts[1])


def load_pi_config(path: str | Path) -> list[PIInterval]:
    """
    Load PI interval definitions from a JSON configuration file.

    Supports two modes controlled by the top-level "mode" key:
    - "date" (default): intervals use YYYY-MM-DD date strings under "from"/"to".
    - "week": intervals use YYYY.WW ISO week strings under "from"/"to".
              from_date is set to Monday of the from-week;
              to_date is set to Sunday of the to-week.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        Ordered list of PIInterval objects as defined in the file.

    Raises:
        ValueError: If a required field is missing or a value cannot be parsed.
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    mode = data.get("mode", "date")
    intervals: list[PIInterval] = []

    for entry in data.get("intervals", []):
        name = entry["name"]
        if mode == "week":
            from_year, from_week = _parse_week(entry["from"])
            to_year, to_week = _parse_week(entry["to"])
            from_date = date.fromisocalendar(from_year, from_week, 1)  # Monday
            to_date = date.fromisocalendar(to_year, to_week, 7)        # Sunday
        else:
            from_date = date.fromisoformat(entry["from"])
            to_date = date.fromisoformat(entry["to"])

        intervals.append(PIInterval(name=name, from_date=from_date, to_date=to_date))

    return intervals


def default_quarter_intervals(from_date: date, to_date: date) -> list[PIInterval]:
    """
    Generate quarterly PI intervals covering the given date range.

    Intervals align to calendar quarters (Q1 = Jan–Mar, Q2 = Apr–Jun,
    Q3 = Jul–Sep, Q4 = Oct–Dec). The first interval starts at the beginning
    of the quarter containing from_date; the last interval ends at the end of
    the quarter containing to_date.

    Args:
        from_date: Start of the date range to cover (inclusive).
        to_date:   End of the date range to cover (inclusive).

    Returns:
        List of PIInterval objects, one per calendar quarter.
    """
    intervals: list[PIInterval] = []
    year = from_date.year
    # first month of the quarter containing from_date (1, 4, 7, or 10)
    month = ((from_date.month - 1) // 3) * 3 + 1

    while True:
        end_month = month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        q_start = date(year, month, 1)
        q_end = date(year, end_month, last_day)

        quarter_num = (month - 1) // 3 + 1
        intervals.append(PIInterval(
            name=f"{year} Q{quarter_num}",
            from_date=q_start,
            to_date=q_end,
        ))

        if q_end >= to_date:
            break

        month += 3
        if month > 12:
            month = 1
            year += 1

    return intervals


def assign_pi(d: date, intervals: list[PIInterval]) -> str | None:
    """
    Find the PI interval that contains the given date.

    Args:
        d:         Date to look up.
        intervals: Ordered list of PIInterval objects to search.

    Returns:
        Name of the matching interval, or None if no interval covers the date.
    """
    for interval in intervals:
        if interval.from_date <= d <= interval.to_date:
            return interval.name
    return None
