# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.10.2026
# Geändert:       17.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des maschinenlesbaren KI-Markers (R3, Leitplanke a): Markerfelder
#   wie der Nachweis, Markdown-Kopf lesbar, HTML-<section> mit data-
#   Attributen und Zähler im <head>, die alten HTML-Funktionen liefern
#   denselben Block, Entwurfsdateien aller Zwecke tragen den Marker;
#   `llm approve`: redigierter Entwurf -> geprüft, Banner ersetzt, Nachweis;
#   unredigiert -> Rückgabe 3, mit --as-is durch; doppelt -> Fehler.
# =============================================================================

from __future__ import annotations

import json
from datetime import date

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.cli import main as llm_main
from llm.guard import (
    MARKER_SCHEMA,
    add_ai_meta,
    ai_html_section,
    ai_markdown_head,
    ai_marker,
    draft_markdown,
    read_markers,
)
from llm.narrate import Narration
from llm.prompts import PROMPT_VERSION


def _narration(text: str = "Alles im Rahmen.") -> Narration:
    res = LlmResult(text=text, provider_id="mock", model="mock-1", deployment_class=DEPLOYMENT_MOCK)
    return Narration(text=text, banner="KI-formulierter Entwurf (mock-1 @ mock, Prompt v2) — ungeprüft.", result=res)


class TestMarker:
    def test_fields_match_the_evidence(self) -> None:
        n = _narration()
        m = ai_marker(n.result, "d1_exec_summary", "de", generated="2026-10-17T10:00:00")
        assert m["schema"] == MARKER_SCHEMA and m["ai_draft"] is True and m["reviewed"] is False
        assert m["purpose"] == "d1_exec_summary" and m["provider"] == "mock" and m["model"] == "mock-1"
        assert m["deployment_class"] == "mock" and m["prompt_version"] == PROMPT_VERSION
        assert len(m["output_sha256"]) == 64 and m["generated"] == "2026-10-17T10:00:00" and m["lang"] == "de"

    def test_markdown_head_and_draft_file_are_readable(self) -> None:
        n = _narration()
        head = ai_markdown_head(n.result, n.banner, "d2_narration", "de")
        assert head.startswith("<!-- sr-ai-draft {") and head.endswith(f"\n> {n.banner}")
        md = draft_markdown(n, "d2_narration")
        markers = read_markers(md)
        assert len(markers) == 1 and markers[0]["purpose"] == "d2_narration"
        assert md.endswith(f"> {n.banner}\n\nAlles im Rahmen.\n")
        assert read_markers("no marker here") == [] and read_markers("<!-- sr-ai-draft {broken -->") == []

    def test_html_section_and_head_counter(self) -> None:
        n = _narration("<b>x</b> & y")
        sec = ai_html_section(n, "d8_conference", "Einleitung", heading_style="font-size:1rem")
        assert sec.startswith('<section class="sr-ai-draft" data-ai-draft="true"')
        for attr in ('data-ai-purpose="d8_conference"', 'data-ai-model="mock-1"', 'data-ai-deployment="mock"',
                     f'data-ai-prompt="{PROMPT_VERSION}"', 'data-ai-reviewed="false"', "data-ai-sha256="):
            assert attr in sec
        assert "<h2 style='font-size:1rem'>Einleitung</h2>" in sec and "&lt;b&gt;x&lt;/b&gt; &amp; y" in sec
        page = add_ai_meta(f"<html><head><title>t</title></head><body>{sec}{sec}</body></html>")
        assert page.count('<meta name="sr-ai-drafts" content="2">') == 1 and page.index("<meta") < page.index("<title>")
        assert add_ai_meta(add_ai_meta(page)).count("sr-ai-drafts") == 1          # idempotent
        assert "sr-ai-drafts" not in add_ai_meta("<html><head></head><body></body></html>")

    def test_module_sections_share_the_block(self) -> None:
        from harmonisation.reading import reading_html_section
        from portfolio.cli import narration_html_section
        from portfolio.conference_draft import draft_html_section
        n = _narration()
        for html in (narration_html_section(n, "T", purpose="d1_exec_summary"),
                     draft_html_section(n, "T"), reading_html_section(n, "T")):
            assert 'class="sr-ai-draft"' in html and "🤖" in html and "<h2" in html


