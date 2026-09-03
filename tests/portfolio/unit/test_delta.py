# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das Delta-Briefing (D2, deterministischer Kern):
#   Snapshot-Roundtrip/Validierung, compute_delta (Kennzahl-Deltas auf
#   Anzeigegenauigkeit, Konfidenz-Wechsel, Governance-Übergänge inkl.
#   „newly overdue", Fehlerfälle), HTML-/Markdown-Rendering und der
#   CLI-Weg --delta. Alles synthetisch — kein Szenario-Bau nötig.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.delta import (
    compute_delta,
    delta_to_markdown,
    render_delta_html,
)
from portfolio.snapshot import (
    Snapshot,
    load_snapshot,
    parse_snapshot,
    save_snapshot,
    snapshot_to_dict,
)

PREV_DAY = date(2025, 6, 16)
NOW_DAY = date(2025, 6, 30)


def _snapshot(as_of: date, **overrides) -> Snapshot:
    base = dict(
        name="Demo",
        kind="portfolio",
        as_of=as_of,
        created="2025-06-30T12:00:00",
        target_ct=90,
        total={"label": "Demo", "items": 100, "completed": 60, "open": 40,
               "median_ct": 8.44, "p85_ct": 18.0, "p95_ct": 30.0,
               "target_ct_pct": 95.0, "median_lt": 16.44, "p85_lt": 39.0},
        units=[{"label": "A", "items": 50, "completed": 30, "open": 20,
                "median_ct": 8.0, "p85_ct": 18.0, "p95_ct": 30.0,
                "target_ct_pct": 95.0, "median_lt": 16.0, "p85_lt": 39.0}],
        sources=[{"label": "ART A", "records": 50, "pct_missing_first": 5.0,
                  "has_cfd": True, "data_as_of": "2025-06-29",
                  "confidence": "high"}],
        governance={"risks": [], "dependencies": [], "nfr": [], "runway": [],
                    "capabilities": [], "decisions": []},
    )
    base.update(overrides)
    return Snapshot(**base)


class TestSnapshotRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        snap = _snapshot(NOW_DAY, governance={"risks": [
            {"id": "R-1", "title": "T", "roam": "owned", "impact": "high",
             "owner": "Team", "since": "2025-05-01", "solution": "S"}],
            "dependencies": [], "nfr": [], "runway": [],
            "capabilities": [], "decisions": []})
        path = tmp_path / "snap.json"
        save_snapshot(path, snap)
        assert load_snapshot(path) == snap

    def test_parse_rejects_wrong_schema_and_shape(self) -> None:
        with pytest.raises(ValueError, match="schema"):
            parse_snapshot({**snapshot_to_dict(_snapshot(NOW_DAY)), "schema": 99})
        with pytest.raises(ValueError, match="JSON object"):
            parse_snapshot([])
        with pytest.raises(ValueError, match="Invalid snapshot"):
            parse_snapshot({"schema": 1, "as_of": "2025-06-30"})


