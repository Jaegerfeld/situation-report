# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Rückwegs „llm check": Bündel parsen (Contract wörtlich, Prüfsumme,
#   fremde Fences überleben), Bündel finden, Wächter (Zahlen immer, Fragen bei
#   d5), Bestanden → gekennzeichnete Datei + Nachweis mit demselben Eingabe-Hash
#   wie der Export-Eintrag, Abgelehnt → nichts geschrieben + guard_passed=false,
#   Banner in fünf Sprachen, CLI-Rückgabewerte, Zwischenablage, GUI-Texte und
#   -Handler, Fragen-Wächter des Red Teams nutzt den gemeinsamen Wächter.
# =============================================================================

from __future__ import annotations

import json
from datetime import datetime

import pytest

from llm.audit import AUDIT_FILENAME
from llm.base import DEPLOYMENT_EXTERNAL_ANSWER, LlmResult
from llm.check import (
    MODEL_UNKNOWN,
    PROVIDER_EXTERNAL,
    Bundle,
    check_answer,
    checked_text,
    find_bundle,
    load_bundle,
    parse_bundle,
    run_check,
    sha256_text,
)
from llm.cli import main
from llm.export import build_bundle, write_bundle
from llm.guard import ai_banner_text, question_violations
from llm.narrate import narrate

CONTRACT = "# Delta\n- Completed: 12 -> 34\n- median CT 39.0 d\n\n```json\n{\"x\": 7}\n```\n"


@pytest.fixture(autouse=True)
def no_clipboard(monkeypatch):
    import llm.providers.export as export_provider
    monkeypatch.setattr(export_provider, "copy_to_clipboard", lambda text: False)


def _bundle(tmp_path, purpose="d2_narration", lang="de", contract=CONTRACT):
    text = build_bundle("SYSTEM", contract, purpose, lang=lang, stamp=datetime(2026, 10, 14, 9, 0))
    return write_bundle(tmp_path, purpose, text, stamp=datetime(2026, 10, 14, 9, 0))


class TestBundleParsing:
    def test_roundtrip_keeps_the_contract_verbatim_and_checksum_matches(self, tmp_path) -> None:
        path = _bundle(tmp_path)
        b = load_bundle(path)
        assert b.purpose == "d2_narration" and b.lang == "de" and b.stamp == "2026-10-14 09:00"
        assert b.system == "SYSTEM" and b.contract == CONTRACT        # inner fences survive
        assert b.checksum == sha256_text(CONTRACT) and b.checksum_ok is True

    def test_english_bundle(self, tmp_path) -> None:
        b = load_bundle(_bundle(tmp_path, purpose="d5_red_team", lang="en", contract="- DR-1: x\n"))
        assert b.lang == "en" and b.purpose == "d5_red_team" and b.contract == "- DR-1: x\n"

    def test_edited_bundle_is_detected_and_old_bundle_has_no_checksum(self) -> None:
        text = build_bundle("S", "items 5\n", "p3_reading").replace("items 5", "items 6")
        assert parse_bundle(text).checksum_ok is False
        legacy = "\n".join(line for line in build_bundle("S", "c", "x").splitlines()
                           if "SHA-256" not in line)
        b = parse_bundle(legacy)
        assert b.checksum == "" and b.checksum_ok is None and b.contract == "c"

    def test_rejects_foreign_text(self) -> None:
        with pytest.raises(ValueError, match="Not a prompt-export bundle"):
            parse_bundle("# Something else\n\n```markdown\nx\n```\n")
        with pytest.raises(ValueError, match="lacks"):
            parse_bundle("# Prompt-Export — p — 2026-10-14 09:00\n\nno sections\n")

    def test_find_newest_bundle_optionally_by_purpose(self, tmp_path) -> None:
        a = write_bundle(tmp_path, "d1_exec_summary", "a", datetime(2026, 10, 14, 8, 0))
        b = write_bundle(tmp_path, "d2_narration", "b", datetime(2026, 10, 14, 9, 0))
        import os
        os.utime(a, (1_800_000_000, 1_800_000_000)); os.utime(b, (1_800_000_100, 1_800_000_100))
        assert find_bundle(tmp_path) == b
        assert find_bundle(tmp_path, "d1_exec_summary") == a
        assert find_bundle(tmp_path, "nope") is None and find_bundle(tmp_path / "empty") is None


