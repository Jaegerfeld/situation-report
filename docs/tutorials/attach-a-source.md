# Tutorial: Attaching your own data source

**Audience:** a developer who has never attached a metric source to
SituationReport. **Time:** about 30 minutes. **You need:** the repository,
Python 3.11+, no external systems — everything runs against the demo
scenario. **At the end:** your own provider feeds the portfolio report.

---

## 1. The model in three terms

Everything in the `sources` framework revolves around three things:

1. **Record** — the normalised result. For an SLO it looks like this:

    ```json
    {"service": "Order API", "slo": "availability",
     "target_pct": 99.9, "sli_pct": 99.95,
     "window": "30d", "source": "csv:slos.csv"}
    ```

    There are three record kinds: `slo`, `dora`, `quality`. The report
    only ever sees records — never your system.

2. **Provider** — a translator: it reads *your* system (a file, a REST
   API, anything) and returns records. One Python file, one class.

3. **Register** — the JSON file a fetch writes
   (`{"schema": 1, "kind": "slo", "records": [...]}`). The solution
   config references it (`"slo": "slo.json"`), the report renders it.

One rule keeps everything comparable: **providers never judge**. Whether
an SLO is *breached* or a DORA unit is *low* is decided centrally, by the
same rule for every source. Your provider only translates values.

---

## 2. Use it before you build it (5 minutes)

Generate the demo portfolio and look at a finished register first:

```bash
python -m testdata_generator --scenario portfolio --output demo --seed 42
python -m sources providers
```

`providers` lists every discovered source (`csv`, `file`, `github`,
`gitlab`, `prometheus`, `sonarqube`). Now run your first fetch — using the
`file` provider and a register the scenario already made:

```bash
echo {"provider": "file", "path": "demo/slo_alpha.json"} > my_sources.json
python -m sources fetch --kind slo --config my_sources.json --output my_slo.json
```

Open `my_slo.json`: that is the target format. Whatever source you attach,
this is what comes out — which is exactly why sources are exchangeable.

---

## 3. Build your own provider, step by step

We attach a **CSV file** as a source (teams often keep SLO values in a
spreadsheet). No server needed — and the pattern is identical for any
system. The finished reference lives in `sources/providers/csv_slo.py`;
type your own copy to learn, or read along.

**Step 3.1 — create one file.** A provider is a single module in
`sources/providers/`. Create `sources/providers/my_csv.py`:

```python
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sources.base import KIND_SLO, SloRecord


class MyCsvSource:
    # (1) The name used in configs and shown by `providers`.
    provider_id = "my_csv"
    # (2) What this source can deliver.
    kinds = (KIND_SLO,)

    # (3) The translator: foreign format in, records out.
    def fetch(self, kind, config, log):
        path = Path(config["path"])
        if not path.is_file():
            raise RuntimeError(f"my_csv: '{path}' does not exist.")
        fetched_at = datetime.now().isoformat(timespec="seconds")
        records = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                records.append(SloRecord(
                    service=row["service"],
                    slo=row["slo"],
                    target_pct=float(row["target_pct"]),
                    sli_pct=float(row["sli_pct"]) if row.get("sli_pct") else None,
                    source=f"my_csv:{path.name}",
                    fetched_at=fetched_at,
                ))
        log(f"  my_csv: {len(records)} records")
        return records


# (4) The auto-discovery looks for exactly this object.
PROVIDER = MyCsvSource()
```

Four numbered ideas — that is the whole contract: an id, the kinds, a
`fetch()` that translates, and a module-level `PROVIDER` object. **No
registry to edit anywhere**: the file's existence registers it.

**Step 3.2 — see it discovered.**

```bash
python -m sources providers
```

`my_csv: slo` appears in the list. If it does not: the file must live in
`sources/providers/` and define `PROVIDER` at module level.

**Step 3.3 — feed it data.** Create `team_slos.csv`:

```text
service,slo,target_pct,sli_pct
Order API,availability,99.9,99.95
Checkout,availability,99.5,99.55
```

**Step 3.4 — fetch.** Create `csv_source.json` …

```json
{"provider": "my_csv", "path": "team_slos.csv"}
```

… and run:

```bash
python -m sources fetch --kind slo --config csv_source.json --output my_slo.json
```

