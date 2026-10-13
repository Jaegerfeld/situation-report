# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Prompt-Exports: Bündel-Format, Provider "export" (Datei neben
#   der Ausgabe, Platzhalter, Klasse export), Einbettung in narrate (Zweck
#   und Ordner wandern in die Config, Zahlen-Wächter übersprungen, Banner
#   „kein Modell", Nachweis mit Provider export), Erreichbarkeit über jede
#   KI-Stelle (D1, D5 ohne Fragen-Wächter, P3), Zwischenablage abschaltbar.
# =============================================================================

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from llm.base import DEPLOYMENT_EXPORT, discover_providers
from llm.export import BUNDLE_SCHEMA, build_bundle, bundle_filename, write_bundle
from llm.guard import ai_banner_text
from llm.narrate import narrate


@pytest.fixture(autouse=True)
def no_clipboard(monkeypatch):
    """Tests never touch the real clipboard."""
    import llm.providers.export as export_provider
    monkeypatch.setattr(export_provider, "copy_to_clipboard", lambda text: False)


class TestBundle:
    def test_contains_instructions_system_and_input(self) -> None:
        text = build_bundle("SYSTEM RULES", "# Contract\nitems 5", "d2_narration", lang="de",
                            stamp=datetime(2026, 10, 13, 12, 0))
        assert text.startswith("# Prompt-Export — d2_narration — 2026-10-13 12:00")
        assert BUNDLE_SCHEMA in text and "Kein Modell wurde aufgerufen" in text
        assert "## Systemprompt" in text and "SYSTEM RULES" in text
        assert "## Eingabe (Contract)" in text and "items 5" in text
        assert text.index("SYSTEM RULES") < text.index("items 5")

    def test_english_variant_and_filename(self) -> None:
        text = build_bundle("S", "I", "p3_reading", lang="en")
        assert "## System prompt" in text and "No model was called" in text
        assert bundle_filename("d1_exec_summary", datetime(2026, 10, 13, 9, 5, 7)) == \
            "prompt_d1_exec_summary_20261013-090507.md"
        assert bundle_filename("a b/c").startswith("prompt_a_b_c_")

    def test_write_bundle_creates_the_folder(self, tmp_path) -> None:
        path = write_bundle(tmp_path / "out", "x", "hello")
        assert path.read_text(encoding="utf-8") == "hello" and path.parent.name == "out"


class TestProvider:
    def test_discovered_like_every_provider(self) -> None:
        provider = discover_providers()["export"]
        assert provider.deployment_class == DEPLOYMENT_EXPORT == "export"
        assert provider.default_model == "none"

    def test_complete_writes_the_bundle_and_returns_the_placeholder(self, tmp_path) -> None:
        provider = discover_providers()["export"]
        result = provider.complete("SYS", "INPUT 42", {"lang": "en", "purpose": "d2_narration",
                                                       "export_dir": str(tmp_path)})
        files = list(tmp_path.glob("prompt_d2_narration_*.md"))
        assert len(files) == 1 and "INPUT 42" in files[0].read_text(encoding="utf-8")
        assert result.deployment_class == DEPLOYMENT_EXPORT and result.model == "none"
        assert result.endpoint == str(files[0])
        assert result.text.startswith("[NO MODEL CALLED]") and "clipboard not available" in result.text

    def test_german_placeholder_and_clipboard_note(self, tmp_path) -> None:
        import llm.providers.export as export_provider
        with patch.object(export_provider, "copy_to_clipboard", lambda text: True):
            result = export_provider.PROVIDER.complete(
                "S", "I", {"lang": "de", "export_dir": str(tmp_path)})
        assert result.text.startswith("[KEIN MODELL AUFGERUFEN]")
        assert "auch in der Zwischenablage" in result.text

    def test_clipboard_can_be_switched_off(self, tmp_path) -> None:
        import llm.providers.export as export_provider
        calls: list[str] = []
        with patch.object(export_provider, "copy_to_clipboard",
                          lambda text: calls.append(text) or True):
            export_provider.PROVIDER.complete("S", "I", {"export_dir": str(tmp_path),
                                                         "clipboard": False})
        assert calls == []


