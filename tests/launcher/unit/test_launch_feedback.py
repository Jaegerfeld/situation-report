# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests zu den UX-Audit-Befunden #1 und #2 des Launchers (Beta-UX):
#   Nach „Starten" zeigt die Karte sofort den Wartezustand (Text, deaktiviert,
#   Wartecursor) und kehrt nach dem Einschwingen zurück; ein Modul, das nicht
#   startet (OSError beim Popen oder Rückgabewert ≠ 0), erzeugt einen Fehler-
#   dialog mit Modulname und stderr-Auszug; ein laufendes Modul erzeugt keinen.
#   Der Text der Dialoge steht in allen fünf Sprachen.
# =============================================================================

from __future__ import annotations

import subprocess
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest

import launcher.gui as gui


class _Proc:
    def __init__(self, code):
        self._code = code

    def poll(self):
        return self._code


@pytest.fixture
def app():
    try:
        a = gui.LauncherApp()
    except tk.TclError as exc:  # pragma: no cover - headless CI
        pytest.skip(f"no display: {exc}")
    a.update_idletasks()
    yield a
    try:
        a.destroy()
    except tk.TclError:
        pass


def _launch(app, code=0, oserror=None):
    errors: list[tuple[str, str]] = []
    with patch.object(subprocess, "Popen", return_value=_Proc(code)) as popen, \
         patch.object(gui.messagebox, "showerror", side_effect=lambda t, m, **k: errors.append((t, m))):
        if oserror:
            popen.side_effect = OSError(oserror)
        with patch.object(app, "after") as after:          # capture the settle callback
            app._launch("build_reports")
        app.update_idletasks()
        return errors, popen, after


class TestPendingState:
    def test_click_shows_pending_state_at_once(self, app) -> None:
        btn = app._launch_button("build_reports")
        assert btn["text"] == "Starten" or btn["text"] == "Launch"
        errors, popen, after = _launch(app)
        assert popen.called and str(btn["state"]) == "disabled" and app["cursor"] == "watch"
        assert btn["text"] in ("Startet …", "Starting …")
        assert after.call_args.args[0] == gui._LAUNCH_SETTLE_MS and errors == []

    def test_settle_restores_button_without_dialog_when_running(self, app) -> None:
        btn = app._launch_button("build_reports")
        errors, popen, after = _launch(app, code=None)
        with patch.object(gui.messagebox, "showerror", side_effect=lambda t, m, **k: errors.append((t, m))):
            after.call_args.args[1]()                      # the scheduled settle callback
        assert str(btn["state"]) == "normal" and app["cursor"] == "" and errors == []
        assert btn["text"] in ("Starten", "Launch")


class TestFailure:
    def test_dead_process_reports_stderr_tail(self, app, tmp_path) -> None:
        errors, popen, after = _launch(app, code=1)
        # the settle callback reads the temp log - stand in for its stderr content
        with patch.object(gui.messagebox, "showerror", side_effect=lambda t, m, **k: errors.append((t, m))):
            with patch.object(Path, "read_text", return_value="Traceback ...\nModuleNotFoundError: No module named 'plotly'\n"):
                after.call_args.args[1]()
        assert len(errors) == 1
        title, message = errors[0]
        assert title in ("Modul konnte nicht gestartet werden", "Module could not be started")
        assert "Build Reports" in message and "No module named 'plotly'" in message
        assert str(app._launch_button("build_reports")["state"]) == "normal"

    def test_popen_oserror_reports_immediately(self, app) -> None:
        errors, popen, after = _launch(app, oserror="No such file: python")
        assert not after.called and len(errors) == 1
        assert "No such file: python" in errors[0][1] and "Build Reports" in errors[0][1]
        assert str(app._launch_button("build_reports")["state"]) == "normal" and app["cursor"] == ""

    def test_texts_in_all_languages(self) -> None:
        for lang, texts in gui._T.items():
            assert "{module}" in texts["msg_launch_failed"] and "{detail}" in texts["msg_launch_failed"], lang
            assert texts["btn_starting"].endswith("…") and texts["dlg_launch_failed_title"], lang
