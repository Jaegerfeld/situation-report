# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die C1-/C2-Register und ihre Darstellung: zentrale
#   Error-Budget-/Status-Regel (gleiche Beurteilung für jede Quelle),
#   DORA-Tier-Schwellen exakt an den Grenzen, Parsen/Roundtrip beider
#   Register, HTML-Rendering (breached/low zuerst, Solution-Spalte,
#   Quellen-Spalte) und die Collector im Aggregator.
# =============================================================================

from __future__ import annotations

import pytest

from portfolio.aggregator import _collect_delivery, _collect_slo
from portfolio.dora_config import (
    DeliveryRegister,
    change_failure_tier,
    deployment_frequency_tier,
    lead_time_tier,
    load_delivery,
    parse_delivery,
    restore_tier,
    save_delivery,
    unit_tier,
)
from portfolio.slo_config import (
    SloRegister,
    error_budget_remaining_pct,
    load_slo,
    parse_slo,
    save_slo,
    slo_status,
)
from portfolio.solution_config import Member, SolutionConfig
from portfolio.summary import render_dora_html, render_slo_html
from sources.base import DoraRecord, QualityRecord, SloRecord


def _slo(sli: float | None, target: float = 99.9) -> SloRecord:
    return SloRecord("API", "availability", target, sli_pct=sli)


class TestSloRules:
    def test_error_budget_math(self) -> None:
        # Ziel 99.9, SLI 99.95: halbes Budget verbraucht -> 50 % Rest.
        assert error_budget_remaining_pct(_slo(99.95)) == 50.0
        # SLI unter Ziel: negatives Restbudget.
        assert error_budget_remaining_pct(_slo(99.8)) == -100.0
        assert error_budget_remaining_pct(_slo(None)) is None

    def test_status_rule_identical_for_every_source(self) -> None:
        assert slo_status(_slo(99.99)) == "met"          # 90 % Budget übrig
        assert slo_status(_slo(99.92)) == "at_risk"       # 20 % übrig < 25 %
        assert slo_status(_slo(99.8)) == "breached"
        assert slo_status(_slo(None)) == "unknown"

    def test_target_100_has_no_budget(self) -> None:
        assert slo_status(_slo(100.0, target=100.0)) == "met"
        assert slo_status(_slo(99.99, target=100.0)) == "breached"

    def test_parse_and_roundtrip(self, tmp_path) -> None:
        register = SloRegister(records=[_slo(99.95)])
        path = tmp_path / "slo.json"
        save_slo(path, register)
        assert load_slo(path) == register
        with pytest.raises(ValueError, match="kind"):
            parse_slo({"kind": "dora", "records": []})
        with pytest.raises(ValueError, match="service"):
            parse_slo({"records": [{"slo": "x", "target_pct": 99}]})


class TestDoraTiers:
    def test_thresholds_at_the_published_boundaries(self) -> None:
        assert deployment_frequency_tier(DoraRecord("u", deployments_per_day=1.0)) == "elite"
        assert deployment_frequency_tier(DoraRecord("u", deployments_per_day=0.2)) == "high"
        assert lead_time_tier(DoraRecord("u", lead_time_hours=24.0)) == "elite"
        assert lead_time_tier(DoraRecord("u", lead_time_hours=800.0)) == "low"
        assert change_failure_tier(DoraRecord("u", change_failure_rate_pct=5.0)) == "elite"
        assert change_failure_tier(DoraRecord("u", change_failure_rate_pct=38.0)) == "low"
        assert restore_tier(DoraRecord("u", time_to_restore_hours=0.5)) == "elite"
        assert restore_tier(DoraRecord("u", time_to_restore_hours=30.0)) == "medium"

    def test_unit_tier_is_worst_known(self) -> None:
        record = DoraRecord("u", deployments_per_day=2.0,
                            lead_time_hours=None,
                            change_failure_rate_pct=38.0)
        assert unit_tier(record) == "low"
        assert unit_tier(DoraRecord("u")) == "unknown"

    def test_parse_both_shapes_and_roundtrip(self, tmp_path) -> None:
        register = DeliveryRegister(
            dora=[DoraRecord("A", deployments_per_day=1.0)],
            quality=[QualityRecord("A", coverage_pct=80.0)])
        path = tmp_path / "delivery.json"
        save_delivery(path, register)
        assert load_delivery(path) == register
        single = parse_delivery({"kind": "dora", "records": [
            {"unit": "B", "deployments_per_day": 0.5}]})
        assert single.dora[0].unit == "B" and single.quality == []
        with pytest.raises(ValueError, match="unit"):
            parse_delivery({"dora": [{"deployments_per_day": 1}]})


class TestRendering:
    def _slo_entries(self):
        return [("Sol A", _slo(99.99)), ("Sol B", _slo(99.1, target=99.5)),
                ("Sol A", _slo(99.92))]

    def test_slo_breached_sorts_first_with_status_colors(self) -> None:
        html = render_slo_html(self._slo_entries())
        assert "3 SLOs (1 breached, 1 at risk)" in html
        rows = html.split("<tr>")
        assert "breached" in rows[2]  # erste Datenzeile
        assert "<th>Solution</th>" in html
        assert "#f8d7da" in html

    def test_slo_empty_renders_nothing(self) -> None:
        assert render_slo_html([]) == ""

    def test_dora_worst_first_and_quality_table(self) -> None:
        dora = [("Sol A", DoraRecord("ART 1", deployments_per_day=1.5,
                                     lead_time_hours=12.0,
                                     change_failure_rate_pct=4.0,
                                     time_to_restore_hours=0.5)),
                ("Sol B", DoraRecord("ART 9", deployments_per_day=0.02,
                                     lead_time_hours=800.0,
                                     change_failure_rate_pct=38.0,
                                     time_to_restore_hours=30.0))]
        quality = [("Sol B", QualityRecord("ART 9", coverage_pct=31.0,
                                           maintainability="D",
                                           critical_issues=7))]
        html = render_dora_html(dora, quality)
        assert "worst tier: low" in html
        assert html.index("ART 9") < html.index("ART 1")  # low zuerst
        assert "Code quality" in html
        assert ">7</td>" in html and "#f8d7da" in html

    def test_dora_empty_renders_nothing(self) -> None:
        assert render_dora_html([], []) == ""


class TestCollectors:
    def test_solution_entries_labelled_and_broken_files_skipped(self, tmp_path) -> None:
        slo_path = tmp_path / "slo.json"
        save_slo(slo_path, SloRegister(records=[_slo(99.95)]))
        delivery_path = tmp_path / "delivery.json"
        save_delivery(delivery_path, DeliveryRegister(
            dora=[DoraRecord("A", deployments_per_day=1.0)],
            quality=[QualityRecord("A", coverage_pct=70.0)]))
        cfg = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            slo=str(slo_path), dora=str(delivery_path))
        slo_entries = _collect_slo(cfg, log=lambda m: None)
        dora_entries, quality_entries = _collect_delivery(cfg, log=lambda m: None)
        assert [(s, r.service) for s, r in slo_entries] == [("Sol", "API")]
        assert len(dora_entries) == 1 and len(quality_entries) == 1

        bad = tmp_path / "bad.json"
        bad.write_text("{broken", encoding="utf-8")
        cfg_bad = SolutionConfig(
            name="Sol", members=[Member(name="A", issue_times="x.xlsx")],
            slo=str(bad), dora=str(bad))
        warnings: list[str] = []
        assert _collect_slo(cfg_bad, log=warnings.append) == []
        assert _collect_delivery(cfg_bad, log=warnings.append) == ([], [])
        assert sum("skipped" in w for w in warnings) == 2
