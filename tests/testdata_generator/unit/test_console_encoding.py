# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       31.10.2026
# Geändert:       31.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prüft, dass der Generator seine Konsolenausgabe auf UTF-8 stellt. Befund
#   aus dem Tester-Paket vom 31.10.2026: `--lang ro` stürzte in einer Windows-
#   Konsole mit cp1252 an „Spațiu de date“ ab (UnicodeEncodeError).
# =============================================================================

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

from testdata_generator.__main__ import ensure_utf8_console

REPO_ROOT = Path(__file__).resolve().parents[3]


def _cp1252_stream() -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


def test_ensure_utf8_console_reconfigures_legacy_stream() -> None:
    stream = _cp1252_stream()
    ensure_utf8_console(stream)
    assert stream.encoding.replace("-", "").lower() == "utf8"
    stream.write("Spațiu de date — ă ș ç ã")  # darf nicht mehr abstürzen
    stream.flush()


def test_ensure_utf8_console_leaves_utf8_and_plain_streams_alone() -> None:
    utf8_stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    plain = io.StringIO()  # hat kein reconfigure
    ensure_utf8_console(utf8_stream, plain)
    assert utf8_stream.encoding == "utf-8"
    plain.write("ă")
    assert plain.getvalue() == "ă"


def test_romanian_scenario_survives_legacy_console(tmp_path: Path) -> None:
    """Ende-zu-Ende: gleicher Aufruf wie im Tester-Paket, Konsole auf cp1252 gezwungen."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    env["PYTHONUTF8"] = "0"
    env.pop("PYTHONLEGACYWINDOWSSTDIO", None)
    result = subprocess.run(
        [sys.executable, "-m", "testdata_generator", "--scenario", "portfolio",
         "--structure", "small", "--story", "calm", "--lang", "ro", "--seed", "7",
         "--output", str(tmp_path / "ro")],
        cwd=REPO_ROOT, env=env, capture_output=True, timeout=300,
    )
    stderr = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, stderr[-800:]
    assert "UnicodeEncodeError" not in stderr
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert "Spa" in stdout and "de date" in stdout
    assert (tmp_path / "ro" / "README.md").exists()
