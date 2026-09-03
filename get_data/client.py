# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Jira-REST-Client (Roadmap C3): holt Issues inklusive Changelog direkt
#   aus Jira und schreibt sie in exakt dem JSON-Format, das der manuelle
#   Export liefert und transform_data liest. Der REST-Weg ist bewusst nur
#   EINER von zwei gleichwertigen Erhebungswegen — der manuelle Export
#   (Handbuch Kapitel 1) bleibt vollwertig, weil die Freigabe für
#   API-Zugriffe in großen Organisationen lange dauern kann. Beide Wege
#   münden im selben Artefakt; die Pipeline dahinter ist identisch.
#   Nur Standardbibliothek (urllib); Tokens werden nie geloggt und nie
#   gespeichert.
# =============================================================================

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

API_V3 = "v3"
API_V2 = "v2"
API_VERSIONS = (API_V3, API_V2)

AUTH_CLOUD = "cloud"    # Basic auth: email + API token (Jira Cloud)
AUTH_BEARER = "bearer"  # Bearer PAT (Jira Server / Data Center)
AUTH_MODES = (AUTH_CLOUD, AUTH_BEARER)

#: Fields transform_data needs (manual section 1.4), plus helpful optionals.
DEFAULT_FIELDS = ("issuetype", "created", "status", "project",
                  "summary", "resolution")

_PAGE_SIZE_V3 = 100    # hard API limit per request (v3)
_PAGE_SIZE_V2 = 1000   # v2 supports up to 1000 per request
_TIMEOUT_SECONDS = 60

#: Patchable in tests; keeps urllib out of the call sites.
_urlopen = urllib.request.urlopen


@dataclass
class JiraConfig:
    """
    Connection settings for one fetch.

    ``jql`` overrides the project-derived default query entirely. The token
    is held in memory only — it is never written to disk or logs.
    """
    base_url: str
    token: str
    project: str = ""
    jql: str = ""
    api_version: str = API_V3
    auth_mode: str = AUTH_CLOUD
    email: str = ""
    max_issues: int = 10000
    fields: tuple[str, ...] = field(default=DEFAULT_FIELDS)

    def effective_jql(self) -> str:
        """The JQL actually sent: explicit jql wins, else project query."""
        if self.jql.strip():
            return self.jql.strip()
        if not self.project.strip():
            raise ValueError("Either a project key or an explicit JQL "
                             "query is required.")
        return f'project = "{self.project.strip()}" ORDER BY created ASC'

    def validate(self) -> None:
        """Raise ValueError on inconsistent settings (before any request)."""
        if not self.base_url.strip().lower().startswith(("http://", "https://")):
            raise ValueError("Jira base URL must start with http(s)://.")
        if self.api_version not in API_VERSIONS:
            raise ValueError(f"Unknown API version '{self.api_version}' — "
                             f"expected one of {', '.join(API_VERSIONS)}.")
        if self.auth_mode not in AUTH_MODES:
            raise ValueError(f"Unknown auth mode '{self.auth_mode}' — "
                             f"expected one of {', '.join(AUTH_MODES)}.")
        if not self.token:
            raise ValueError("No API token given (empty token).")
        if self.auth_mode == AUTH_CLOUD and not self.email.strip():
            raise ValueError("Cloud auth (Basic) needs the account e-mail.")
        self.effective_jql()


def _auth_header(config: JiraConfig) -> str:
    """Authorization header value for the configured auth mode."""
    if config.auth_mode == AUTH_CLOUD:
        raw = f"{config.email.strip()}:{config.token}".encode()
        return "Basic " + base64.b64encode(raw).decode("ascii")
    return f"Bearer {config.token}"