class TestGuards:
    def test_numbers_guard_against_the_contract(self) -> None:
        b = Bundle("d2_narration", "de", "S", CONTRACT)
        ok = check_answer("Von 12 auf 34 abgeschlossen; Median 39 Tage.", b)
        assert ok.passed and ok.violations == []
        bad = check_answer("Von 12 auf 35 abgeschlossen, also 2,9 % mehr.", b)
        assert not bad.passed and bad.number_violations == ["29", "35"]
        assert bad.violations[0].startswith("Zahl nicht im Contract: 29")

    def test_questions_guard_only_for_red_team(self) -> None:
        answer = "## DR-1\n- Was passiert, wenn nicht?\n- Das ist riskant.\n"
        assert check_answer(answer, Bundle("d5_red_team", "en", "S", "- DR-1: x")).question_violations \
            == ["- Das ist riskant."]
        assert check_answer(answer, Bundle("d2_narration", "en", "S", "- DR-1: x")).passed
        assert question_violations("nur Prosa") == ["<keine Fragen enthalten>"]
        assert question_violations("- a?\n- b?") == []

    def test_empty_answer_is_rejected(self) -> None:
        assert check_answer("   \n", Bundle("x", "de", "S", "c")).violations == \
            ["Zahl nicht im Contract: <leere Antwort>"]

    def test_red_team_module_uses_the_shared_guard(self) -> None:
        from portfolio.red_team import QuestionsOnlyError, enforce_questions
        with pytest.raises(QuestionsOnlyError):
            enforce_questions("- Statement.")
        enforce_questions("- Frage?")


class TestBannerAndText:
    @pytest.mark.parametrize("lang,word", [("de", "Extern erzeugter"), ("en", "Externally produced"),
                                           ("ro", "produsă extern"), ("pt", "produzido externamente"),
                                           ("fr", "produit à l'extérieur")])
    def test_banner_in_every_language_names_the_model(self, lang, word) -> None:
        result = LlmResult(text="x", provider_id=PROVIDER_EXTERNAL, model="gpt-x",
                           deployment_class=DEPLOYMENT_EXTERNAL_ANSWER)
        banner = ai_banner_text(result, lang)
        assert word in banner and "gpt-x" in banner

    def test_checked_text_is_banner_plus_answer(self) -> None:
        report = check_answer("Antwort 12.", Bundle("d2_narration", "de", "S", "12"), model="m1")
        text = checked_text(report)
        assert text.startswith("<!-- sr-ai-draft {") and "\n> Extern erzeugter KI-Entwurf (Modell laut Bediener: m1" in text
        assert text.endswith("\n\nAntwort 12.\n")


