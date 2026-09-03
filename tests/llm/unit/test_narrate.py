# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   End-zu-End-Tests der Narration (D2 Teil 2) mit dem Mock-Provider:
#   narrate() verdrahtet Wächter + Kennzeichnung + Audit unumgehbar
#   (auch beim Wächter-Fehlschlag entsteht ein Nachweis), die llm-CLI
#   (providers/test) und die portfolio-CLI mit --narrate — ohne Flag
#   exakt heutiges Verhalten, mit Flag Abschnitt „Narration (Entwurf)",
#   separate <output>.narration.md und llm_audit.jsonl neben der Ausgabe.
# =============================================================================

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_MOCK, LlmResult
from llm.guard import NumbersGuardError
from llm.narrate import narrate
from portfolio.snapshot import Snapshot, save_snapshot

PREV_DAY = date(2026, 8, 16)
NOW_DAY = date(2026, 8, 30)


def _snapshot(as_of: date, completed: int) -> Snapshot:
    return Snapshot(
        name="Demo", kind="portfolio", as_of=as_of,
        created="2026-08-30T12:00:00", target_ct=90,
        total={"label": "Demo", "items": 100, "completed": completed,
               "open": 100 - completed, "median_ct": 8.4, "p85_ct": 18.0,
               "p95_ct": 30.0, "target_ct_pct": 95.0, "median_lt": 16.4,
               "p85_lt": 39.0},
        units=[], sources=[],
        governance={"risks": [], "dependencies": [], "nfr": [], "runway": [],
                    "capabilities": [], "decisions": []})


class _InventingProvider:
    """Test double that violates the numbers guard on purpose."""

    provider_id = "inventor"
    deployment_class = DEPLOYMENT_MOCK
    default_model = "inventor-1"

    def complete(self, system: str, prompt: str,
                 config: dict[str, Any]) -> LlmResult:
        return LlmResult(text="Wir lieferten 9999 Items.",
                         provider_id=self.provider_id,
                         model=self.default_model,
                         deployment_class=self.deployment_class)


class TestNarrate:
    def test_mock_end_to_end_with_banner_and_audit(self, tmp_path) -> None:
        audit = tmp_path / "llm_audit.jsonl"
        narration = narrate("# Briefing\n- Completed: 12 -> 34\n",
                            provider_id="mock", audit_path=audit)
        assert "ATTRAPPE" in narration.text
        assert "mock-1" in narration.banner
        assert "ungeprüft" in narration.banner
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["guard_passed"] is True
        assert record["purpose"] == "d2_narration"

    def test_language_reaches_provider_and_banner(self) -> None:
        narration = narrate("briefing", provider_id="mock", lang="en")
        assert "MOCK" in narration.text
        assert "unreviewed" in narration.banner

    def test_unknown_provider_lists_known_ones(self) -> None:
        with pytest.raises(RuntimeError, match="known: .*mock.*ollama"):
            narrate("briefing", provider_id="gpt")

    def test_guard_failure_discards_text_but_keeps_evidence(
            self, tmp_path) -> None:
        audit = tmp_path / "llm_audit.jsonl"
        fake = {"inventor": _InventingProvider()}
        with patch("llm.narrate.discover_providers", return_value=fake):
            with pytest.raises(NumbersGuardError, match="9999"):
                narrate("Completed: 12 -> 34", provider_id="inventor",
                        audit_path=audit)
        record = json.loads(audit.read_text(encoding="utf-8"))
        assert record["guard_passed"] is False
        assert record["provider"] == "inventor"
        assert "9999" not in audit.read_text(encoding="utf-8")


class TestLlmCli:
    def test_providers_lists_inventory(self, capsys) -> None:
        from llm.cli import main
        assert main(["providers"]) == 0
        out = capsys.readouterr().out
        assert "ollama: default=mistral-nemo (local)" in out
        assert "claude: default=claude-sonnet-5 (external_api)" in out
        assert "mock:" in out

    def test_test_command_with_mock(self, capsys) -> None:
        from llm.cli import main
        assert main(["test", "--llm", "mock"]) == 0
        out = capsys.readouterr().out
        assert "KI-formulierter Entwurf" in out
        assert "ATTRAPPE" in out

    def test_test_command_reports_provider_errors(self, capsys) -> None:
        from llm.cli import main
        assert main(["test", "--llm", "nope"]) == 1
        assert "Unknown llm provider" in capsys.readouterr().err


