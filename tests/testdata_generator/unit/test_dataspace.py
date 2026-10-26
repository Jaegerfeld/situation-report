# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Dienstschicht des Demo-Datenraums (Beta Schnitt 3a): Anfrage mit
#   Vorgaben und Prüfung, Schätzung, Lauf mit Fortschritt je Teilschritt in
#   Prototyp-Reihenfolge, Abbruch zwischen Schritten, Ergebniszahlen,
#   KI-Entwürfe (F3) mit Marker, Prompt-Bündel und Übungsantwort, die
#   `llm check` zurückweist.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from llm.check import load_bundle, run_check
from llm.guard import read_markers
from testdata_generator.ai_drafts import AI_DRAFTS_DIR, PRACTICE_ANSWER, PRACTICE_README
from testdata_generator.dataspace import (
    STATE_DONE,
    STATE_RUNNING,
    STATE_SKIPPED,
    STEPS,
    GenerationCancelled,
    GenerationRequest,
    ProgressEvent,
    estimate_request,
    generate_dataspace,
)
from testdata_generator.story import TEMPLATE_CALM, TEMPLATE_STANDARD
from testdata_generator.structure import structure_from_arts_spec

REF = date(2025, 6, 30)


class TestRequest:
    def test_defaults_and_resolution(self, tmp_path) -> None:
        req = GenerationRequest(output_dir=tmp_path)
        assert req.template == TEMPLATE_STANDARD and req.resolved_stands() == 6
        assert req.resolved_structure().describe() == "1 Portfolio · 2 Solutions · 6 ARTs"
        assert not req.ai_drafts and req.scale == "m"
        assert GenerationRequest(output_dir=tmp_path, template=TEMPLATE_CALM).resolved_stands() == 3
        assert GenerationRequest(output_dir=tmp_path, stands=4).resolved_stands() == 4

    def test_validate_catches_every_refusal_early(self, tmp_path) -> None:
        GenerationRequest(output_dir=tmp_path).validate()
        with pytest.raises(ValueError, match="Unknown story template"):
            GenerationRequest(output_dir=tmp_path, template="drama").validate()
        with pytest.raises(ValueError, match="stands must be"):
            GenerationRequest(output_dir=tmp_path, stands=1).validate()
        with pytest.raises(ValueError, match="Unknown scale"):
            GenerationRequest(output_dir=tmp_path, scale="xl").validate()
        with pytest.raises(ValueError, match="at least one ART"):
            bad = structure_from_arts_spec("1")
            bad.portfolios[0].solutions[0].arts = []
            GenerationRequest(output_dir=tmp_path, structure=bad).validate()

    def test_estimate_follows_request(self, tmp_path) -> None:
        est = estimate_request(GenerationRequest(output_dir=tmp_path, template=TEMPLATE_CALM,
                                                 structure=structure_from_arts_spec("2,1")))
        assert (est.arts, est.stands, est.deltas) == (3, 3, 2)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("service")
    events: list[ProgressEvent] = []
    lines: list[str] = []
    req = GenerationRequest(output_dir=out, reference=REF, scale="s", stands=2,
                            structure=structure_from_arts_spec("2,1"))
    result = generate_dataspace(req, progress=events.append, log=lines.append)
    return result, events, lines


@pytest.fixture(scope="module")
def drafts(tmp_path_factory):
    out = tmp_path_factory.mktemp("drafts")
    events: list[ProgressEvent] = []
    req = GenerationRequest(output_dir=out, reference=REF, scale="s", stands=2, ai_drafts=True)
    result = generate_dataspace(req, progress=events.append)
    return out, result, events