class TestApprove:
    def _draft(self, tmp_path, text: str = "Alles im Rahmen.", edited: bool = True):
        n = _narration(text)
        path = tmp_path / "report.html.exec_summary.md"
        md = draft_markdown(n, "d1_exec_summary", "de")
        if edited:
            md = md.replace(text, text + " Redigiert durch den Stab.")
        path.write_text(md, encoding="utf-8")
        return path

    def test_edited_draft_is_approved_with_evidence(self, tmp_path, capsys) -> None:
        path = self._draft(tmp_path)
        assert llm_main(["approve", str(path), "--by", "Stab Alpha", "--note", "VSC 42"]) == 0
        out = capsys.readouterr().out
        assert "approved: report.html.exec_summary.md by Stab Alpha" in out and "(edited)" in out
        text = path.read_text(encoding="utf-8")
        m = read_markers(text)[0]
        assert m["reviewed"] is True and m["reviewed_by"] == "Stab Alpha" and m["edited"] is True
        assert m["reviewed_on"] == date.today().isoformat() and m["note"] == "VSC 42"
        assert "> Freigegeben durch Stab Alpha am " in text and "ungeprüft" not in text
        assert "Redigiert durch den Stab." in text
        rec = json.loads((tmp_path / "llm_audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert rec["purpose"] == "approval" and rec["draft_purpose"] == "d1_exec_summary"
        assert rec["reviewed_by"] == "Stab Alpha" and rec["edited"] is True and len(rec["approved_sha256"]) == 64
        # a second approval is refused
        assert llm_main(["approve", str(path), "--by", "Stab Alpha"]) == 1
        assert "already approved" in capsys.readouterr().err

    def test_unedited_needs_as_is(self, tmp_path, capsys) -> None:
        path = self._draft(tmp_path, edited=False)
        assert llm_main(["approve", str(path), "--by", "Stab Beta"]) == 3
        assert "unchanged" in capsys.readouterr().out and read_markers(path.read_text(encoding="utf-8"))[0]["reviewed"] is False
        assert llm_main(["approve", str(path), "--by", "Stab Beta", "--as-is"]) == 0
        m = read_markers(path.read_text(encoding="utf-8"))[0]
        assert m["reviewed"] is True and m["edited"] is False
        assert "(as is)" in capsys.readouterr().out

    def test_show_missing_marker_and_missing_team(self, tmp_path, capsys) -> None:
        path = self._draft(tmp_path)
        assert llm_main(["approve", str(path), "--show"]) == 0
        assert '"purpose": "d1_exec_summary"' in capsys.readouterr().out
        assert llm_main(["approve", str(path)]) == 1 and "--by" in capsys.readouterr().err
        plain = tmp_path / "plain.md"
        plain.write_text("> some banner\n\ntext\n", encoding="utf-8")
        assert llm_main(["approve", str(plain), "--by", "Team"]) == 1
        assert "No AI-draft marker" in capsys.readouterr().err

    def test_english_draft_gets_english_approval_line(self, tmp_path) -> None:
        n = _narration("Within limits.")
        path = tmp_path / "d.md"
        path.write_text(draft_markdown(n, "d2_narration", "en").replace("Within limits.", "Within limits, edited."),
                        encoding="utf-8")
        assert llm_main(["approve", str(path), "--by", "Staff"]) == 0
        assert "> Approved by Staff on " in path.read_text(encoding="utf-8")


class TestDraftsCarryMarkers:
    def test_ask_briefing_alarm_and_check_outputs(self, tmp_path) -> None:
        from llm.check import Bundle, CheckReport, checked_text
        bundle = Bundle(purpose="d3_question", lang="de", system="s", contract="# C\n- [S1/a] x = 1\n",
                        path=tmp_path / "prompt_d3_question_x.md", checksum="0" * 64)
        text = checked_text(CheckReport(bundle=bundle, answer="Dazu liegt im Lagebild keine Angabe vor.",
                                        model="gpt-x"))
        m = read_markers(text)
        assert m and m[0]["purpose"] == "d3_question" and m[0]["deployment_class"] == "external_answer"

    @pytest.mark.parametrize("purpose", ["d4_anomaly", "m6_briefing"])
    def test_marker_json_is_sorted_and_complete(self, purpose) -> None:
        n = _narration()
        s = json.dumps(ai_marker(n.result, purpose, "de"), ensure_ascii=False, sort_keys=True)
        assert read_markers(f"<!-- sr-ai-draft {s} -->")[0]["purpose"] == purpose
