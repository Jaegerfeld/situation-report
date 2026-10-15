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

## Data minimisation at the source (R1, since 0.51.0)

No module of the pipeline reads a person field. `transform_data` needs exactly seven paths:
`project.key`, `issuetype.name`, `status.name`, `created`, `components[].name`, `resolution.name`
and, from the changelog, each history's `created` plus its status items. Yet a raw export carries
person data: every changelog entry names its **author** (display name, e-mail, account id, avatar,
time zone), person items carry names in `fromString`/`toString`, and a manual export adds
`assignee`, `reporter`, `creator`, comments and descriptions. All of it is by-catch — so `get_data`
removes it at the source, before anything else touches the file.

- **Allowlist, not denylist.** Issue fields are reduced to the seven paths above; `--keep FIELD`
  adds named non-person fields (e.g. `summary`, `labels`). Person fields can never be kept.
- **The changelog stays complete** — every history, every item, so the transitions are gapless.
  Persons in it are anonymised: the author becomes the constant `anonymised` (a constant, not a
  per-person pseudonym — a pseudonym would still be personal data), items of person fields keep
  the field name and lose their values, items of free-text fields (description, summary, comment)
  lose their text values.
- **REST fetch always minimises** — no opt-out, since no pipeline purpose needs persons.
- **Manual export:** `python -m get_data minimise EXPORT.json` writes `EXPORT_min.json` next to
  the original (which stays; the log reminds you to delete it once the minimised file is checked).
  `check` warns when an export still holds person data. GUI: button **Minimise** next to **Check**.
- **Report:** what was removed, as counts per field — person fields separately.
- **Contract test:** the tracked test export, raw and minimised, yields identical IssueTimes,
  Transitions and CFD in `transform_data`.

```bash
python -m get_data fetch --url https://company.atlassian.net --project ART_A --email name@company.com --output ART_A.json --keep summary
python -m get_data minimise ART_A_merged.json            # -> ART_A_merged_min.json
python -m get_data check ART_A_merged.json               # warns: person data present
```

**Note on the legal basis (an assessment, not legal advice).** Aggregating issue data into a
situational picture is itself a processing operation under the GDPR and needs a legal basis — in
practice legitimate interest (Art. 6(1)(f)), with the right to object; data minimisation (Art. 5(1)(c))
is a principle of every processing. Minimising at the source lowers the amount and the risk of
person data in the pipeline, but it does not replace the legal basis, and operators should check
whether a data-protection impact assessment (Art. 35) is required. Sources: Rohrlich, *KI und
Recht*, ch. 3; EDPB Opinion 28/2024; DSK guidance on AI and data protection.

## GUI

`python -m get_data` (or the **Get Data** card in the launcher) opens a
window with both paths as a toggle: *Jira REST fetch* (URL, project or
JQL, API v3/v2, cloud/bearer auth, token field — memory only) and
*Existing export* (pick a file → check or minimise). Fetch, check and minimise run in a
background thread with log output; DE/EN labels.

## Architecture

```
get_data/
├── __main__.py   Dispatcher: GUI without arguments, CLI with arguments
├── cli.py        Sub-commands fetch (REST), check (export validation), minimise (R1)
├── client.py     Jira REST client: v3/v2 pagination, auth, error mapping
├── validate.py   Export validation (fields, changelog, pages, duplicates, person data)
├── minimise.py   Data minimisation (R1): allowlist of fields, changelog persons anonymised
└── gui.py        Two-path window (mode toggle), thread + log pattern
```

Standard library only (urllib) — no new dependencies. A contract test
guarantees that a fetched file and a manual export of the same data are
processed identically by `transform_data`.