class TestRun:
    def test_progress_runs_through_the_prototype_steps_in_order(self, run) -> None:
        result, events, _ = run
        order = [s for s, _ in STEPS]
        seen = [e.step for e in events if e.state == STATE_RUNNING]
        assert seen == [s for s in order if s != "ai_drafts"]
        done = {e.step for e in events if e.state == STATE_DONE}
        assert done == set(order) - {"ai_drafts"}
        skipped = [e for e in events if e.state == STATE_SKIPPED]
        assert [e.step for e in skipped] == ["ai_drafts"] and "Schalter aus" in skipped[0].detail
        assert all(e.label for e in events) and all(e.elapsed_s >= 0 for e in events)
        stands_done = next(e for e in events if e.step == "stands" and e.state == STATE_DONE)
        assert "2 Stände" in stands_done.detail

    def test_result_numbers(self, run) -> None:
        result, _, lines = run
        assert result.portfolios == ["demo_portfolio"]
        assert result.issues > 0 and result.registers == 22
        assert result.stands == 2 and result.deltas == 1
        assert result.providers == 4            # slo, slo_csv, dora, quality
        assert result.ai_drafts == [] and result.elapsed_s > 0
        assert result.story is not None and result.story.template == TEMPLATE_STANDARD
        assert result.root.joinpath("portfolio.json").is_file()
        assert any("Szenario komplett" in li for li in lines)

    def test_invalid_request_writes_nothing(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            generate_dataspace(GenerationRequest(output_dir=tmp_path / "x", stands=99))
        assert not (tmp_path / "x").exists()

    def test_cancel_between_steps(self, tmp_path) -> None:
        seen: list[str] = []

        def cancel() -> bool:
            return "arts" in seen            # stop as soon as the ART step reported

        def progress(e: ProgressEvent) -> None:
            seen.append(e.step)

        req = GenerationRequest(output_dir=tmp_path / "c", reference=REF, scale="s", stands=2,
                                structure=structure_from_arts_spec("1"))
        with pytest.raises(GenerationCancelled, match="abgebrochen"):
            generate_dataspace(req, progress=progress, cancel=cancel)
        assert not (tmp_path / "c" / "snapshots" / "snapshot_now.json").exists()


class TestAiDrafts:
    def test_drafts_folder_separates_input_from_output(self, drafts) -> None:
        out, result, events = drafts
        folder = out / AI_DRAFTS_DIR
        assert result.ai_drafts == [folder]
        names = sorted(p.name for p in folder.iterdir())
        assert "einseiter.html" in names
        briefing = [n for n in names if n.startswith("einseiter.html.") and n.endswith(".md")]
        assert len(briefing) == 1                      # <page>.briefing.md (en) / .vortrag.md (de)
        assert [n for n in names if n.startswith("frage_") and n.endswith(".ask.md")] == [
            "frage_1.ask.md", "frage_2.ask.md", "frage_3.ask.md"]
        assert any(n.startswith("prompt_d3_question_") for n in names)
        assert PRACTICE_ANSWER in names and PRACTICE_README in names and "llm_audit.jsonl" in names
        done = next(e for e in events if e.step == "ai_drafts" and e.state == STATE_DONE)
        assert "1 Ordner" in done.detail

    def test_every_draft_carries_the_marker_and_is_not_approved(self, drafts) -> None:
        out, _, _ = drafts
        folder = out / AI_DRAFTS_DIR
        briefing = next(folder.glob("einseiter.html.*.md"))
        for path in (briefing, folder / "frage_1.ask.md", folder / "frage_2.ask.md"):
            text = path.read_text(encoding="utf-8")
            markers = read_markers(text)
            assert markers and markers[0].get("provider") == "mock"
            assert not any(m.get("approved") for m in markers)

    def test_practice_answer_is_rejected_by_llm_check(self, drafts, tmp_path) -> None:
        out, _, _ = drafts
        folder = out / AI_DRAFTS_DIR
        bundle_path = next(folder.glob("prompt_d3_question_*.md"))
        bundle = load_bundle(bundle_path)
        assert bundle.purpose == "d3_question"
        report = run_check((folder / PRACTICE_ANSWER).read_text(encoding="utf-8"), bundle_path,
                           out_path=tmp_path / "checked.md", log=lambda m: None)
        assert not report.passed
        assert any("4711" in v for v in report.number_violations)
        assert report.written is None
        readme = (folder / PRACTICE_README).read_text(encoding="utf-8")
        assert "python -m llm check" in readme and bundle_path.name in readme