class TestComputeDelta:
    def test_rejects_mismatched_names_and_reversed_order(self) -> None:
        with pytest.raises(ValueError, match="different reports"):
            compute_delta(_snapshot(PREV_DAY, name="X"), _snapshot(NOW_DAY))
        with pytest.raises(ValueError, match="reversed"):
            compute_delta(_snapshot(NOW_DAY), _snapshot(PREV_DAY))

    def test_quiet_when_nothing_changed(self) -> None:
        delta = compute_delta(_snapshot(PREV_DAY), _snapshot(NOW_DAY))
        assert delta.quiet
        assert delta.period_days == 14
        assert "No changes" in delta_to_markdown(delta)
        assert "No changes" in render_delta_html(delta)

    def test_display_precision_hides_invisible_float_changes(self) -> None:
        # 16.44 -> 16.36 rundet beidseitig auf 16.4 — kein sichtbares Delta.
        now = _snapshot(NOW_DAY)
        now.total = {**now.total, "median_lt": 16.36, "completed": 75}
        delta = compute_delta(_snapshot(PREV_DAY), now)
        assert delta.total is not None
        assert "median_lt" not in delta.total.fields
        assert delta.total.fields["completed"] == (60, 75)
        assert delta.completed_delta == 15

    def test_confidence_transition_marks_worsening(self) -> None:
        now = _snapshot(NOW_DAY)
        now.sources = [{**now.sources[0], "confidence": "low"}]
        delta = compute_delta(_snapshot(PREV_DAY), now)
        [change] = delta.confidence_changes
        assert change.entry_id == "ART A"
        assert change.fields["confidence"] == ("high", "low")
        assert change.worsened

    def test_governance_added_removed_changed(self) -> None:
        prev = _snapshot(PREV_DAY, governance={
            "risks": [], "nfr": [], "runway": [], "capabilities": [],
            "decisions": [],
            "dependencies": [
                {"id": "D-1", "title": "API", "from": "A", "to": "B",
                 "status": "at_risk", "due": "2025-07-01", "solution": "S"},
                {"id": "D-9", "title": "Gone", "from": "A", "to": "B",
                 "status": "done", "due": None, "solution": "S"}]})
        now = _snapshot(NOW_DAY, governance={
            "risks": [{"id": "R-9", "title": "New risk", "roam": "owned",
                       "impact": "high", "owner": "T", "since": "2025-06-25",
                       "solution": "S"}],
            "nfr": [], "runway": [], "capabilities": [], "decisions": [],
            "dependencies": [
                {"id": "D-1", "title": "API", "from": "A", "to": "B",
                 "status": "blocked", "due": "2025-07-01", "solution": "S"}]})
        delta = compute_delta(prev, now)
        deps = delta.governance["dependencies"]
        [changed] = deps.changed
        assert changed.fields["status"] == ("at_risk", "blocked")
        assert changed.worsened
        assert [e["id"] for e in deps.removed] == ["D-9"]
        assert [e["id"] for e in delta.governance["risks"].added] == ["R-9"]

    def test_newly_overdue_only_when_flipping(self) -> None:
        entry = {"id": "RW-1", "title": "Gap", "status": "gap",
                 "needed_by": "2025-06-20", "solution": "S"}
        prev = _snapshot(PREV_DAY, governance={
            "risks": [], "dependencies": [], "nfr": [], "capabilities": [],
            "decisions": [], "runway": [dict(entry)]})
        now = _snapshot(NOW_DAY, governance={
            "risks": [], "dependencies": [], "nfr": [], "capabilities": [],
            "decisions": [], "runway": [dict(entry)]})
        delta = compute_delta(prev, now)
        # needed_by 20.06.: am 16.06. noch nicht überfällig, am 30.06. schon.
        assert [e["id"] for e in delta.governance["runway"].newly_overdue] \
            == ["RW-1"]
        # War es schon vorher überfällig, ist es kein NEUER Befund.
        early = {**entry, "needed_by": "2025-06-10"}
        prev.governance["runway"] = [early]
        now.governance["runway"] = [dict(early)]
        assert compute_delta(prev, now).governance["runway"].newly_overdue == []

    def test_open_assumption_expiry_flip(self) -> None:
        entry = {"id": "AS-1", "kind": "assumption", "title": "Guess",
                 "status": "open", "review_by": "2025-06-25", "solution": "S"}
        prev = _snapshot(PREV_DAY, governance={
            "risks": [], "dependencies": [], "nfr": [], "runway": [],
            "capabilities": [], "decisions": [dict(entry)]})
        now = _snapshot(NOW_DAY, governance={
            "risks": [], "dependencies": [], "nfr": [], "runway": [],
            "capabilities": [], "decisions": [dict(entry)]})
        delta = compute_delta(prev, now)
        assert [e["id"] for e in delta.governance["decisions"].newly_overdue] \
            == ["AS-1"]
        # Eine bestätigte Annahme verfällt nicht.
        confirmed = {**entry, "status": "confirmed"}
        now.governance["decisions"] = [confirmed]
        prev.governance["decisions"] = [dict(confirmed)]
        assert compute_delta(prev, now).governance["decisions"].newly_overdue \
            == []


class TestRendering:
    def _story_delta(self):
        prev = _snapshot(PREV_DAY)
        now = _snapshot(NOW_DAY)
        now.total = {**now.total, "completed": 75, "open": 55}
        now.sources = [{**now.sources[0], "confidence": "low"}]
        now.governance = {**now.governance, "risks": [
            {"id": "R-9", "title": "New risk", "roam": "owned",
             "impact": "high", "owner": "T", "since": "2025-06-25",
             "solution": "S"}]}
        return compute_delta(prev, now)

    def test_html_highlights_and_sections(self) -> None:
        html = render_delta_html(self._story_delta())
        assert html.startswith("<!DOCTYPE html>")
        assert "Delta Briefing — Demo" in html
        assert "+15 items completed" in html
        assert "class='worse'" in html            # Konfidenz-Verfall rot
        assert "ROAM risks" in html and "R-9" in html
        assert "Dependencies" not in html          # leere Sektion fehlt

    def test_markdown_contract(self) -> None:
        md = delta_to_markdown(self._story_delta())
        assert md.splitlines()[0] == "# Delta Briefing — Demo"
        assert "## Data confidence" in md
        assert "- ART A: high → low" in md
        assert "- new: [S] R-9: New risk" in md


class TestCliDelta:
    def test_cli_delta_writes_markdown_and_html(self, tmp_path, capsys) -> None:
        from portfolio.cli import run_delta_briefing
        prev_p = tmp_path / "prev.json"
        now_p = tmp_path / "now.json"
        save_snapshot(prev_p, _snapshot(PREV_DAY))
        now = _snapshot(NOW_DAY)
        now.total = {**now.total, "completed": 75}
        save_snapshot(now_p, now)

        run_delta_briefing(prev_p, now_p, output=None, log=lambda m: None)
        assert "# Delta Briefing — Demo" in capsys.readouterr().out

        md_file = tmp_path / "delta.md"
        run_delta_briefing(prev_p, now_p, output=md_file, log=lambda m: None)
        assert "+15 items completed" in md_file.read_text(encoding="utf-8")

        html_file = tmp_path / "delta.html"
        run_delta_briefing(prev_p, now_p, output=html_file, log=lambda m: None)
        assert html_file.read_text(encoding="utf-8").startswith("<!DOCTYPE")
