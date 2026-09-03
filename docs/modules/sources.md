# sources

Pluggable framework for external metrics (roadmap C1/C2): SLO/SLI data,
DORA delivery metrics and code quality — from **exchangeable, combinable**
sources, into normalised register JSON the portfolio report renders.

**Status:** implemented (alpha)

## Design: three guarantees

1. **Exchangeable** — the report never sees a vendor. Providers translate a
   foreign system into three normalised record contracts (`SloRecord`,
   `DoraRecord`, `QualityRecord`); status/tier judgements happen centrally
   in the registers (`portfolio/slo_config.py`, `portfolio/dora_config.py`),
   so every source is judged by the same rule.
2. **Combinable** — a fetch config may list several sources; their records
   merge into one register, each row keeping its origin (`source` column in
   the report).
3. **Easy to extend** — a new source is ONE file in `sources/providers/`
   defining a `PROVIDER` object; auto-discovery picks it up, no registry to
   edit (see the recipe below).

The file provider is the universal fallback (the C3 principle): any system
can be attached today by exporting the normalised JSON — no API approval
needed.

## Shipped providers

| Provider | Kind | Why this reference |
|---|---|---|
| `file` | slo, dora, quality | Universal path 1 — works without any API access |
| `prometheus` | slo | De-facto OSS monitoring standard (~77 % production use; sits behind most Grafana setups); commercial leaders (Datadog ~24 % APM share, Dynatrace) attach via `file` or a future provider |
| `github` | dora | Robert's pick, largest platform — **no native DORA API**, so the four keys are *derived*: deployments (frequency), latest deployment statuses (CFR), merged PRs (lead time, median created→merged), incident-labelled issues (MTTR). Approximations are documented and configurable (environment, incident label, caps) |
| `gitlab` | dora | The only mainstream system with a **native DORA API** (`/api/v4/.../dora/metrics`, Ultimate tier) — kept as the second reference to prove exchangeability |
| `sonarqube` | quality | De-facto static-quality standard (named by the roadmap): coverage, maintainability rating, critical violations |

Tokens always come from environment variables (`PROMETHEUS_TOKEN`,
`GITHUB_TOKEN`, `GITLAB_TOKEN`, `SONAR_TOKEN`, overridable via
`token_env`), are never stored and never logged; 401/403 errors point to
the possibly missing approval and to the file path as fallback.

## CLI

```bash
python -m sources providers
python -m sources fetch --kind slo --config slo_sources.json --output slo.json
```

A config is one source object — or a combination:

```json
{
  "sources": [
    {"provider": "prometheus", "base_url": "https://prom.intern",
     "services": [{"service": "Order API", "slo": "availability",
                    "target_pct": 99.9,
                    "sli_query": "avg_over_time(up[30d])", "scale": 100}]},
    {"provider": "file", "path": "dynatrace_export.json"}
  ]
}
```

The output is the register JSON the solution config references
(`"slo": "slo.json"`, `"dora": "dora.json"`); the report then renders
**Service Levels & Error Budgets** (breached first, central budget rule:
consumed = (100−SLI)/(100−target), at risk below 25 % remaining) and
**Delivery Performance (DORA) & Code Quality** (per-metric tiers at the
published DORA thresholds, unit tier = worst metric; quality table below).

## Recipe: your own source in ~30 lines

Create `sources/providers/my_system.py`:

```python
from sources.base import KIND_SLO, SloRecord
from sources.http import bearer, get_json, token_from_env

class MySystemSource:
    provider_id = "my_system"
    kinds = (KIND_SLO,)

    def fetch(self, kind, config, log):
        headers = bearer(token_from_env(config, "MY_SYSTEM_TOKEN"))
        data = get_json(config["base_url"] + "/api/slos", headers, "MySystem")
        return [SloRecord(service=e["name"], slo=e["goal"],
                          target_pct=e["target"], sli_pct=e["current"],
                          source="my_system") for e in data]

PROVIDER = MySystemSource()
```

Done — `python -m sources providers` lists it, `fetch` can use it, and it
combines freely with every other source.

## Architecture

```
sources/
├── base.py            Record contracts, provider protocol, auto-discovery
├── http.py            Shared urllib GET + auth headers + error mapping
├── cli.py             fetch (multi-source merge) and providers commands
└── providers/
    ├── file_source.py Universal file path (all kinds)
    ├── prometheus.py  C1 reference (SLO/SLI via instant query)
    ├── github_dora.py C2 reference (DORA derived from GitHub)
    ├── gitlab_dora.py C2 alternative (native DORA API)
    └── sonarqube.py   C2 quality (component measures)
```

Standard library only. The REST providers are fully mock-tested; a live
test against real instances is the remaining practice step (as with
get_data).