class TestNarrateIntegration:
    def test_purpose_and_folder_reach_the_provider_guard_skipped_banner_audit(self, tmp_path) -> None:
        audit = tmp_path / "out" / "llm_audit.jsonl"
        narration = narrate("# Contract\nitems 5 of 9", provider_id="export", lang="de",
                            audit_path=audit, purpose="d1_exec_summary")
        bundle = list((tmp_path / "out").glob("prompt_d1_exec_summary_*.md"))
        assert len(bundle) == 1                               # next to the audit file
        assert "items 5 of 9" in bundle[0].read_text(encoding="utf-8")
        # the placeholder names a path full of digits - the numbers guard must not judge it
        assert narration.text.startswith("[KEIN MODELL AUFGERUFEN]")
        assert narration.banner.startswith("Kein Modell aufgerufen — Prompt exportiert (")
        record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
        assert record["provider"] == "export" and record["model"] == "none"
        assert record["deployment_class"] == "export" and record["guard_passed"] is True

    @pytest.mark.parametrize("lang,word", [("en", "No model called"), ("ro", "Niciun model"),
                                           ("pt", "Nenhum modelo"), ("fr", "Aucun modèle")])
    def test_export_banner_in_every_house_language(self, lang, word) -> None:
        from llm.base import LlmResult
        result = LlmResult(text="x", provider_id="export", model="none",
                           deployment_class=DEPLOYMENT_EXPORT, endpoint="C:/x/prompt.md")
        assert word in ai_banner_text(result, lang) and "C:/x/prompt.md" in ai_banner_text(result, lang)

    def test_without_audit_path_the_bundle_lands_in_cwd(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        narrate("c", provider_id="export", purpose="d2_narration")
        assert list(tmp_path.glob("prompt_d2_narration_*.md"))


class TestReachableFromEveryAiStep:
    def test_exec_summary_d1(self, tmp_path) -> None:
        from datetime import date

        from portfolio.exec_summary import attach_exec_summary
        from portfolio.snapshot import Snapshot
        snap = Snapshot(name="D", kind="solution", as_of=date(2026, 10, 13), created="x",
                        target_ct=90, total={"label": "D", "items": 3, "completed": 2, "open": 1,
                                             "median_ct": 1.0, "p85_ct": 1.0, "p95_ct": 1.0,
                                             "target_ct_pct": 100.0, "median_lt": 1.0})
        with patch("portfolio.exec_summary.build_snapshot", return_value=snap):
            page, narration = attach_exec_summary(
                "<h2>Management Summary</h2><table></table>", config=object(),
                provider_id="export", lang="de", audit_path=tmp_path / "llm_audit.jsonl",
                log=lambda m: None)
        assert "Kein Modell aufgerufen" in page and list(tmp_path.glob("prompt_d1_exec_summary_*.md"))

    def test_red_team_d5_skips_the_questions_guard(self, tmp_path) -> None:
        from portfolio.decision_config import LogEntry
        from portfolio.red_team import run_red_team
        entry = LogEntry(entry_id="DR-1", kind="decision", title="Use stage map", status="accepted")
        with patch("portfolio.aggregator._collect_decisions", return_value=[("S", entry)]):
            run_red_team(object(), tmp_path / "questions.md", provider_id="export", lang="en",
                         log=lambda m: None)
        assert list(tmp_path.glob("prompt_d5_red_team_*.md"))
        assert "[NO MODEL CALLED]" in (tmp_path / "questions.md").read_text(encoding="utf-8")

    def test_harmonisation_reading_p3(self, tmp_path) -> None:
        from harmonisation.examples import write_example
        from harmonisation.model import load_workspace
        from harmonisation.reading import attach_reading, matrix_to_markdown
        write_example(tmp_path)
        ws = load_workspace(tmp_path)
        page, _ = attach_reading("<table></table>", matrix_to_markdown(ws), "export", lang="en",
                                 audit_path=tmp_path / "llm_audit.jsonl", log=lambda m: None)
        assert "No model called" in page and list(tmp_path.glob("prompt_p3_reading_*.md"))