class TestPortfolioNarrateFlag:
    def _write_snaps(self, tmp_path):
        prev_p = tmp_path / "prev.json"
        now_p = tmp_path / "now.json"
        save_snapshot(prev_p, _snapshot(PREV_DAY, completed=60))
        save_snapshot(now_p, _snapshot(NOW_DAY, completed=75))
        return prev_p, now_p

    def test_without_flag_behaviour_is_unchanged(self, tmp_path) -> None:
        from portfolio.cli import run_delta_briefing
        prev_p, now_p = self._write_snaps(tmp_path)
        out = tmp_path / "delta.md"
        run_delta_briefing(prev_p, now_p, output=out, log=lambda m: None)
        assert "Narration" not in out.read_text(encoding="utf-8")
        assert not (tmp_path / "llm_audit.jsonl").exists()
        assert not out.with_suffix(".md.narration.md").exists()

    def test_narrate_markdown_adds_section_draft_and_audit(
            self, tmp_path) -> None:
        from portfolio.cli import run_delta_briefing
        prev_p, now_p = self._write_snaps(tmp_path)
        out = tmp_path / "delta.md"
        run_delta_briefing(prev_p, now_p, output=out, narrate_with="mock",
                           log=lambda m: None)
        text = out.read_text(encoding="utf-8")
        assert "## Narration (Entwurf)" in text
        assert "KI-formulierter Entwurf" in text
        assert "ATTRAPPE" in text
        draft = out.with_suffix(".md.narration.md")
        assert "ATTRAPPE" in draft.read_text(encoding="utf-8")
        record = json.loads(
            (tmp_path / "llm_audit.jsonl").read_text(encoding="utf-8"))
        assert record["provider"] == "mock"
        assert record["guard_passed"] is True

    def test_narrate_html_section_is_labeled(self, tmp_path) -> None:
        from portfolio.cli import run_delta_briefing
        prev_p, now_p = self._write_snaps(tmp_path)
        out = tmp_path / "delta.html"
        run_delta_briefing(prev_p, now_p, output=out, narrate_with="mock",
                           llm_lang="en", log=lambda m: None)
        html = out.read_text(encoding="utf-8")
        assert "<h2>Narration (Entwurf)</h2>" in html
        assert "AI-drafted" in html
        assert "MOCK" in html
        assert html.rstrip().endswith("</body></html>")
        assert out.with_suffix(".html.narration.md").exists()

    def test_cli_flags_parse_and_reach_narration(self, tmp_path,
                                                 monkeypatch) -> None:
        import sys

        from portfolio.cli import main
        prev_p, now_p = self._write_snaps(tmp_path)
        out = tmp_path / "cli.md"
        monkeypatch.setattr(sys, "argv", [
            "portfolio", "--delta", str(prev_p), str(now_p),
            "--output", str(out), "--narrate", "mock", "--llm-lang", "en"])
        main()
        assert "MOCK" in out.read_text(encoding="utf-8")

    def test_narration_input_is_exactly_the_delta_contract(
            self, tmp_path) -> None:
        # Aggregat-Leitplanke (b): das LLM sieht AUSSCHLIESSLICH das
        # Delta-Markdown — das enthaelt per Konstruktion Teams/Solutions,
        # nie Personen. Jede andere Eingabe waere ein Regressionsbruch.
        import llm.narrate as narrate_mod
        from portfolio.cli import run_delta_briefing
        from portfolio.delta import compute_delta, delta_to_markdown
        from portfolio.snapshot import load_snapshot

        prev_p, now_p = self._write_snaps(tmp_path)
        expected = delta_to_markdown(
            compute_delta(load_snapshot(prev_p), load_snapshot(now_p)))
        seen: list[str] = []
        original = narrate_mod.narrate

        def spy(source_text, **kwargs):
            seen.append(source_text)
            return original(source_text, **kwargs)

        with patch("llm.narrate.narrate", side_effect=spy):
            run_delta_briefing(prev_p, now_p, output=tmp_path / "d.md",
                               narrate_with="mock", log=lambda m: None)
        assert seen == [expected]


class TestGuiNarration:
    """Display-independent GUI building blocks (no tkinter needed)."""

    def _snaps(self, tmp_path):
        prev_p = tmp_path / "snapshot_prev.json"
        now_p = tmp_path / "snapshot_now.json"
        save_snapshot(prev_p, _snapshot(PREV_DAY, completed=60))
        save_snapshot(now_p, _snapshot(NOW_DAY, completed=75))
        return prev_p, now_p

    def test_provider_dropdown_lists_discovery(self) -> None:
        from portfolio.gui import _llm_provider_ids
        ids = _llm_provider_ids()
        assert {"ollama", "claude", "mock"} <= set(ids)

    def test_demo_dropdown_lists_discovery_too(self) -> None:
        from testdata_generator.gui import _llm_provider_ids
        assert {"ollama", "claude", "mock"} <= set(_llm_provider_ids())

    def test_portfolio_gui_helper_appends_labeled_section(
            self, tmp_path) -> None:
        from pathlib import Path

        from portfolio.gui import _build_delta_html_file
        prev_p, now_p = self._snaps(tmp_path)
        out = Path(_build_delta_html_file(prev_p, now_p,
                                          narrate_with="mock"))
        try:
            html = out.read_text(encoding="utf-8")
        finally:
            out.unlink(missing_ok=True)
        assert "<h2>Narration (Entwurf)</h2>" in html
        assert "ATTRAPPE" in html
        # Nachweis liegt bei den DATEN (neben dem Nachher-Snapshot),
        # nicht bei der Temp-Datei.
        assert (tmp_path / "llm_audit.jsonl").exists()

    def test_testdata_demo_helper_takes_provider_id(self, tmp_path) -> None:
        from pathlib import Path

        from testdata_generator.gui import _build_delta_html_file
        prev_p, now_p = self._snaps(tmp_path)
        out = Path(_build_delta_html_file(prev_p, now_p,
                                          log=lambda m: None,
                                          narrate_with="mock", lang="en"))
        try:
            html = out.read_text(encoding="utf-8")
        finally:
            out.unlink(missing_ok=True)
        assert "MOCK" in html
        assert "AI-drafted" in html
        assert (tmp_path / "llm_audit.jsonl").exists()
        # Ohne Provider bleibt die Demo deterministisch.
        out2 = Path(_build_delta_html_file(prev_p, now_p,
                                           log=lambda m: None))
        try:
            assert "Narration" not in out2.read_text(encoding="utf-8")
        finally:
            out2.unlink(missing_ok=True)

    def test_helpers_stay_deterministic_without_narration(
            self, tmp_path) -> None:
        from pathlib import Path

        from portfolio.gui import _build_delta_html_file
        prev_p, now_p = self._snaps(tmp_path)
        out = Path(_build_delta_html_file(prev_p, now_p))
        try:
            html = out.read_text(encoding="utf-8")
        finally:
            out.unlink(missing_ok=True)
        assert "Narration" not in html
        assert not (tmp_path / "llm_audit.jsonl").exists()
