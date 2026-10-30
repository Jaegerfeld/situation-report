# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Lokaler Server der Browser-Oberfläche (Beta, Schnitt 3b, E6). Nur die
#   Standardbibliothek: ThreadingHTTPServer an 127.0.0.1 mit Zufallsport,
#   jeder Pfad beginnt mit einem Zufallsschlüssel (ohne ihn: 403), kein
#   Zugriff aus dem Netz, keine externen Ressourcen (CSP). Die JSON-API
#   übersetzt die Seite auf die Dienstschicht `dataspace`:
#
#     GET  /<key>/                 die Seite
#     GET  /<key>/api/options      Vorlagen, Struktur-Vorlagen, Vorgaben
#     POST /<key>/api/preview      Schätzung + Geschichte für die Eingaben
#     POST /<key>/api/generate     Erzeugung im Hintergrund (Ordner-Rückfrage)
#     GET  /<key>/api/progress     Schritte, Zustand, Ergebnis
#     POST /<key>/api/cancel       Abbruch zwischen Schritten
#     POST /<key>/api/browse       Ordnerdialog (tkinter als Helfer, eigener Prozess)
#     POST /<key>/api/open         README, Ordner, Report, Mappe, Delta öffnen
#
#   Ordnerwahl: Browser können keinen Ordner wählen — ein Pfadfeld plus
#   „Durchsuchen" über den tkinter-Dialog, wo er vorhanden ist (tkinter als
#   Helfer, nicht als Oberfläche).
# =============================================================================

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from build_reports.chart_texts import DEFAULT_LANG, LANGUAGES
from version import __version__

from ..dataspace import (
    STATE_DONE,
    STATE_RUNNING,
    STEPS,
    GenerationCancelled,
    GenerationRequest,
    ProgressEvent,
    estimate_request,
    generate_dataspace,
)
from ..i18n import normalise, step_label, template_title
from ..register_gen import SCALES
from ..scenario import DEFAULT_STANDS, MAX_STANDS, MIN_STANDS, _solution_tags
from ..story import (
    STORY_TEMPLATES,
    SUGGESTED_STANDS,
    bind_roles,
    story_for,
    story_to_dict,
)
from ..structure import (
    STRUCTURE_TEMPLATES,
    Structure,
    from_dict,
    structure_template,
    to_dict,
)
from .page import render_page
from .texts import LANGUAGE_NAMES, texts_for

HOST = "127.0.0.1"
DEFAULT_REALISM = 60
_LOG_KEEP = 40

JOB_IDLE = "idle"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"

#: The folder dialog runs in its own interpreter: tkinter stays out of the
#: server process and a missing tkinter is just "no dialog".
_BROWSE_SCRIPT = (
    "import sys, tkinter, tkinter.filedialog as fd\n"
    "root = tkinter.Tk(); root.withdraw(); root.attributes('-topmost', True)\n"
    "path = fd.askdirectory(initialdir=sys.argv[1] or None, mustexist=False)\n"
    "print(path or '')\n"
)


