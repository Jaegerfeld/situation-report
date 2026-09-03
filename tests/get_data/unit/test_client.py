# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für get_data.client (C3, REST-Weg): Config-Validierung,
#   Auth-Header (Basic/Bearer), v3-Cursor- und v2-Offset-Paginierung,
#   Dedupe, Sicherheitslimit, Fehlerbilder (401/403 mit Freigabe-Hinweis,
#   400 mit JQL-Hinweis) und der Datei-Export im transform_data-Format.
#   Alle HTTP-Aufrufe sind gemockt — kein Netzwerk.
# =============================================================================

from __future__ import annotations

import base64
import io
import json
import urllib.error
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from get_data.client import (
    API_V2,
    AUTH_BEARER,
    JiraConfig,
    fetch_issues,
    fetch_to_file,
)


def _config(**overrides) -> JiraConfig:
    base = dict(base_url="https://jira.example.com", token="secret-token",
                project="ART_A", email="user@example.com")
    base.update(overrides)
    return JiraConfig(**base)


def _issue(key: str) -> dict:
    return {"key": key,
            "fields": {"issuetype": {"name": "Feature"},
                       "created": "2025-01-01T09:00:00.000+0000",
                       "status": {"name": "Done"}},
            "changelog": {"histories": [{"items": []}]}}


@contextmanager
def _mock_pages(pages: list[dict]):
    """Patch _urlopen to return the given JSON pages in order; records requests."""
    calls: list = []

    def fake_urlopen(req, timeout=0):
        calls.append(req)
        body = json.dumps(pages[len(calls) - 1]).encode("utf-8")

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()

        return _Resp(body)

    with patch("get_data.client._urlopen", side_effect=fake_urlopen):
        yield calls


class TestConfigValidation:
    def test_rejects_bad_url_api_auth_token(self) -> None:
        with pytest.raises(ValueError, match="http"):
            _config(base_url="jira.example.com").validate()
        with pytest.raises(ValueError, match="API version"):
            _config(api_version="v9").validate()
        with pytest.raises(ValueError, match="auth mode"):
            _config(auth_mode="magic").validate()
        with pytest.raises(ValueError, match="token"):
            _config(token="").validate()

    def test_cloud_needs_email_and_query_needs_project_or_jql(self) -> None:
        with pytest.raises(ValueError, match="e-mail"):
            _config(email="").validate()
        with pytest.raises(ValueError, match="project key or an explicit JQL"):
            _config(project="", jql="").validate()

    def test_explicit_jql_wins_over_project(self) -> None:
        cfg = _config(jql="assignee = x")
        assert cfg.effective_jql() == "assignee = x"
        assert _config().effective_jql() == \
            'project = "ART_A" ORDER BY created ASC'


class TestFetchV3:
    def test_paginates_until_islast_and_sends_cursor(self) -> None:
        pages = [
            {"issues": [_issue("A-1"), _issue("A-2")],
             "isLast": False, "nextPageToken": "tok-2"},
            {"issues": [_issue("A-3")], "isLast": True},
        ]
        with _mock_pages(pages) as calls:
            data = fetch_issues(_config(), log=lambda m: None)
        assert [i["key"] for i in data["issues"]] == ["A-1", "A-2", "A-3"]
        assert data["total"] == 3
        assert len(calls) == 2
        body2 = json.loads(calls[1].data.decode("utf-8"))
        assert body2["nextPageToken"] == "tok-2"
        assert body2["expand"] == ["changelog"]
        assert calls[0].get_full_url().endswith("/rest/api/3/search/jql")

    def test_basic_auth_header_never_leaks_into_url(self) -> None:
        with _mock_pages([{"issues": [], "isLast": True}]) as calls:
            fetch_issues(_config(), log=lambda m: None)
        header = calls[0].get_header("Authorization")
        expected = base64.b64encode(b"user@example.com:secret-token").decode()
        assert header == f"Basic {expected}"
        assert "secret-token" not in calls[0].get_full_url()

    def test_dedupe_and_max_issues(self) -> None:
        pages = [{"issues": [_issue("A-1"), _issue("A-1"), _issue("A-2")],
                  "isLast": True}]
        with _mock_pages(pages):
            data = fetch_issues(_config(max_issues=2), log=lambda m: None)
        assert [i["key"] for i in data["issues"]] == ["A-1"]  # dedupe after cap
        pages = [{"issues": [_issue("A-1"), _issue("A-1"), _issue("A-2")],
                  "isLast": True}]
        with _mock_pages(pages):
            data = fetch_issues(_config(), log=lambda m: None)
        assert [i["key"] for i in data["issues"]] == ["A-1", "A-2"]


class TestFetchV2:
    def test_offset_pagination_and_bearer_header(self) -> None:
        pages = [
            {"issues": [_issue("B-1")], "total": 2, "startAt": 0},
            {"issues": [_issue("B-2")], "total": 2, "startAt": 1},
        ]
        cfg = _config(api_version=API_V2, auth_mode=AUTH_BEARER, email="")
        with _mock_pages(pages) as calls:
            data = fetch_issues(cfg, log=lambda m: None)
        assert [i["key"] for i in data["issues"]] == ["B-1", "B-2"]
        assert len(calls) == 2
        assert calls[0].get_header("Authorization") == "Bearer secret-token"
        assert "startAt=0" in calls[0].get_full_url()
        assert "startAt=1" in calls[1].get_full_url()
        assert "expand=changelog" in calls[0].get_full_url()

    def test_stops_on_empty_page(self) -> None:
        pages = [{"issues": [], "total": 99, "startAt": 0}]
        with _mock_pages(pages) as calls:
            data = fetch_issues(_config(api_version=API_V2),
                                log=lambda m: None)
        assert data["issues"] == []
        assert len(calls) == 1


class TestErrorMessages:
    def _raise_http(self, code: int):
        def fake_urlopen(req, timeout=0):
            raise urllib.error.HTTPError(
                req.get_full_url(), code, "err", {},
                io.BytesIO(b'{"errorMessages":["nope"]}'))
        return fake_urlopen

    def test_401_points_to_token_and_manual_export_path(self) -> None:
        with patch("get_data.client._urlopen", side_effect=self._raise_http(401)):
            with pytest.raises(RuntimeError) as exc:
                fetch_issues(_config(), log=lambda m: None)
        msg = str(exc.value)
        assert "401" in msg and "approval" in msg and "manual export" in msg
        assert "secret-token" not in msg

    def test_400_points_to_jql(self) -> None:
        with patch("get_data.client._urlopen", side_effect=self._raise_http(400)):
            with pytest.raises(RuntimeError, match="JQL"):
                fetch_issues(_config(), log=lambda m: None)

    def test_network_error_names_host(self) -> None:
        with patch("get_data.client._urlopen",
                   side_effect=urllib.error.URLError("refused")):
            with pytest.raises(RuntimeError, match="jira.example.com"):
                fetch_issues(_config(), log=lambda m: None)


class TestFetchToFile:
    def test_writes_export_envelope(self, tmp_path) -> None:
        pages = [{"issues": [_issue("A-1")], "isLast": True}]
        out = tmp_path / "raw" / "ART_A.json"
        with _mock_pages(pages):
            count = fetch_to_file(_config(), out, log=lambda m: None)
        assert count == 1
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"expand", "startAt", "maxResults",
                                    "total", "issues"}
        assert data["expand"] == "changelog"
        assert data["total"] == 1