def _request(config: JiraConfig, url: str, body: dict | None) -> dict:
    """
    Execute one HTTP request and return the parsed JSON response.

    Raises:
        RuntimeError: With an actionable message on HTTP/network errors —
                      401/403 point to token/approval (the corporate
                      bottleneck), 400 to the JQL. The token itself never
                      appears in any message.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    req.add_header("Authorization", _auth_header(config))
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        if exc.code in (401, 403):
            raise RuntimeError(
                f"Jira refused the request (HTTP {exc.code}): check token, "
                f"e-mail/auth mode — or the API access approval is still "
                f"missing. In that case use the manual export path "
                f"(manual, chapter 1). {detail}") from exc
        if exc.code == 400:
            raise RuntimeError(
                f"Jira rejected the query (HTTP 400) — check the JQL. "
                f"{detail}") from exc
        raise RuntimeError(f"Jira request failed (HTTP {exc.code}). "
                           f"{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Jira at {config.base_url.strip()}: "
            f"{exc.reason}") from exc


def _fetch_v3(config: JiraConfig,
              log: Callable[[str], None]) -> list[dict[str, Any]]:
    """Cursor pagination via POST /rest/api/3/search/jql (nextPageToken)."""
    url = config.base_url.rstrip("/") + "/rest/api/3/search/jql"
    issues: list[dict[str, Any]] = []
    token: str | None = None
    while len(issues) < config.max_issues:
        body: dict[str, Any] = {
            "jql": config.effective_jql(),
            "maxResults": _PAGE_SIZE_V3,
            "expand": ["changelog"],
            "fields": list(config.fields),
        }
        if token:
            body["nextPageToken"] = token
        page = _request(config, url, body)
        got = page.get("issues", [])
        issues.extend(got)
        log(f"  Seite geladen: +{len(got)} Issues (gesamt {len(issues)})")
        if page.get("isLast", True) or not page.get("nextPageToken"):
            break
        token = str(page["nextPageToken"])
    return issues


def _fetch_v2(config: JiraConfig,
              log: Callable[[str], None]) -> list[dict[str, Any]]:
    """Offset pagination via GET /rest/api/2/search (startAt)."""
    base = config.base_url.rstrip("/") + "/rest/api/2/search"
    issues: list[dict[str, Any]] = []
    start_at = 0
    while len(issues) < config.max_issues:
        query = urllib.parse.urlencode({
            "jql": config.effective_jql(),
            "expand": "changelog",
            "maxResults": _PAGE_SIZE_V2,
            "startAt": start_at,
            "fields": ",".join(config.fields),
        })
        page = _request(config, f"{base}?{query}", None)
        got = page.get("issues", [])
        issues.extend(got)
        total = int(page.get("total", len(issues)))
        log(f"  Seite geladen: +{len(got)} Issues (gesamt {len(issues)}/{total})")
        start_at += len(got)
        if not got or start_at >= total:
            break
    return issues


def fetch_issues(
    config: JiraConfig,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """
    Fetch all issues (with changelog) for the configured query.

    Pages are fetched sequentially, duplicates removed by issue key, and the
    result wrapped in the same envelope the manual export produces — so
    transform_data consumes both paths identically.

    Args:
        config: Validated connection settings.
        log:    Progress callback (never receives the token).

    Returns:
        Export-shaped dict: {expand, startAt, maxResults, total, issues}.

    Raises:
        ValueError:   On inconsistent settings.
        RuntimeError: On HTTP/network failures (actionable messages).
    """
    config.validate()
    log(f"Jira-Abruf ({config.api_version}, {config.auth_mode}): "
        f"{config.base_url.strip()}")
    fetcher = _fetch_v3 if config.api_version == API_V3 else _fetch_v2
    raw = fetcher(config, log)

    seen: set[str] = set()
    issues: list[dict[str, Any]] = []
    for issue in raw[:config.max_issues]:
        key = str(issue.get("key", ""))
        if key and key in seen:
            continue
        seen.add(key)
        issues.append(issue)
    if len(issues) != len(raw):
        log(f"  {len(raw) - len(issues)} Duplikate entfernt")
    log(f"Fertig: {len(issues)} Issues")
    return {
        "expand": "changelog",
        "startAt": 0,
        "maxResults": len(issues),
        "total": len(issues),
        "issues": issues,
    }


def fetch_to_file(
    config: JiraConfig,
    output: Path,
    log: Callable[[str], None] = print,
) -> int:
    """
    Fetch issues and write the export JSON to ``output``.

    Returns:
        Number of issues written.
    """
    data = fetch_issues(config, log=log)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    log(f"Export geschrieben: {target}")
    return len(data["issues"])
