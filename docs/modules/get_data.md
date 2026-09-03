# get_data

Two equal acquisition paths for Jira data — **REST fetch** and **manual
export** — ending in the same JSON file that `transform_data` consumes.

**Status:** implemented (alpha)

Why two paths: in large organisations, approval for direct API access can
take a long time. The manual export (chapter 1 of the manual) therefore
stays a first-class option; `get_data` adds the automated fetch and a
validator for exports, both producing/checking the identical artifact so
the pipeline behind them never changes.

## Manuals

| Language | Download |
|----------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../get_data_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../get_data_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../get_data_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../get_data_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../get_data_ManuelUtilisateur.pdf) |

## Path 1 — REST fetch

```bash
set JIRA_TOKEN=YourAPIToken
python -m get_data fetch --url https://company.atlassian.net --project ART_A --email name@company.com --output ART_A.json
```

- **API versions**: `--api v3` (default; `POST /rest/api/3/search/jql`,
  cursor pagination via `nextPageToken`) or `--api v2`
  (`GET /rest/api/2/search`, offset pagination via `startAt`).
- **Auth**: `--auth cloud` (Basic: e-mail + API token, Jira Cloud) or
  `--auth bearer` (PAT, Server/Data Center).
- **Security**: the token comes only from an environment variable
  (`--token-env`, default `JIRA_TOKEN`) — never as a command-line argument,
  never stored, never logged.
- Pages are fetched sequentially with `expand=changelog`, duplicates
  removed, and the result written in the export envelope
  (`{expand, startAt, maxResults, total, issues}`).
- Error messages are actionable: 401/403 points to token/auth **or the
  still-missing API approval** — and to the manual path as the fallback.

## Path 2 — manual export (unchanged, plus a validator)

The manual export via curl/browser (manual, chapter 1) works exactly as
before. New: validate the file before feeding the pipeline:

```bash
python -m get_data check ART_A_merged.json
```

The check catches the classic mistakes: missing required fields, missing
changelog (`expand=changelog` forgotten), duplicate keys — and forgotten
follow-up pages (`total` larger than the issues actually in the file).
Exit code 0 = usable, 2 = not usable.

## GUI

`python -m get_data` (or the **Get Data** card in the launcher) opens a
window with both paths as a toggle: *Jira REST fetch* (URL, project or
JQL, API v3/v2, cloud/bearer auth, token field — memory only) and
*Existing export* (pick a file → check). Fetch and check run in a
background thread with log output; DE/EN labels.

## Architecture

```
get_data/
├── __main__.py   Dispatcher: GUI without arguments, CLI with arguments
├── cli.py        Sub-commands fetch (REST) and check (export validation)
├── client.py     Jira REST client: v3/v2 pagination, auth, error mapping
├── validate.py   Export validation (fields, changelog, pages, duplicates)
└── gui.py        Two-path window (mode toggle), thread + log pattern
```

Standard library only (urllib) — no new dependencies. A contract test
guarantees that a fetched file and a manual export of the same data are
processed identically by `transform_data`.