def default_browse(initial: str) -> str | None:
    """Ask for a folder with tkinter in a child process; None when no dialog exists."""
    try:
        proc = subprocess.run([sys.executable, "-c", _BROWSE_SCRIPT, initial],
                              capture_output=True, text=True, timeout=600, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    chosen = proc.stdout.strip()
    return chosen or ""


def default_open(target: Path) -> None:
    """Open a file or folder with the system default (browser for HTML)."""
    if target.suffix.lower() in (".html", ".htm", ".md", ".json", ".txt"):
        webbrowser.open(target.resolve().as_uri())
        return
    if sys.platform.startswith("win"):
        os.startfile(str(target))  # type: ignore[attr-defined]  # noqa: S606
    else:
        webbrowser.open(target.resolve().as_uri())


class Job:
    """The one generation a server runs at a time."""

    def __init__(self) -> None:
        self.state = JOB_IDLE
        self.events: list[dict[str, Any]] = []
        self.logs: list[str] = []
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.cancel_flag = False
        self.started = 0.0
        self.finished = 0.0
        self.thread: threading.Thread | None = None
        self.rooms: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def add_event(self, event: ProgressEvent) -> None:
        with self.lock:
            self.events.append(asdict(event))

    def add_log(self, line: str) -> None:
        with self.lock:
            self.logs.append(line)
            del self.logs[:-_LOG_KEEP]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            end = self.finished or time.monotonic()
            return {"state": self.state, "events": list(self.events), "logs": list(self.logs),
                    "result": self.result, "error": self.error,
                    "elapsed_s": round(end - self.started, 1) if self.started else 0.0}


class DataspaceServer(ThreadingHTTPServer):
    """HTTP server bound to the loopback address with a per-run access key."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, lang: str = DEFAULT_LANG, port: int = 0,
                 opener: Callable[[Path], None] = default_open,
                 browse: Callable[[str], str | None] = default_browse,
                 verbose: bool = False) -> None:
        super().__init__((HOST, port), _Handler)
        self.token = secrets.token_hex(16)
        # One language for page and generated texts; the page's switch
        # (``/?lang=xx``) changes both for this server (single user, loopback).
        self.ui_lang = normalise(lang)
        self.data_lang = self.ui_lang
        self.opener = opener
        self.browse = browse
        self.verbose = verbose
        self.job = Job()
        self.job_lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.server_port}/{self.token}/"

    def set_lang(self, lang: str) -> None:
        """Switch page and data language (the page's language select reloads with ?lang=)."""
        self.ui_lang = normalise(lang)
        self.data_lang = self.ui_lang

    # --- API -----------------------------------------------------------------

    def options(self) -> dict[str, Any]:
        today = date.today()
        return {
            "version": __version__,
            "lang": self.ui_lang,
            "data_lang": self.data_lang,
            "ui_languages": [{"id": code, "name": LANGUAGE_NAMES[code]} for code in LANGUAGES],
            "templates": [{"id": t, "title": template_title(t, self.ui_lang),
                           "suggested_stands": SUGGESTED_STANDS[t]} for t in STORY_TEMPLATES],
            "structure_templates": [{"id": s, "structure": to_dict(structure_template(s))}
                                    for s in STRUCTURE_TEMPLATES],
            "scales": list(SCALES),
            "languages": list(LANGUAGES),
            "stands": {"min": MIN_STANDS, "max": MAX_STANDS, "default": DEFAULT_STANDS},
            "steps": [{"id": s, "label": step_label(s, self.ui_lang)} for s, _label in STEPS],
            "defaults": {"seed": 42, "reference": today.isoformat(), "realism": DEFAULT_REALISM,
                         "scale": "m",
                         "output_dir": str(Path.home() / f"SituationReport-Datenraum-{today.isoformat()}")},
        }

    def preview(self, body: dict[str, Any]) -> dict[str, Any]:
        structure = _structure_from_body(body)
        template = str(body.get("template") or "standard")
        if template not in STORY_TEMPLATES:
            raise ValueError(f"Unknown story template '{template}'.")
        stands = _stands_from_body(body, template)
        switches = _switches_from_body(body)
        request = GenerationRequest(output_dir=Path("."), structure=structure, template=template,
                                    switches=switches, stands=stands, scale=str(body.get("scale") or "m"))
        request.validate()
        first = structure.portfolios[0]
        est = estimate_request(request)
        story = story_for(template, bind_roles(first, self.ui_lang), _solution_tags(first), stands,
                          switches, lang=self.ui_lang)
        return {"ok": True, "describe": structure.describe(), "stands": stands,
                "estimate": {**asdict(est), "warn_reason": est.warn_text(self.ui_lang)},
                "story": story_to_dict(story)}

    def start_generation(self, body: dict[str, Any]) -> dict[str, Any]:
        request = request_from_body(body, self.data_lang)
        request.validate()
        with self.job_lock:
            if self.job.state == JOB_RUNNING:
                return {"ok": False, "busy": True}
        out = Path(request.output_dir)
        if out.exists() and not out.is_dir():
            raise ValueError(f"{out} ist kein Ordner.")
        if out.is_dir() and any(out.iterdir()) and not body.get("confirm"):
            return {"ok": False, "needs_confirm": True, "path": str(out),
                    "entries": sum(1 for _ in out.iterdir())}
        with self.job_lock:
            if self.job.state == JOB_RUNNING:
                return {"ok": False, "busy": True}
            job = Job()
            job.state = JOB_RUNNING
            job.started = time.monotonic()
            self.job = job
        thread = threading.Thread(target=self._run_job, args=(job, request), daemon=True)
        job.thread = thread
        thread.start()
        return {"ok": True, "started": True, "path": str(out)}

    def _run_job(self, job: Job, request: GenerationRequest) -> None:
        try:
            result = generate_dataspace(request, progress=job.add_event, log=job.add_log,
                                        cancel=lambda: job.cancel_flag)
        except GenerationCancelled:
            with job.lock:
                job.state = JOB_CANCELLED
                job.finished = time.monotonic()
            return
        except Exception as exc:  # the page shows it next to the step
            with job.lock:
                job.state = JOB_FAILED
                job.error = f"{type(exc).__name__}: {exc}"
                job.finished = time.monotonic()
            return
        rooms = _rooms(result.paths, result.structure)
        with job.lock:
            job.rooms = rooms
            job.result = {
                "root": str(result.root), "name": result.root.name, "seed": request.seed,
                "issues": result.issues, "registers": result.registers, "stands": result.stands,
                "deltas": result.deltas, "providers": result.providers,
                "elapsed_s": result.elapsed_s, "arts": result.structure.n_arts,
                "solutions": result.structure.n_solutions,
                "portfolios": [{"key": r["key"], "name": r["name"]} for r in rooms],
                "story": ({"title": result.story.title, "summary": result.story.summary}
                          if result.story else None),
                "stand_dates": rooms[0]["stand_dates"] if rooms else [],
                "has_drafts": bool(result.ai_drafts),
                "listing": _listing(Path(rooms[0]["root"])) if rooms else [],
            }
            job.state = JOB_DONE
            job.finished = time.monotonic()

    def cancel(self) -> dict[str, Any]:
        with self.job_lock:
            job = self.job
        job.cancel_flag = True
        return {"ok": True, "state": job.state}

    def open_target(self, body: dict[str, Any]) -> dict[str, Any]:
        with self.job_lock:
            job = self.job
        if job.state != JOB_DONE or not job.rooms:
            raise LookupError("Noch kein fertiger Datenraum.")
        room = job.rooms[max(0, min(int(body.get("room", 0)), len(job.rooms) - 1))]
        root = Path(room["root"])
        what = str(body.get("what", ""))
        if what == "folder":
            target = root
        elif what == "readme":
            target = root / "README.md"
        elif what == "drafts":
            target = root / "ai_drafts" / "uebung_README.md"
        elif what == "report":
            target = _render_report(root, kind="report")
        elif what == "conference":
            target = _render_report(root, kind="conference")
        elif what == "delta":
            target = _delta_pair(root, room, int(body.get("a", 1)), int(body.get("b", 2)),
                                 self.data_lang)
        elif what == "delta_last":
            n = len(room["stand_dates"])
            target = _delta_pair(root, room, n - 1, n, self.data_lang)
        else:
            raise ValueError(f"unknown target '{what}'.")
        if not target.exists():
            raise LookupError(f"{target.name} fehlt.")
        self.opener(target)
        return {"ok": True, "path": str(target)}


# --- helpers -----------------------------------------------------------------

def _structure_from_body(body: dict[str, Any]) -> Structure:
    raw = body.get("structure")
    if isinstance(raw, dict):
        return from_dict(raw)
    name = str(body.get("structure_template") or "standard")
    return structure_template(name)


def _stands_from_body(body: dict[str, Any], template: str) -> int:
    raw = body.get("stands")
    if raw in (None, "", "auto"):
        return SUGGESTED_STANDS.get(template, DEFAULT_STANDS)
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("stands must be a number.") from exc


def _switches_from_body(body: dict[str, Any]) -> dict[str, bool]:
    raw = body.get("switches") or {}
    if not isinstance(raw, dict):
        raise ValueError("switches must be an object.")
    return {str(k): bool(v) for k, v in raw.items()}


def request_from_body(body: dict[str, Any], data_lang: str) -> GenerationRequest:
    """Translate the page's JSON into a GenerationRequest (ValueError on bad input)."""
    structure = _structure_from_body(body)
    template = str(body.get("template") or "standard")
    stands = _stands_from_body(body, template)
    out = str(body.get("output_dir") or "").strip()
    if not out:
        raise ValueError("output_dir is required.")
    try:
        seed = int(body.get("seed", 42))
    except (TypeError, ValueError) as exc:
        raise ValueError("seed must be a whole number.") from exc
    reference_raw = str(body.get("reference") or "")
    try:
        reference = date.fromisoformat(reference_raw) if reference_raw else None
    except ValueError as exc:
        raise ValueError("reference must be an ISO date.") from exc
    lang = str(body.get("lang") or data_lang)
    if lang not in LANGUAGES:
        raise ValueError(f"Unknown language '{lang}'.")
    art_profiles: dict[str, dict] | None = None
    realism = body.get("realism")
    if realism not in (None, "", DEFAULT_REALISM):
        try:
            value = int(realism)
        except (TypeError, ValueError) as exc:
            raise ValueError("realism must be 0-100.") from exc
        if not 0 <= value <= 100:
            raise ValueError("realism must be 0-100.")
        if value != DEFAULT_REALISM:
            art_profiles = {art: {"realism": value}
                            for p in structure.portfolios for art in p.arts}
    return GenerationRequest(
        output_dir=Path(out).expanduser(), structure=structure, template=template,
        switches=_switches_from_body(body), stands=stands,
        scale=str(body.get("scale") or "m"), seed=seed, reference=reference, lang=lang,
        art_profiles=art_profiles, ai_drafts=bool(body.get("ai_drafts")))


def _rooms(paths: dict[str, Any], structure: Structure) -> list[dict[str, Any]]:
    per = paths["portfolios"] if "portfolios" in paths else {structure.portfolios[0].key: paths}
    rooms = []
    for spec in structure.portfolios:
        room = per.get(spec.key)
        if not room:
            continue
        stand_dates: list[str] = []
        index = room.get("stands")
        if index and Path(index).is_file():
            data = json.loads(Path(index).read_text(encoding="utf-8"))
            stand_dates = [str(s["as_of"]) for s in data.get("stands", [])]
        rooms.append({"key": spec.key, "name": spec.name,
                      "root": str(Path(room["portfolio"]).parent), "stand_dates": stand_dates})
    return rooms


def _listing(root: Path) -> list[str]:
    lines = []
    for entry in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if entry.is_dir():
            count = sum(1 for _ in entry.rglob("*") if _.is_file())
            lines.append(f"{entry.name}/  ({count})")
        else:
            lines.append(entry.name)
    return lines


def _render_report(root: Path, kind: str) -> Path:
    from portfolio.aggregator import render_conference_html, render_html
    from portfolio.solution_config import load_solution_config

    config = load_solution_config(root / "portfolio.json")
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    if kind == "conference":
        html = render_conference_html(config, log=lambda m: None)
        target = reports / "konferenzmappe.html"
    else:
        html = render_html(config, log=lambda m: None)
        target = reports / "portfolio_report.html"
    target.write_text(html, encoding="utf-8")
    return target


def _delta_pair(root: Path, room: dict[str, Any], a: int, b: int, lang: str) -> Path:
    from portfolio.cli import run_delta_briefing

    n = len(room["stand_dates"])
    if not (1 <= a < b <= n):
        raise ValueError(f"stand pair {a}->{b} outside 1..{n}.")
    index = json.loads((root / "snapshots" / "stands.json").read_text(encoding="utf-8"))
    files = {int(s["index"]): root / "snapshots" / s["file"] for s in index["stands"]}
    target = root / "deltas" / f"delta_{a:02d}-{b:02d}.html"
    if not target.is_file():
        run_delta_briefing(files[a], files[b], output=target, lang=lang, log=lambda m: None)
    return target


# --- HTTP ------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    server: DataspaceServer  # type: ignore[assignment]
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
        if self.server.verbose:
            super().log_message(fmt, *args)

    # -- plumbing --
    def _headers(self, status: HTTPStatus, ctype: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         "connect-src 'self'; img-src data:; form-action 'none'; base-uri 'none'; "
                         "frame-ancestors 'none'")
        self.end_headers()

    def _send_json(self, status: HTTPStatus, obj: Any) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(data))
        self.wfile.write(data)

    def _send_html(self, status: HTTPStatus, html: str) -> None:
        data = html.encode("utf-8")
        self._headers(status, "text/html; charset=utf-8", len(data))
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, 2_000_000))
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid JSON body: {exc}") from exc
        return data if isinstance(data, dict) else {}

    def _route(self) -> tuple[str, ...] | None:
        parts = tuple(p for p in urlsplit(self.path).path.split("/") if p)
        if not parts or parts[0] != self.server.token:
            texts = texts_for(self.server.ui_lang)
            self._send_html(HTTPStatus.FORBIDDEN,
                            f"<!doctype html><meta charset='utf-8'><title>403</title>"
                            f"<p style='font-family:system-ui;padding:24px'>{texts['app']}: "
                            f"{texts['forbidden']}</p>")
            return None
        return parts[1:]

    # -- verbs --
    def do_GET(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            return
        if route == ():
            wanted = parse_qs(urlsplit(self.path).query).get("lang", [None])[0]
            if wanted in LANGUAGES and wanted != self.server.ui_lang:
                self.server.set_lang(wanted)
            self._send_html(HTTPStatus.OK, render_page(self.server.ui_lang, self.server.token,
                                                       __version__))
        elif route == ("api", "options"):
            self._send_json(HTTPStatus.OK, self.server.options())
        elif route == ("api", "progress"):
            self._send_json(HTTPStatus.OK, self.server.job.snapshot())
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        route = self._route()
        if route is None:
            return
        try:
            body = self._read_json()
            if route == ("api", "preview"):
                self._send_json(HTTPStatus.OK, self.server.preview(body))
            elif route == ("api", "generate"):
                answer = self.server.start_generation(body)
                self._send_json(HTTPStatus.CONFLICT if answer.get("busy") else HTTPStatus.OK, answer)
            elif route == ("api", "cancel"):
                self._send_json(HTTPStatus.OK, self.server.cancel())
            elif route == ("api", "browse"):
                chosen = self.server.browse(str(body.get("initial") or ""))
                self._send_json(HTTPStatus.OK, {"ok": chosen is not None, "path": chosen or None})
            elif route == ("api", "open"):
                self._send_json(HTTPStatus.OK, self.server.open_target(body))
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except LookupError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except Exception as exc:  # the page shows the message instead of a blank 500
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR,
                            {"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def serve(lang: str = DEFAULT_LANG, port: int = 0, open_browser: bool = True,
          log: Callable[[str], None] = print) -> DataspaceServer:
    """Start the server in the background; returns it (call shutdown() to stop)."""
    server = DataspaceServer(lang=lang, port=port)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25},
                              daemon=True, name="dataspace-web")
    thread.start()
    log(f"Datenraum-Oberfläche: {server.url}")
    if open_browser:
        webbrowser.open(server.url)
    return server


def run(lang: str = DEFAULT_LANG, port: int = 0, open_browser: bool = True) -> int:
    """Start, print the address and block until Ctrl+C."""
    server = serve(lang=lang, port=port, open_browser=open_browser)
    print("Beenden mit Strg+C.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


__all__ = ["DataspaceServer", "default_browse", "default_open", "request_from_body", "run",
           "serve", "STATE_DONE", "STATE_RUNNING"]