class TestRunCheck:
    def test_pass_writes_draft_and_links_the_audit_to_the_export(self, tmp_path) -> None:
        out = tmp_path / "out"
        narrate(CONTRACT, provider_id="export", lang="de", audit_path=out / AUDIT_FILENAME,
                purpose="d2_narration")
        bundle = find_bundle(out)
        assert bundle is not None
        report = run_check("Abgeschlossen 12 -> 34, Median 39 Tage.", bundle, model="llama-x",
                           log=lambda m: None)
        assert report.passed and report.written == bundle.with_suffix(".checked.md")
        assert "\n> Extern erzeugter KI-Entwurf" in report.written.read_text(encoding="utf-8")
        records = [json.loads(line) for line in (out / AUDIT_FILENAME).read_text(encoding="utf-8").splitlines()]
        export_rec, check_rec = records[-2], records[-1]
        assert export_rec["provider"] == "export" and check_rec["provider"] == PROVIDER_EXTERNAL
        assert check_rec["input_sha256"] == export_rec["input_sha256"]      # the link
        assert check_rec["deployment_class"] == DEPLOYMENT_EXTERNAL_ANSWER
        assert check_rec["model"] == "llama-x" and check_rec["guard_passed"] is True
        assert check_rec["purpose"] == "d2_narration"

    def test_reject_writes_nothing_but_records(self, tmp_path) -> None:
        bundle = _bundle(tmp_path)
        logged: list[str] = []
        report = run_check("Von 12 auf 99.", bundle, out_path=tmp_path / "draft.md", log=logged.append)
        assert not report.passed and report.written is None
        assert not (tmp_path / "draft.md").exists()
        assert any(line.startswith("REJECTED (d2_narration): 1 violation") for line in logged)
        rec = json.loads((tmp_path / AUDIT_FILENAME).read_text(encoding="utf-8").splitlines()[-1])
        assert rec["guard_passed"] is False and rec["model"] == MODEL_UNKNOWN

    def test_edited_bundle_is_warned_about(self, tmp_path) -> None:
        bundle = _bundle(tmp_path)
        bundle.write_text(bundle.read_text(encoding="utf-8").replace("12 -> 34", "12 -> 44"),
                          encoding="utf-8")
        logged: list[str] = []
        run_check("Von 12 auf 44.", bundle, out_path=tmp_path / "d.md", log=logged.append)
        assert any("does not match its checksum" in line for line in logged)


class TestCli:
    def test_file_pass_default_output_and_exit_codes(self, tmp_path, capsys) -> None:
        _bundle(tmp_path)
        answer = tmp_path / "antwort.md"
        answer.write_text("Abgeschlossen 12 -> 34.", encoding="utf-8")
        assert main(["check", str(answer), "--model", "x"]) == 0
        assert (tmp_path / "antwort.md.checked.md").exists()
        answer.write_text("Abgeschlossen 12 -> 77.", encoding="utf-8")
        assert main(["check", str(answer)]) == 2
        assert "REJECTED" in capsys.readouterr().out

    def test_missing_bundle_and_missing_answer(self, tmp_path, capsys) -> None:
        answer = tmp_path / "a.md"
        answer.write_text("x", encoding="utf-8")
        assert main(["check", str(answer)]) == 1
        assert "no exported prompt bundle" in capsys.readouterr().err
        assert main(["check"]) == 1
        assert main(["check", str(tmp_path / "missing.md"), "--bundle", str(_bundle(tmp_path))]) == 1

    def test_clipboard_path(self, tmp_path, monkeypatch) -> None:
        bundle = _bundle(tmp_path)
        import llm.check as check_mod
        monkeypatch.setattr(check_mod, "read_clipboard", lambda: "Median 39 Tage, 12 -> 34.")
        assert main(["check", "--clipboard", "--bundle", str(bundle), "--lang", "en"]) == 0
        text = bundle.with_suffix(".checked.md").read_text(encoding="utf-8")
        assert "\n> Externally produced AI draft" in text
        monkeypatch.setattr(check_mod, "read_clipboard", lambda: "")
        assert main(["check", "--clipboard", "--bundle", str(bundle)]) == 1


class TestGuiWiring:
    def test_texts_in_every_language_and_handler(self) -> None:
        from portfolio.gui import _T, SolutionManagerApp
        for lang in ("de", "en", "ro", "pt", "fr"):
            for key in ("btn_check_answer", "dlg_open_answer", "dlg_open_bundle", "dlg_model_title",
                        "dlg_model_prompt", "msg_check_ok", "msg_check_failed", "msg_check_error"):
                assert key in _T[lang], (lang, key)
        assert callable(SolutionManagerApp._check_answer)
