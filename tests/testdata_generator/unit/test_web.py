# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Browser-Oberfläche des Datenraums (Beta Schnitt 3b, E6): Server nur an
#   127.0.0.1 mit Zufallsschlüssel (ohne Schlüssel 403), Seite mit Texten
#   und Schlüssel, Sicherheits-Header, Optionen, Vorschau, Erzeugung im
#   Hintergrund mit Fortschritt und Ergebnis, Rückfrage bei vollem Ordner,
#   Abbruch, Öffnen von README/Ordner/Delta/Report, Ordnerdialog-Helfer,
#   Übersetzung der Seiten-Eingaben in eine Anfrage (Realismus, Fehler).
# =============================================================================

from __future__ import annotations

import http.client
import json
import threading
import time
from datetime import date
from pathlib import Path

import pytest

from testdata_generator.web.server import DataspaceServer, request_from_body
from testdata_generator.web.texts import TEXTS, texts_for

REF = date(2025, 6, 30)


class Client:
    def __init__(self, server: DataspaceServer) -> None:
        self.port = server.server_port
        self.token = server.token

    def call(self, method: str, path: str, body=None, token: bool = True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        prefix = f"/{self.token}" if token else ""
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        conn.request(method, prefix + path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        ctype = resp.getheader("Content-Type") or ""
        payload = json.loads(raw.decode("utf-8")) if "json" in ctype else raw.decode("utf-8")
        return resp.status, payload, dict(resp.getheaders())


@pytest.fixture(scope="module")
def srv():
    opened: list[Path] = []
    server = DataspaceServer(lang="de", port=0, opener=opened.append,
                             browse=lambda initial: "C:/gewaehlt" if initial else None)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    yield server, Client(server), opened
    server.shutdown()
    server.server_close()


def _wait_done(client: Client, timeout: float = 240.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, j, _ = client.call("GET", "/api/progress")
        assert status == 200
        if j["state"] != "running":
            return j
        time.sleep(0.3)
    raise AssertionError("generation did not finish in time")


class TestAccess:
    def test_without_key_everything_is_forbidden(self, srv) -> None:
        _, client, _ = srv
        for path in ("/", "/api/options", "/wrongkey/api/options"):
            status, body, _ = client.call("GET", path, token=False)
            assert status == 403 and "Zugang nur" in body

    def test_page_carries_texts_key_and_security_headers(self, srv) -> None:
        server, client, _ = srv
        status, html, headers = client.call("GET", "/")
        assert status == 200 and html.startswith("<!doctype html>")
        assert server.token in html and TEXTS["de"]["h1_step1"] in html
        assert "cdn" not in html.lower() and "http://" not in html.replace("http://127.0.0.1", "")
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "127.0.0.1" in server.url and server.token in server.url

    def test_unknown_routes(self, srv) -> None:
        _, client, _ = srv
        assert client.call("GET", "/api/nothing")[0] == 404
        assert client.call("POST", "/api/nothing", {})[0] == 404


class TestOptionsAndPreview:
    def test_options(self, srv) -> None:
        _, client, _ = srv
        status, o, _ = client.call("GET", "/api/options")
        assert status == 200 and o["lang"] == "de"
        assert [t["id"] for t in o["templates"]] == ["calm", "standard", "escalation", "recovery"]
        assert {s["id"] for s in o["structure_templates"]} == {"small", "standard", "large"}
        assert o["stands"] == {"min": 2, "max": 12, "default": 6}
        assert [s["id"] for s in o["steps"]][0] == "story" and o["defaults"]["seed"] == 42

    def test_preview_returns_estimate_and_story(self, srv) -> None:
        _, client, _ = srv
        status, p, _ = client.call("POST", "/api/preview", {"structure_template": "small", "template": "escalation",
                                                            "switches": {"E3": False}})
        assert status == 200 and p["ok"]
        assert p["describe"] == "1 Portfolio · 1 Solution · 2 ARTs" and p["stands"] == 6
        assert p["estimate"]["jira_exports"] == 2 and p["estimate"]["deltas"] == 5
        blocked = next(e for e in p["story"]["events"] if e["id"] == "E3")
        assert blocked["enabled"] is False and p["story"]["template"] == "escalation"
        assert any("Nur eine Solution" in n for n in p["story"]["notices"])

    def test_preview_with_custom_structure_and_errors(self, srv) -> None:
        _, client, _ = srv
        structure = {"portfolios": [{"name": "P", "solutions": [{"name": "Nord", "arts": ["Nord-1", "Nord-2", "Nord-3"],
                                                                 "workflow": "classic"},
                                                                {"name": "Süd", "arts": ["Süd-1"], "workflow": "stage_map"}]}]}
        status, p, _ = client.call("POST", "/api/preview", {"structure": structure, "template": "standard", "stands": 3})
        assert status == 200 and p["story"]["roles"]["outlier_art"] == "Nord-3"
        structure["portfolios"][0]["solutions"][1]["arts"] = []
        status, p, _ = client.call("POST", "/api/preview", {"structure": structure, "template": "standard"})
        assert status == 400 and "at least one ART" in p["error"]
        status, p, _ = client.call("POST", "/api/preview", {"template": "drama"})
        assert status == 400 and "Unknown story template" in p["error"]


class TestGeneration:
    def test_full_run_with_progress_result_and_open(self, srv, tmp_path) -> None:
        server, client, opened = srv
        out = tmp_path / "raum"
        body = {"structure_template": "small", "template": "standard", "stands": 2, "scale": "s", "seed": 7,
                "reference": REF.isoformat(), "lang": "de", "realism": 60, "ai_drafts": False, "output_dir": str(out)}
        status, j, _ = client.call("POST", "/api/generate", body)
        assert status == 200 and j["ok"] and j["started"]
        status, busy, _ = client.call("POST", "/api/generate", body)
        assert status == 409 and busy["busy"]
        final = _wait_done(client)
        assert final["state"] == "done", final.get("error")
        steps = [e["step"] for e in final["events"] if e["state"] in ("done", "skipped")]
        assert steps[0] == "story" and "stands" in steps and "deltas" in steps and "ai_drafts" in steps
        r = final["result"]
        assert r["name"] == "raum" and r["stands"] == 2 and r["deltas"] == 1 and r["arts"] == 2
        assert r["issues"] > 0 and r["story"]["title"] == "Standard-Lage" and len(r["stand_dates"]) == 2
        assert any(line.startswith("snapshots/") for line in r["listing"]) and r["has_drafts"] is False
        # Open targets: README, folder, the latest delta, an explicit pair, the rendered report.
        for what in ("readme", "folder", "delta_last", "report", "conference"):
            status, o, _ = client.call("POST", "/api/open", {"what": what})
            assert status == 200 and o["ok"], (what, o)
        status, o, _ = client.call("POST", "/api/open", {"what": "delta", "a": 1, "b": 2})
        assert status == 200 and o["path"].endswith("delta_01-02.html")
        assert opened[-1].name == "delta_01-02.html" and (out / "reports" / "portfolio_report.html").is_file()
        status, o, _ = client.call("POST", "/api/open", {"what": "drafts"})
        assert status == 404
        status, o, _ = client.call("POST", "/api/open", {"what": "delta", "a": 2, "b": 1})
        assert status == 400

    def test_non_empty_folder_asks_first(self, srv, tmp_path) -> None:
        _, client, _ = srv
        out = tmp_path / "voll"
        out.mkdir()
        (out / "alt.txt").write_text("x", encoding="utf-8")
        body = {"structure_template": "small", "stands": 2, "scale": "s", "output_dir": str(out),
                "reference": REF.isoformat()}
        status, j, _ = client.call("POST", "/api/generate", body)
        assert status == 200 and j["needs_confirm"] and j["entries"] == 1 and not j["ok"]
        status, j, _ = client.call("POST", "/api/generate", {**body, "confirm": True})
        assert status == 200 and j["ok"]
        assert _wait_done(client)["state"] == "done"
        assert (out / "portfolio.json").is_file() and (out / "alt.txt").is_file()

    def test_invalid_request_is_a_400(self, srv, tmp_path) -> None:
        _, client, _ = srv
        status, j, _ = client.call("POST", "/api/generate", {"output_dir": str(tmp_path / "x"), "stands": 99})
        assert status == 400 and "stands must be" in j["error"]
        status, j, _ = client.call("POST", "/api/generate", {"stands": 2})
        assert status == 400 and "output_dir" in j["error"]

    def test_cancel_stops_between_steps(self, srv, tmp_path) -> None:
        _, client, _ = srv
        body = {"structure_template": "standard", "template": "standard", "stands": 4, "scale": "s",
                "output_dir": str(tmp_path / "abbruch"), "reference": REF.isoformat()}
        status, j, _ = client.call("POST", "/api/generate", body)
        assert status == 200 and j["ok"]
        status, c, _ = client.call("POST", "/api/cancel", {})
        assert status == 200 and c["ok"]
        final = _wait_done(client)
        assert final["state"] in ("cancelled", "done")
        if final["state"] == "cancelled":
            assert final["result"] is None

    def test_browse_uses_the_helper(self, srv) -> None:
        _, client, _ = srv
        status, j, _ = client.call("POST", "/api/browse", {"initial": "C:/"})
        assert status == 200 and j["ok"] and j["path"] == "C:/gewaehlt"
        status, j, _ = client.call("POST", "/api/browse", {"initial": ""})
        assert status == 200 and not j["ok"] and j["path"] is None


class TestRequestTranslation:
    def test_realism_becomes_art_profiles(self) -> None:
        req = request_from_body({"structure_template": "small", "output_dir": "x", "realism": 90,
                                 "stands": 3, "seed": "5"}, "en")
        assert req.art_profiles == {"Alpha-1": {"realism": 90}, "Alpha-2": {"realism": 90}}
        assert req.seed == 5 and req.stands == 3 and req.lang == "en" and req.reference is None
        default = request_from_body({"structure_template": "small", "output_dir": "x", "realism": 60}, "de")
        assert default.art_profiles is None and default.lang == "de" and default.resolved_stands() == 6

    @pytest.mark.parametrize("body,needle", [
        ({"output_dir": "x", "seed": "abc"}, "seed"),
        ({"output_dir": "x", "reference": "gestern"}, "reference"),
        ({"output_dir": "x", "lang": "xx"}, "language"),
        ({"output_dir": "x", "realism": 150}, "realism"),
        ({"output_dir": "x", "switches": ["E3"]}, "switches"),
        ({"output_dir": "x", "stands": "viele"}, "stands"),
    ])
    def test_bad_values_raise(self, body, needle) -> None:
        with pytest.raises(ValueError, match=needle):
            request_from_body(body, "de")


class TestTexts:
    def test_all_five_languages_have_the_same_keys(self) -> None:
        assert set(TEXTS) == {"de", "en", "ro", "pt", "fr"}
        assert all(set(TEXTS[lang]) == set(TEXTS["en"]) for lang in TEXTS)
        assert texts_for("fr") is TEXTS["fr"] and texts_for("de") is TEXTS["de"]
        assert texts_for("xx") is TEXTS["en"]
