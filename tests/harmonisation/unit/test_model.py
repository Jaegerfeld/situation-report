# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests des Datenmodells: Katalog-, Prozess-, Bewertungs- und
#   Entscheidungs-Parser mit ihren Fehlerfällen, Laden eines
#   Arbeitsbereichs, Rundreise über das Beispiel.
# =============================================================================

from __future__ import annotations

import json
from datetime import date

import pytest

from harmonisation.examples import EXAMPLE_CATALOGUE, write_example
from harmonisation.model import (
    DECISION_STANDARDISE,
    EVIDENCE_DOCUMENTED,
    SCHEMA_VERSION,
    Answer,
    Assessment,
    HarmonisationError,
    assessment_filename,
    assessment_to_json,
    load_workspace,
    parse_assessment,
    parse_catalogue,
    parse_decisions,
    parse_processes,
)

CAT = parse_catalogue(EXAMPLE_CATALOGUE)


class TestCatalogue:
    def test_example_has_three_dimensions_of_eight(self) -> None:
        assert [len(d.questions) for d in CAT.dimensions] == [8, 8, 8]
        assert len(CAT.question_ids) == 24
        assert CAT.dimension_of("it3").id == "it_operations"

    def test_labels_fall_back_to_english(self) -> None:
        q = CAT.dimensions[0].questions[0]
        assert q.label("de").startswith("Der Prozess")
        assert q.label("xx") == q.label("en")
        assert CAT.dimensions[1].label("ro") == "Transparență"

    def test_bare_string_text_counts_as_english(self) -> None:
        cat = parse_catalogue({"schema_version": SCHEMA_VERSION, "dimensions": [
            {"id": "d", "name": "Dim", "questions": [{"id": "q1", "text": "Only text"}]}]})
        assert cat.dimensions[0].questions[0].label("de") == "Only text"

    @pytest.mark.parametrize("bad", [
        {"schema_version": 2, "dimensions": []},
        {"schema_version": SCHEMA_VERSION, "dimensions": []},
        {"schema_version": SCHEMA_VERSION, "dimensions": [{"id": "d", "name": "x", "questions": []}]},
        {"schema_version": SCHEMA_VERSION, "dimensions": [
            {"id": "d", "name": "x", "questions": [{"id": "q", "text": "a"}, {"id": "q", "text": "b"}]}]},
        {"schema_version": SCHEMA_VERSION, "dimensions": [
            {"id": "d", "name": "x", "questions": [{"id": "q", "text": 5}]}]},
    ])
    def test_rejects_broken_catalogues(self, bad: dict) -> None:
        with pytest.raises(HarmonisationError):
            parse_catalogue(bad)


class TestAssessment:
    def test_parses_values_unknown_and_evidence(self) -> None:
        a = parse_assessment({"schema_version": SCHEMA_VERSION, "process": "p", "assessor": "x",
                              "date": "2026-10-12",
                              "answers": {"bv1": {"value": 4, "evidence": EVIDENCE_DOCUMENTED},
                                          "bv2": {"value": None}}}, CAT, "f.json")
        assert a.answers["bv1"] == Answer(4, EVIDENCE_DOCUMENTED)
        assert a.answers["bv2"].value is None
        assert a.day == date(2026, 10, 12) and a.source == "f.json"

    @pytest.mark.parametrize("answers, message", [
        ({"nope": {"value": 1}}, "not in the catalogue"),
        ({"bv1": {"value": 5}}, "0..4"),
        ({"bv1": {"value": True}}, "0..4"),
        ({"bv1": {"value": 1, "evidence": "guess"}}, "unknown"),
        ({"bv1": 3}, "must be an object"),
    ])
    def test_rejects_bad_answers(self, answers: dict, message: str) -> None:
        with pytest.raises(HarmonisationError, match=message):
            parse_assessment({"schema_version": SCHEMA_VERSION, "process": "p",
                              "date": "2026-10-12", "answers": answers}, CAT)

    def test_rejects_bad_date_and_missing_process(self) -> None:
        with pytest.raises(HarmonisationError, match="YYYY-MM-DD"):
            parse_assessment({"schema_version": SCHEMA_VERSION, "process": "p",
                              "date": "12.10.2026", "answers": {}}, CAT)
        with pytest.raises(HarmonisationError, match="no process"):
            parse_assessment({"schema_version": SCHEMA_VERSION, "date": "2026-10-12"}, CAT)

    def test_json_round_trip(self) -> None:
        a = Assessment("p", "Who", date(2026, 1, 2), {"bv1": Answer(2), "bv2": Answer(None)}, "n")
        again = parse_assessment(assessment_to_json(a), CAT)
        assert again.answers == a.answers and again.note == "n"
        assert assessment_filename(a) == "2026-01-02_p_who.json"


class TestProcessesAndDecisions:
    def test_duplicate_process_id_is_an_error(self) -> None:
        with pytest.raises(HarmonisationError):
            parse_processes({"schema_version": SCHEMA_VERSION,
                             "processes": [{"id": "a", "name": "A"}, {"id": "a", "name": "B"}]})

    def test_decision_defaults_and_validation(self) -> None:
        d = parse_decisions({"schema_version": SCHEMA_VERSION,
                             "decisions": {"a": {"decision": DECISION_STANDARDISE, "date": "2026-10-06"}}})
        assert d["a"].day == date(2026, 10, 6) and d["a"].depth == ""
        with pytest.raises(HarmonisationError):
            parse_decisions({"schema_version": SCHEMA_VERSION, "decisions": {"a": {"decision": "maybe"}}})


class TestWorkspace:
    def test_example_round_trips_through_the_folder(self, tmp_path) -> None:
        written = write_example(tmp_path)
        assert len(written) == 2 + 3 + 1
        ws = load_workspace(tmp_path)
        assert [p.id for p in ws.processes] == ["o2d", "c2o", "p2p", "h2r"]
        assert len(ws.assessments) == 3
        assert ws.decisions["o2d"].decision == DECISION_STANDARDISE
        assert ws.root == tmp_path

    def test_names_the_missing_file(self, tmp_path) -> None:
        with pytest.raises(HarmonisationError, match="catalogue.json"):
            load_workspace(tmp_path)

    def test_assessment_for_unknown_process_is_rejected(self, tmp_path) -> None:
        write_example(tmp_path)
        bad = tmp_path / "assessments" / "zzz.json"
        bad.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "process": "ghost",
                                   "date": "2026-10-12", "answers": {}}), encoding="utf-8")
        with pytest.raises(HarmonisationError, match="ghost"):
            load_workspace(tmp_path)

    def test_invalid_json_names_the_file(self, tmp_path) -> None:
        write_example(tmp_path)
        (tmp_path / "decisions.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(HarmonisationError, match="decisions.json"):
            load_workspace(tmp_path)
