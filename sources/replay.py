# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Replay — Provider-Anfragen aus aufgezeichneten Antworten bedienen, ohne
#   Netz (Beta, Schnitt 1c, Entscheidung E4 vom 26.10.2026). Eine Quelle in
#   `sources.json` trägt `"replay": "<datei>.json"`; die Datei hält die
#   Antworten des echten Systems in dessen Format, adressiert über Pfad und
#   Kennparameter der Anfrage. `sources.http.get_json` fragt zuerst das
#   aktive Replay — die Provider bleiben unverändert und lesen exakt das,
#   was sie auch von Prometheus, GitHub, GitLab oder SonarQube bekämen.
#
#   Zweck: der Demo-Datenraum des Testdaten-Generators bringt je Provider
#   Rohdaten mit, `python -m sources fetch` läuft darauf ohne Zugang zu
#   einem System, und ein Test vergleicht, was der Provider daraus macht,
#   mit dem direkt erzeugten Register (Writer gegen Reader).
# =============================================================================

from __future__ import annotations

import copy
import json
import urllib.parse
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

REPLAY_KEY = "replay"
REPLAY_SCHEMA = 1


class Replay:
    """
    Recorded responses of one system.

    File shape (schema 1)::

        {"schema": 1, "system": "github",
         "responses": [{"path": "/repos/demo/alpha-1/deployments",
                        "params": {"environment": "production"},
                        "body": [...]}, ...]}

    A request matches an entry when its URL path equals ``path`` and every
    key in ``params`` appears in the query with that value (other query
    parameters, such as time windows, are ignored). The first match wins.
    """

    def __init__(self, path: Path, system: str, responses: list[dict[str, Any]]) -> None:
        self.path = path
        self.system = system
        self.responses = responses

    @classmethod
    def load(cls, path: Path) -> Replay:
        """Read and validate a replay file; raises RuntimeError on problems."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as exc:
            raise RuntimeError(f"Replay file '{path}' cannot be read: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Replay file '{path}' is not valid JSON: {exc}") from exc
        if not isinstance(data, dict) or int(data.get("schema", 0)) != REPLAY_SCHEMA:
            raise RuntimeError(f"Replay file '{path}': expected schema {REPLAY_SCHEMA}.")
        responses = data.get("responses")
        if not isinstance(responses, list):
            raise RuntimeError(f"Replay file '{path}': 'responses' must be a list.")
        for entry in responses:
            if (not isinstance(entry, dict) or not isinstance(entry.get("path"), str)
                    or "body" not in entry):
                raise RuntimeError(f"Replay file '{path}': every response needs "
                                   f"'path' and 'body'.")
            params = entry.get("params", {})
            if not isinstance(params, dict):
                raise RuntimeError(f"Replay file '{path}': 'params' must be an object.")
        return cls(Path(path), str(data.get("system", "")), responses)

    def lookup(self, url: str) -> Any:
        """The recorded body for ``url``; raises RuntimeError when none matches."""
        parts = urllib.parse.urlsplit(url)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(
            parts.query, keep_blank_values=True).items()}
        for entry in self.responses:
            if entry["path"] != parts.path:
                continue
            params = entry.get("params", {})
            if all(query.get(k) == str(v) for k, v in params.items()):
                return copy.deepcopy(entry["body"])
        shown = parts.path + (f"?{parts.query}" if parts.query else "")
        raise RuntimeError(
            f"Replay '{self.path.name}' ({self.system or 'unknown system'}) has no "
            f"recorded response for {shown} — the raw data does not cover this request.")


_ACTIVE: list[Replay] = []


def active() -> Replay | None:
    """The replay currently serving requests, or None (live HTTP)."""
    return _ACTIVE[-1] if _ACTIVE else None


@contextmanager
def activated(replay: Replay | None) -> Iterator[None]:
    """Serve every get_json() inside the block from ``replay`` (None = live)."""
    if replay is None:
        yield
        return
    _ACTIVE.append(replay)
    try:
        yield
    finally:
        _ACTIVE.pop()


def resolve_relative(value: str, base_dir: Path | None) -> Path:
    """
    A config path as the user meant it: relative paths count from the
    working directory first and, when nothing is there, from the folder of
    the config file (so a data room can be run from anywhere).
    """
    path = Path(value)
    if path.is_absolute() or base_dir is None or path.exists():
        return path
    candidate = Path(base_dir) / path
    return candidate if candidate.exists() else path


def replay_from_config(config: dict[str, Any], base_dir: Path | None = None) -> Replay | None:
    """Load the replay a source config names (``"replay": ...``), else None."""
    value = config.get(REPLAY_KEY)
    if not value:
        return None
    return Replay.load(resolve_relative(str(value), base_dir))