**Step 3.5 — into the report.** Open `demo/solution_alpha.json` and set
`"slo": "my_slo.json"` (or add the field to your own solution config).
Then render:

```bash
python -m portfolio demo/solution_alpha.json --output report.html --browser
```

The section **Service Levels & Error Budgets** now shows your CSV rows —
status and error budget were derived centrally, and the *Data source*
column says `my_csv:team_slos.csv`. Your source is attached.

---

## 4. A REST system instead of a file?

Same pattern; only `fetch()` changes. The shared helper handles HTTP,
auth and error mapping:

```python
from sources.http import bearer, get_json, token_from_env

def fetch(self, kind, config, log):
    headers = bearer(token_from_env(config, "MY_SYSTEM_TOKEN"))
    data = get_json(config["base_url"] + "/api/slos", headers, "MySystem")
    return [SloRecord(service=e["name"], slo=e["goal"],
                      target_pct=e["target"], sli_pct=e["current"],
                      source="my_system") for e in data]
```

Three rules for REST providers:

- **Tokens only from environment variables** (`token_from_env`) — never
  in configs, never in logs. The GUI/CLI never store them.
- `get_json` maps errors for you: a 401/403 message points the user to
  the possibly missing API approval **and to the file path as fallback**.
- **Test with mocks**, not against the live system: copy the
  request-recorder pattern from `tests/sources/unit/test_rest_providers.py`
  — it patches `sources.http._urlopen` and asserts URLs, headers and
  your translation math.

---

## 5. Swapping a source

Swapping means: **change the fetch config, nothing else.** Say Prometheus
approval has not arrived yet, so you start with the CSV …

```json
{"provider": "my_csv", "path": "team_slos.csv"}
```

… and the day the approval lands, the same file becomes:

```json
{"provider": "prometheus", "base_url": "https://prom.intern",
 "services": [{"service": "Order API", "slo": "availability",
               "target_pct": 99.9,
               "sli_query": "avg_over_time(up[30d])", "scale": 100}]}
```

Re-run the same `fetch` command; the register keeps its name; the
solution config and the report do not change at all. Only the *Data
source* column now reads `prometheus:prom.intern` — provenance stays
visible, judgement rules stay identical.

---

## 6. Combining two sources

A config may hold a `sources` list; the records merge into **one**
register, each row keeping its origin:

```json
{"sources": [
  {"provider": "prometheus", "base_url": "https://prom.intern",
   "services": [{"service": "Order API", "slo": "availability",
                 "target_pct": 99.9,
                 "sli_query": "avg_over_time(up[30d])", "scale": 100}]},
  {"provider": "my_csv", "path": "team_slos.csv"}
]}
```

Typical use: most services live in monitoring, two legacy services only
in a spreadsheet — one register, one report section, per-row provenance.

---

## 7. Managing sources day to day

- **Inventory:** `python -m sources providers` is the authoritative list —
  a new provider file appears automatically, a deleted one disappears.
- **Tokens:** one environment variable per system
  (`PROMETHEUS_TOKEN`, `GITHUB_TOKEN`, `GITLAB_TOKEN`, `SONAR_TOKEN`,
  your own via `token_env`). Never store tokens in configs or code.
- **Conventions:** one file per source; providers translate, they never
  judge (status/tier rules live in `portfolio/slo_config.py` and
  `portfolio/dora_config.py`); records without a measured value carry
  `None`, not a guess.
- **Errors:** a failing REST source names the host and, on 401/403, the
  approval hint — until approval arrives, ship the same data via `file`
  or `csv`.
- **Tests:** give your provider a small test file next to
  `tests/sources/unit/test_csv_provider.py` — happy path, one broken
  input, and the error message a colleague will actually read.

---

## 8. Checklist for a new source

1. One file in `sources/providers/` with `provider_id`, `kinds`,
   `fetch()`, `PROVIDER`.
2. `fetch()` returns normalised records; unknown values are `None`;
   every record sets `source`.
3. No judgement in the provider.
4. Tokens via `token_from_env`; nothing secret in logs or configs.
5. `python -m sources providers` lists it.
6. A fetch writes a register; the report renders it.
7. Mock-based tests are green.
8. Swapping back to `file`/`csv` still works — that is your fallback
   while approvals are pending.
