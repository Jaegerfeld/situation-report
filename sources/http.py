# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Gemeinsamer HTTP-Baustein der Quellen-Provider (C1/C2): JSON-GET über
#   urllib mit wählbarem Auth-Header, klaren Fehlermeldungen (401/403 →
#   Token/Freigabe — der Konzern-Engpass; Netz → Host benannt) und einem
#   patchbaren _urlopen für Tests. Tokens kommen aus Umgebungsvariablen,
#   erscheinen nie in Meldungen und werden nie gespeichert.
# =============================================================================

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

_TIMEOUT_SECONDS = 60

#: Patchable in tests; keeps urllib out of the providers.
_urlopen = urllib.request.urlopen


def token_from_env(config: dict[str, Any], default_var: str) -> str:
    """
    Resolve a provider token from the environment.

    ``config["token_env"]`` names the variable (default: ``default_var``).
    An empty value is allowed — providers decide whether auth is optional.
    """
    return os.environ.get(str(config.get("token_env", default_var)), "")


def get_json(url: str, headers: dict[str, str], source_name: str) -> Any:
    """
    HTTP GET returning parsed JSON, with actionable error mapping.

    Args:
        url:         Full request URL (no secrets in it).
        headers:     Extra headers (e.g. Authorization) — never logged.
        source_name: Human name for error messages (e.g. "Prometheus").

    Raises:
        RuntimeError: On HTTP/network/JSON errors, with the corporate
                      approval hint on 401/403.
    """
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    for name, value in headers.items():
        req.add_header(name, value)
    try:
        with _urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        if exc.code in (401, 403):
            raise RuntimeError(
                f"{source_name} refused the request (HTTP {exc.code}): "
                f"check the token — or the API access approval is still "
                f"missing; use the file source as fallback until it is "
                f"granted. {detail}") from exc
        raise RuntimeError(
            f"{source_name} request failed (HTTP {exc.code}). "
            f"{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach {source_name} at {url.split('?')[0]}: "
            f"{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{source_name} returned no valid JSON: {exc}") from exc


def bearer(token: str) -> dict[str, str]:
    """Authorization header for a bearer token ('' → no header)."""
    return {"Authorization": f"Bearer {token}"} if token else {}


def basic(user: str, password: str) -> dict[str, str]:
    """Authorization header for HTTP Basic auth."""
    raw = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {raw}"}
