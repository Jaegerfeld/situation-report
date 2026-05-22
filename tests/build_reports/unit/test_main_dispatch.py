# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.05.2026
# Geändert:       22.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Argument-Weiche in build_reports/__main__.py. Prüft,
#   dass ohne Argumente die GUI startet, `--gui-template <pfad>` die GUI mit
#   einem Handover-Template startet und sonstige Argumente in die CLI gehen.
# =============================================================================

from __future__ import annotations

from pathlib import Path

import pytest

import build_reports.__main__ as entry


def test_no_args_launches_gui_without_template(monkeypatch):
    """Without arguments, the GUI is launched and no handover template passed."""
    calls: list = []
    monkeypatch.setattr(entry, "_launch_gui", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(entry.sys, "argv", ["build_reports"])

    entry.main()

    assert calls == [((), {})]


def test_gui_template_flag_launches_gui_with_path(monkeypatch):
    """`--gui-template <path>` launches the GUI with that template path."""
    received: list[Path] = []
    monkeypatch.setattr(entry, "_launch_gui", lambda p: received.append(p))
    monkeypatch.setattr(
        entry.sys, "argv", ["build_reports", "--gui-template", "/tmp/handover.json"]
    )

    entry.main()

    assert received == [Path("/tmp/handover.json")]


def test_gui_template_flag_without_path_exits(monkeypatch):
    """`--gui-template` without a path argument exits with an error."""
    monkeypatch.setattr(entry, "_launch_gui", lambda *a, **k: None)
    monkeypatch.setattr(entry.sys, "argv", ["build_reports", "--gui-template"])

    with pytest.raises(SystemExit):
        entry.main()


def test_other_arguments_route_to_cli(monkeypatch):
    """Any non-GUI argument delegates to the CLI entry point."""
    import build_reports.cli as cli

    calls: list = []
    monkeypatch.setattr(cli, "main", lambda: calls.append("cli"))
    monkeypatch.setattr(entry, "_launch_gui", lambda *a, **k: calls.append("gui"))
    monkeypatch.setattr(entry.sys, "argv", ["build_reports", "some.xlsx", "--help"])

    entry.main()

    assert calls == ["cli"]
