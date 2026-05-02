# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für testdata_generator.generator. Prüft die technische
#   Korrektheit der Issue-Generierung: Anzahl, Pflichtfelder, Zeitstempel-
#   Monotonie, Completion-Rate, Seed-Reproduzierbarkeit und Backflow.
# =============================================================================

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from testdata_generator.generator import GeneratorConfig, generate
from testdata_generator.workflow_parser import WorkflowSpec


def _simple_workflow() -> WorkflowSpec:
    """Minimal 4-stage workflow with first and closed markers."""
    return WorkflowSpec(
        stages=["Funnel", "Analysis", "Dev", "Done"],
        status_to_stage={
            "Funnel": "Funnel",
            "Analysis": "Analysis",
            "Dev": "Dev",
            "Done": "Done",
        },
        first_stage="Analysis",
        closed_stage="Done",
        inprogress_stage=None,
    )


def _config(**kwargs) -> GeneratorConfig:
    """Create a GeneratorConfig with sensible test defaults."""
    defaults = dict(
        project_key="TEST",
        issue_count=50,
        from_date=date(2025, 1, 1),
        to_date=date(2025, 12, 31),
        seed=42,
    )
    defaults.update(kwargs)
    return GeneratorConfig(**defaults)


class TestIssueCount:
    def test_output_issue_count_matches_config(self) -> None:
        """Generated issues list length equals issue_count."""
        data = generate(_simple_workflow(), _config(issue_count=30))
        assert len(data["issues"]) == 30

    def test_total_field_matches_issue_count(self) -> None:
        """Top-level 'total' field equals issue_count."""
        data = generate(_simple_workflow(), _config(issue_count=25))
        assert data["total"] == 25

    def test_max_results_field_matches_issue_count(self) -> None:
        """Top-level 'maxResults' field equals issue_count."""
        data = generate(_simple_workflow(), _config(issue_count=25))
        assert data["maxResults"] == 25


class TestRequiredFields:
    @pytest.fixture(scope="class")
    def issues(self) -> list[dict]:
        data = generate(_simple_workflow(), _config(issue_count=20))
        return data["issues"]

    def test_all_have_key(self, issues: list[dict]) -> None:
        """Every issue has a 'key' field."""
        assert all("key" in i for i in issues)

    def test_keys_use_project_prefix(self, issues: list[dict]) -> None:
        """Keys start with the configured project key."""
        assert all(i["key"].startswith("TEST-") for i in issues)

    def test_all_have_current_stage(self, issues: list[dict]) -> None:
        """Every issue has fields.status.name."""
        assert all(i["fields"]["status"]["name"] for i in issues)

    def test_current_stage_is_in_workflow(self, issues: list[dict]) -> None:
        """fields.status.name is always a known workflow stage."""
        stages = set(_simple_workflow().stages)
        assert all(i["fields"]["status"]["name"] in stages for i in issues)

    def test_all_have_changelog(self, issues: list[dict]) -> None:
        """Every issue has a 'changelog' dict."""
        assert all("changelog" in i for i in issues)

    def test_all_have_histories(self, issues: list[dict]) -> None:
        """Every issue has changelog.histories list."""
        assert all(isinstance(i["changelog"]["histories"], list) for i in issues)

    def test_all_have_created(self, issues: list[dict]) -> None:
        """Every issue has fields.created."""
        assert all(i["fields"]["created"] for i in issues)

    def test_all_have_project_key(self, issues: list[dict]) -> None:
        """Every issue has fields.project.key matching the config."""
        assert all(i["fields"]["project"]["key"] == "TEST" for i in issues)


class TestTimestamps:
    def test_transition_timestamps_monotonic(self) -> None:
        """Within each issue, history timestamps are non-decreasing."""
        data = generate(_simple_workflow(), _config(issue_count=50))
        for issue in data["issues"]:
            timestamps = [h["created"] for h in issue["changelog"]["histories"]]
            assert timestamps == sorted(timestamps), f"Non-monotonic timestamps in {issue['key']}"

    def test_transitions_not_before_created(self) -> None:
        """No transition timestamp precedes the issue's created timestamp."""
        data = generate(_simple_workflow(), _config(issue_count=50))
        for issue in data["issues"]:
            created = issue["fields"]["created"]
            for h in issue["changelog"]["histories"]:
                assert h["created"] >= created, (
                    f"Transition before created in {issue['key']}: "
                    f"{h['created']} < {created}"
                )

    def test_datetime_format_parseable(self) -> None:
        """Generated datetime strings match Jira format and are parseable."""
        import re
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{4}")
        data = generate(_simple_workflow(), _config(issue_count=10))
        for issue in data["issues"]:
            assert pattern.fullmatch(issue["fields"]["created"])
            for h in issue["changelog"]["histories"]:
                assert pattern.fullmatch(h["created"])


class TestStatusConsistency:
    def test_status_matches_last_transition(self) -> None:
        """fields.status.name equals the toString of the last history entry."""
        data = generate(_simple_workflow(), _config(issue_count=50))
        for issue in data["issues"]:
            histories = issue["changelog"]["histories"]
            if histories:
                last_to = histories[-1]["items"][0]["toString"]
                current = issue["fields"]["status"]["name"]
                assert current == last_to, (
                    f"{issue['key']}: status={current!r} but last transition→{last_to!r}"
                )

    def test_transition_items_have_status_field(self) -> None:
        """All history items have field='status'."""
        data = generate(_simple_workflow(), _config(issue_count=20))
        for issue in data["issues"]:
            for h in issue["changelog"]["histories"]:
                for item in h["items"]:
                    assert item["field"] == "status"

    def test_transition_from_and_to_are_strings(self) -> None:
        """fromString and toString in history items are non-empty strings."""
        data = generate(_simple_workflow(), _config(issue_count=20))
        for issue in data["issues"]:
            for h in issue["changelog"]["histories"]:
                for item in h["items"]:
                    assert isinstance(item["fromString"], str) and item["fromString"]
                    assert isinstance(item["toString"], str) and item["toString"]


