# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für das Portfolio-CLI (portfolio/cli.py): Orchestrierung in
#   run_solution_report (Modus-Weiche, Terminologie-Override, HTML-/PDF-Pfade,
#   Browser-Öffnung) und argparse-Verdrahtung in main() inklusive Fehlerpfad.
#   Renderer und Config-Loader sind gemockt — geprüft wird die CLI-Logik,
#   nicht die Aggregation.
# =============================================================================

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import pytest

import portfolio.cli as cli
from build_reports.metrics.flow_time import CT_METHOD_A, CT_METHOD_B
from build_reports.terminology import GLOBAL, SAFE
from portfolio.solution_config import MODE_COMPARISON, MODE_POOLED


@dataclass
class _FakeConfig:
    """Minimal stand-in for a parsed solution config."""

    name: str = "Payments Solution"
    kind: str = "solution"
    framework: str = "SAFe"
    terminology: str = SAFE
    members: list = field(default_factory=lambda: [object(), object()])


class _Recorder:
    """Callable that records every invocation and returns a fixed value."""

    def __init__(self, result=""):
        self.calls: list[dict] = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return self.result


@pytest.fixture
def fake_config(monkeypatch):
    """Patch the config loader to return a fixed fake config."""
    config = _FakeConfig()
    monkeypatch.setattr(cli, "load_solution_config", lambda path: config)
    return config


@pytest.fixture
def renderers(monkeypatch):
    """Patch all three renderers; pooled/comparison return distinct HTML."""
    pooled = _Recorder(result="<html>pooled</html>")
    comparison = _Recorder(result="<html>comparison</html>")
    pdf = _Recorder(result=None)
    monkeypatch.setattr(cli, "render_pooled_html", pooled)
    monkeypatch.setattr(cli, "render_comparison_html", comparison)
    monkeypatch.setattr(cli, "render_pdf", pdf)
    return {"pooled": pooled, "comparison": comparison, "pdf": pdf}


class TestRunSolutionReport:
    def test_pooled_default_uses_pooled_renderer(self, fake_config, renderers, tmp_path):
        html = cli.run_solution_report(tmp_path / "cfg.json", log=lambda m: None)
        assert html == "<html>pooled</html>"
        assert len(renderers["pooled"].calls) == 1
        assert renderers["comparison"].calls == []
        assert renderers["pdf"].calls == []

    def test_comparison_mode_uses_comparison_renderer(self, fake_config, renderers, tmp_path):
        html = cli.run_solution_report(
            tmp_path / "cfg.json", mode=MODE_COMPARISON, log=lambda m: None)
        assert html == "<html>comparison</html>"
        assert len(renderers["comparison"].calls) == 1
        assert renderers["pooled"].calls == []

    def test_html_written_to_output_path_with_parents(self, fake_config, renderers, tmp_path):
        out = tmp_path / "nested" / "dir" / "report.html"
        cli.run_solution_report(tmp_path / "cfg.json", output_html=out, log=lambda m: None)
        assert out.read_text(encoding="utf-8") == "<html>pooled</html>"

    def test_empty_html_writes_no_file(self, fake_config, renderers, tmp_path):
        renderers["pooled"].result = ""
        out = tmp_path / "report.html"
        html = cli.run_solution_report(
            tmp_path / "cfg.json", output_html=out, log=lambda m: None)
        assert html == ""
        assert not out.exists()

    def test_pdf_only_calls_pdf_renderer_and_skips_html(self, fake_config, renderers, tmp_path):
        html = cli.run_solution_report(
            tmp_path / "cfg.json", output_pdf=tmp_path / "r.pdf", log=lambda m: None)
        assert html == ""
        assert len(renderers["pdf"].calls) == 1
        assert renderers["pooled"].calls == []

    def test_pdf_and_html_together(self, fake_config, renderers, tmp_path):
        out = tmp_path / "report.html"
        html = cli.run_solution_report(
            tmp_path / "cfg.json", output_html=out,
            output_pdf=tmp_path / "r.pdf", log=lambda m: None)
        assert html == "<html>pooled</html>"
        assert len(renderers["pdf"].calls) == 1
        assert out.exists()

    def test_terminology_defaults_to_config_value(self, fake_config, renderers, tmp_path):
        fake_config.terminology = GLOBAL
        cli.run_solution_report(tmp_path / "cfg.json", log=lambda m: None)
        assert renderers["pooled"].calls[0]["kwargs"]["terminology"] == GLOBAL

    def test_terminology_argument_overrides_config(self, fake_config, renderers, tmp_path):
        fake_config.terminology = GLOBAL
        cli.run_solution_report(
            tmp_path / "cfg.json", terminology=SAFE, log=lambda m: None)
        assert renderers["pooled"].calls[0]["kwargs"]["terminology"] == SAFE

    def test_browser_opened_only_when_html_written(self, fake_config, renderers,
                                                   tmp_path, monkeypatch):
        opened = _Recorder()
        monkeypatch.setattr(cli.webbrowser, "open", opened)
        out = tmp_path / "report.html"
        cli.run_solution_report(
            tmp_path / "cfg.json", output_html=out, open_browser=True, log=lambda m: None)
        assert len(opened.calls) == 1
        assert opened.calls[0]["args"][0].startswith("file://")

    def test_browser_not_opened_without_output(self, fake_config, renderers,
                                               tmp_path, monkeypatch):
        opened = _Recorder()
        monkeypatch.setattr(cli.webbrowser, "open", opened)
        cli.run_solution_report(
            tmp_path / "cfg.json", open_browser=True, log=lambda m: None)
        assert opened.calls == []

    def test_log_reports_solution_and_mode(self, fake_config, renderers, tmp_path):
        lines: list[str] = []
        cli.run_solution_report(tmp_path / "cfg.json", log=lines.append)
        assert any("Payments Solution" in line and MODE_POOLED in line for line in lines)


