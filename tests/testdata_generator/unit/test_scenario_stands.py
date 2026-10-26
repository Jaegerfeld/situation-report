# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Stände-Reihe des Demo-Datenraums (Beta Schnitt 1b,
#   Entscheidung E3): N Stände im 14-Tage-Rhythmus, stands.json, prev/now
#   als Aliasse der letzten beiden, Delta-Briefings aller Folgepaare als
#   Markdown und HTML, Wachstum über die Reihe, Grenzen, Fortschreibung
#   hängt einen Stand an.
# =============================================================================

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from portfolio.delta import compute_delta
from portfolio.snapshot import load_snapshot
from testdata_generator.scenario import (
    DEFAULT_STANDS,
    MAX_STANDS,
    MIN_STANDS,
    STAND_INTERVAL_DAYS,
    build_portfolio_scenario,
)
from testdata_generator.scenario_continue import continue_portfolio_scenario
from testdata_generator.structure import TEMPLATE_SMALL, structure_template

REF = date(2025, 6, 30)


@pytest.fixture(scope="module")
def series(tmp_path_factory):
    out = tmp_path_factory.mktemp("series")
    messages: list[str] = []
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=messages.append,
                                     scale="s")
    return out, paths, messages


class TestSeries:
    def test_default_is_six_stands_two_weeks_apart(self, series) -> None:
        out, paths, _ = series
        assert DEFAULT_STANDS == 6
        assert len(paths["snapshots"]) == 6
        dates = [load_snapshot(p).as_of for p in paths["snapshots"]]
        assert dates[-1] == REF
        assert all((b - a).days == STAND_INTERVAL_DAYS for a, b in zip(dates, dates[1:]))
        assert dates[0] == REF - timedelta(days=STAND_INTERVAL_DAYS * 5)
        names = sorted(p.name for p in (out / "snapshots").glob("snapshot_??_*.json"))
        assert names[0].startswith("snapshot_01_") and names[-1].startswith("snapshot_06_")

    def test_index_lists_every_stand(self, series) -> None:
        out, paths, _ = series
        index = json.loads(paths["stands"].read_text(encoding="utf-8"))
        assert index["schema"] == 1 and index["interval_days"] == STAND_INTERVAL_DAYS
        assert [s["index"] for s in index["stands"]] == [1, 2, 3, 4, 5, 6]
        assert index["stands"][-1]["as_of"] == REF.isoformat()
        for entry in index["stands"]:
            assert (out / "snapshots" / entry["file"]).is_file()

    def test_prev_and_now_are_the_last_two_stands(self, series) -> None:
        _, paths, _ = series
        assert paths["snapshot_prev"].read_bytes() == paths["snapshots"][-2].read_bytes()
        assert paths["snapshot_now"].read_bytes() == paths["snapshots"][-1].read_bytes()

    def test_deltas_for_every_consecutive_pair(self, series) -> None:
        out, paths, _ = series
        assert len(paths["deltas"]) == 5
        for k, (md, html) in enumerate(paths["deltas"], start=1):
            assert md.name == f"delta_{k:02d}-{k + 1:02d}.md" and md.is_file()
            assert html.name == f"delta_{k:02d}-{k + 1:02d}.html" and html.is_file()
            text = md.read_text(encoding="utf-8")
            assert text.startswith("# Delta Briefing — Demo Portfolio")
            assert f"({STAND_INTERVAL_DAYS} days)" in text
            assert html.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
        assert sorted(p.name for p in (out / "deltas").iterdir()) == sorted(
            f"delta_{k:02d}-{k + 1:02d}.{ext}" for k in range(1, 6) for ext in ("md", "html"))

    def test_the_world_grows_along_the_series(self, series) -> None:
        _, paths, _ = series
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        items = [int(s.total["items"]) for s in snaps]
        assert items == sorted(items) and items[0] < items[-1]
        for prev, now in zip(snaps, snaps[1:]):
            delta = compute_delta(prev, now)
            assert delta.period_days == STAND_INTERVAL_DAYS
            assert delta.completed_delta > 0

    def test_now_events_switch_on_at_the_last_stand_only(self, series) -> None:
        _, paths, _ = series
        snaps = [load_snapshot(p) for p in paths["snapshots"]]
        # BR-2 (new risk) and the blocked AD-1 belong to the "now" story.
        for s in snaps[:-1]:
            assert "BR-2" not in {r["id"] for r in s.governance["risks"]}
        assert "BR-2" in {r["id"] for r in snaps[-1].governance["risks"]}
        early = compute_delta(snaps[1], snaps[2])
        assert early.governance["risks"].added == []

    def test_readme_and_log_name_the_stands(self, series) -> None:
        _, paths, messages = series
        readme = paths["readme"].read_text(encoding="utf-8")
        assert "## Stände" in readme and "Stand 06: 2025-06-30" in readme
        assert "deltas/delta_05-06.html" in readme
        assert any("6 Stände" in m for m in messages)
        assert any("5 Folgepaare" in m for m in messages)


class TestStandCount:
    def test_two_stands_is_the_minimum_and_yields_one_delta(self, tmp_path) -> None:
        paths = build_portfolio_scenario(tmp_path, seed=1, reference=REF, log=lambda m: None,
                                         scale="s", stands=MIN_STANDS,
                                         structure=structure_template(TEMPLATE_SMALL))
        assert len(paths["snapshots"]) == 2 and len(paths["deltas"]) == 1
        assert load_snapshot(paths["snapshot_prev"]).as_of == REF - timedelta(days=14)

    @pytest.mark.parametrize("bad", [MIN_STANDS - 1, MAX_STANDS + 1, 0])
    def test_out_of_range_is_rejected_before_building(self, tmp_path, bad: int) -> None:
        with pytest.raises(ValueError, match="stands must be"):
            build_portfolio_scenario(tmp_path, reference=REF, log=lambda m: None, stands=bad)
        assert not (tmp_path / "portfolio.json").exists()


class TestContinuationAppendsAStand:
    def test_continue_adds_stand_and_delta(self, tmp_path) -> None:
        paths = build_portfolio_scenario(tmp_path, seed=3, reference=REF, log=lambda m: None,
                                         scale="s", stands=3,
                                         structure=structure_template(TEMPLATE_SMALL))
        new_ref = REF + timedelta(days=21)
        lines: list[str] = []
        continue_portfolio_scenario(tmp_path, new_ref, log=lines.append)
        index = json.loads(paths["stands"].read_text(encoding="utf-8"))
        assert [s["index"] for s in index["stands"]] == [1, 2, 3, 4]
        assert index["stands"][-1]["as_of"] == new_ref.isoformat()
        fourth = tmp_path / "snapshots" / index["stands"][-1]["file"]
        assert fourth.read_bytes() == paths["snapshot_now"].read_bytes()
        assert (tmp_path / "deltas" / "delta_03-04.md").is_file()
        assert (tmp_path / "deltas" / "delta_03-04.html").is_file()
        assert "(21 days)" in (tmp_path / "deltas" / "delta_03-04.md").read_text(encoding="utf-8")
        assert any("Stand 04" in li for li in lines)