class TestCompletionRate:
    def test_completion_rate_one_all_issues_closed(self) -> None:
        """At completion_rate=1.0, every issue reaches the closed stage."""
        wf = _simple_workflow()
        data = generate(wf, _config(issue_count=30, completion_rate=1.0))
        for issue in data["issues"]:
            assert issue["fields"]["status"]["name"] == wf.closed_stage, (
                f"{issue['key']} not closed: {issue['fields']['status']['name']!r}"
            )

    def test_completion_rate_zero_no_issues_closed(self) -> None:
        """At completion_rate=0.0, no issue is in the closed stage."""
        wf = _simple_workflow()
        data = generate(wf, _config(issue_count=30, completion_rate=0.0))
        for issue in data["issues"]:
            assert issue["fields"]["status"]["name"] != wf.closed_stage, (
                f"{issue['key']} unexpectedly closed"
            )

    def test_completion_rate_approximate(self) -> None:
        """With a seeded run and rate=0.7, roughly 60–80% of issues are closed."""
        wf = _simple_workflow()
        data = generate(wf, _config(issue_count=200, completion_rate=0.7, seed=0))
        closed = sum(
            1 for i in data["issues"]
            if i["fields"]["status"]["name"] == wf.closed_stage
        )
        rate = closed / 200
        assert 0.50 <= rate <= 0.85, f"Completion rate {rate:.2f} out of expected range"


class TestSeedReproducibility:
    def test_same_seed_produces_identical_output(self) -> None:
        """Two generate() calls with the same seed produce identical JSON."""
        wf = _simple_workflow()
        cfg = _config(issue_count=20, seed=99)
        out1 = generate(wf, cfg)
        out2 = generate(wf, cfg)
        assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)

    def test_different_seeds_produce_different_output(self) -> None:
        """Two generate() calls with different seeds produce different JSON."""
        wf = _simple_workflow()
        out1 = generate(wf, _config(issue_count=20, seed=1))
        out2 = generate(wf, _config(issue_count=20, seed=2))
        assert json.dumps(out1, sort_keys=True) != json.dumps(out2, sort_keys=True)


class TestBackflow:
    def test_backflow_prob_one_creates_backward_transitions(self) -> None:
        """At backflow_prob=1.0 with enough stages, backward transitions appear."""
        wf = _simple_workflow()  # 4 stages: Funnel, Analysis, Dev, Done
        data = generate(wf, _config(issue_count=50, completion_rate=1.0, backflow_prob=1.0, seed=7))
        stages = wf.stages

        backward_found = False
        for issue in data["issues"]:
            histories = issue["changelog"]["histories"]
            for i in range(1, len(histories)):
                prev_to = histories[i - 1]["items"][0]["toString"]
                curr_from = histories[i]["items"][0]["fromString"]
                curr_to = histories[i]["items"][0]["toString"]
                if (curr_from in stages and curr_to in stages
                        and stages.index(curr_to) < stages.index(curr_from)):
                    backward_found = True
                    break
            if backward_found:
                break

        assert backward_found, "Expected at least one backward transition with backflow_prob=1.0"

    def test_backflow_never_before_first_stage(self) -> None:
        """Backflow never moves an issue before first_stage."""
        wf = _simple_workflow()
        data = generate(wf, _config(issue_count=50, completion_rate=0.5, backflow_prob=1.0, seed=5))
        first_idx = wf.stages.index(wf.first_stage)

        for issue in data["issues"]:
            for h in issue["changelog"]["histories"]:
                to_stage = h["items"][0]["toString"]
                if to_stage in wf.stages:
                    assert wf.stages.index(to_stage) >= first_idx, (
                        f"{issue['key']}: transition to {to_stage!r} before first_stage"
                    )


class TestIssueTypes:
    def test_issue_types_respect_weights(self) -> None:
        """With a large dataset and seed, issue type distribution matches weights."""
        wf = _simple_workflow()
        types = {"Feature": 0.8, "Bug": 0.2}
        data = generate(wf, _config(issue_count=500, issue_types=types, seed=0))
        counts: dict[str, int] = {}
        for issue in data["issues"]:
            t = issue["fields"]["issuetype"]["name"]
            counts[t] = counts.get(t, 0) + 1
        feature_rate = counts.get("Feature", 0) / 500
        assert 0.70 <= feature_rate <= 0.90, (
            f"Feature rate {feature_rate:.2f} outside expected 0.70–0.90"
        )

    def test_only_configured_types_generated(self) -> None:
        """No issue type appears that was not in the configuration."""
        wf = _simple_workflow()
        types = {"Story": 1.0}
        data = generate(wf, _config(issue_count=20, issue_types=types))
        for issue in data["issues"]:
            assert issue["fields"]["issuetype"]["name"] == "Story"


class TestJSONSerializable:
    def test_output_is_json_serializable(self) -> None:
        """generate() output can be serialised to JSON without errors."""
        data = generate(_simple_workflow(), _config(issue_count=10))
        serialised = json.dumps(data)
        assert serialised