class TestMain:
    def _run(self, monkeypatch, argv: list[str], result="<html>x</html>"):
        recorder = _Recorder(result=result)
        monkeypatch.setattr(cli, "run_solution_report", recorder)
        monkeypatch.setattr(sys, "argv", ["portfolio", *argv])
        cli.main()
        return recorder

    def test_minimal_invocation_uses_defaults(self, monkeypatch, capsys, tmp_path):
        cfg = tmp_path / "cfg.json"
        rec = self._run(monkeypatch, [str(cfg)])
        kw = rec.calls[0]["kwargs"]
        assert kw["config_path"] == cfg
        assert kw["mode"] == MODE_POOLED
        assert kw["ct_method"] == CT_METHOD_A
        assert kw["target_ct"] == 90
        assert kw["output_html"] is None and kw["output_pdf"] is None
        assert "nothing was written" in capsys.readouterr().out

    def test_arguments_are_passed_through(self, monkeypatch, tmp_path):
        cfg = tmp_path / "cfg.json"
        out = tmp_path / "r.html"
        rec = self._run(monkeypatch, [
            str(cfg), "--output", str(out), "--mode", MODE_COMPARISON,
            "--metrics", "flow_velocity", "flow_time",
            "--terminology", GLOBAL, "--ct-method", CT_METHOD_B,
            "--target-ct", "45", "--browser",
        ])
        kw = rec.calls[0]["kwargs"]
        assert kw["output_html"] == out
        assert kw["mode"] == MODE_COMPARISON
        assert kw["metrics"] == ["flow_velocity", "flow_time"]
        assert kw["terminology"] == GLOBAL
        assert kw["ct_method"] == CT_METHOD_B
        assert kw["target_ct"] == 45
        assert kw["open_browser"] is True

    def test_no_report_exits_with_error(self, monkeypatch, capsys, tmp_path):
        with pytest.raises(SystemExit) as exc:
            self._run(monkeypatch, [str(tmp_path / "cfg.json")], result="")
        assert exc.value.code == 1
        assert "No report produced" in capsys.readouterr().err

    def test_pdf_without_html_is_not_an_error(self, monkeypatch, capsys, tmp_path):
        self._run(monkeypatch,
                  [str(tmp_path / "cfg.json"), "--pdf", str(tmp_path / "r.pdf")],
                  result="")
        captured = capsys.readouterr()
        assert captured.err == ""
