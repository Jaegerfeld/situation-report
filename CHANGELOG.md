# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.22.0] – 2026-09-03

### Fixed
- **Release bundles were missing the `sources` package** — in v0.21.0,
  clicking *Solutions & Portfolios* (and every other GUI that imports
  the portfolio module) failed with "No module named 'sources'": the
  package introduced with C1/C2 had not been added to the copy lists in
  the release workflow. Both platform lists now include it, and two
  regression tests guard the whole failure class: every top-level
  package of the repo must appear in both release copy lists, and a
  mini-bundle built exactly from those lists must import every GUI
  entry point in an isolated subprocess (both tests verified to fail
  against the broken v0.21.0 state).

### Added
- Portfolio: **strategic themes & integrated roadmap** (roadmap B7,
  VSC-2 from the Wolfsburg workshop) — `"themes": "themes.json"` (new
  module `portfolio/themes_config.py`, schema v1: themes; epics with
  train, horizon P1·P2·Y1·Y2·Y3 near-granular/far-coarse, status,
  theme link). **Orphan detection in both directions**: a theme no epic
  pays into is flagged red as *declared & forgotten* (judged
  portfolio-wide), an epic with an **empty** theme is a *zombie
  initiative* — while a typo in the reference is a validation error,
  not a silent zombie. The report renders the theme table, the roadmap
  matrix (trains × horizons, zombies red) and the zombie list (HTML +
  PDF); the conference pre-read carries the view as Input 4. Roadmap
  epics flow into D2 snapshots — the delta briefing gains the section
  *Roadmap epics (updated roadmaps)* with multi-field changes (horizon
  shifts, status changes; a lost theme reads `→ zombie`, worsened). The
  demo scenario ships `themes_alpha/beta.json` (orphan theme "Green
  operations", zombie EP-A9; in the delta EP-A9 loses its theme and
  EP-B2 moves P2 → P1); manual section 5.15 in all five languages;
  one-pager (DE+EN).
- Portfolio: **flow-problem backlog & conference pre-read** (roadmap B6,
  VSC-1 from the Wolfsburg workshop) — a solution config can reference
  the Value-Stream Conference's impediment backlog
  (`"flow_problems": "flow_problems.json"`; new module
  `portfolio/flow_problems_config.py`, schema v1: status
  open/committed/resolved/dropped, affected value_streams with *derived*
  cross-VS, raiser, owning team, raised_on, a people-maintained
  `conferences` counter, resolution_commitment, follow_up_pi). The
  workshop pattern "logged, never mitigated, back next PI" becomes
  measurable: unresolved problems seen in ≥ 3 conferences sort first
  with a red counter. New report section (HTML + PDF,
  portfolio-aggregated) plus the **conference pre-read**
  (`--conference FILE [--conference-date]`): a light, printable page
  bundling the meeting inputs — current data, impediment backlog with
  ROAM/dependencies, business objectives (capabilities + SLOs); the
  integrated roadmap view joins with B7. The demo scenario ships
  `flow_problems_alpha/beta.json` (FP-A1/FP-B1 survive 3 resp. 4
  conferences, FP-B1 cross-VS); manual section 5.14 in all five
  languages; one-pager (DE+EN). Roadmap: B6/B7 sections folded in from
  PR #149 (closed there due to conflicts).

## [0.21.0] – 2026-09-03

### Added
- **Sources tutorial + management chapter** — a full step-by-step
  tutorial "Attaching your own data source" written for developers who
  have never attached a source: builds a CSV provider from zero against
  the demo scenario (no external systems needed), then covers the REST
  pattern, swapping (config-only), combining and day-to-day management —
  every step with an example. Available on the docs site
  (Tutorials → Attach a data source, en+de) and as PDFs
  (`sources_Tutorial_DE/EN.pdf`, new generator
  `docs/generate_sources_tutorial.py`). The get_data manual gains
  chapter 3 "Managing metric sources" in all five languages (FAQ/glossary
  renumbered). The tutorial's reference solution ships as a real
  provider: `csv` (SLO records from CSV incl. German-Excel semicolons,
  decimal commas and BOM).
- **External metric sources + SLO/DORA views** (roadmap C1/C2) — new
  pluggable `sources` framework: normalised record contracts (SLO, DORA,
  quality) decouple the report from any vendor; providers are
  exchangeable, **combinable** (several sources merge into one register,
  each row keeping its origin) and easy to extend (a new source is one
  file in `sources/providers/` with a `PROVIDER` object — auto-discovered,
  ~30-line recipe on the module page). Shipped providers: `file`
  (universal path, no API approval needed), `prometheus` (C1 reference,
  SLO/SLI via instant query), `github` (C2 reference per Robert — DORA
  derived from deployments/PRs/incident issues with documented,
  configurable approximations), `gitlab` (native DORA API, second
  reference), `sonarqube` (quality measures). Tokens only via environment
  variables, never stored or logged. CLI: `python -m sources fetch|
  providers`. The report gains two sections via the new config fields
  `slo`/`dora`: **Service Levels & Error Budgets** (central budget rule,
  breached first) and **Delivery Performance (DORA) & Code Quality**
  (per-metric tiers at the published DORA thresholds, unit tier = worst
  metric; quality table below) — HTML and PDF, portfolio-aggregated with
  Solution column. The demo scenario ships `slo_*/dora_*.json` (Beta's
  sync API breached, ART Beta-3 low tier, coverage 31 %, rating D);
  manual section 5.13 in all five languages; one-pager (DE+EN).
- **get_data implemented** (roadmap C3) — two equal acquisition paths for
  Jira data, ending in the same JSON `transform_data` consumes. Path 1,
  REST fetch (`python -m get_data fetch`): API v3 (`POST /search/jql`,
  cursor pagination) and v2 (`GET /search`, offset pagination) with
  `expand=changelog`, auth for Jira Cloud (Basic: e-mail + API token) and
  Server/DC (bearer PAT), sequential paging, de-duplication, safety cap;
  the token comes only from an environment variable (default `JIRA_TOKEN`),
  is never stored and never logged; 401/403 errors point to the possibly
  missing API approval and to the manual path as fallback. Path 2, manual
  export (unchanged) plus a validator (`python -m get_data check`) that
  catches missing required fields, missing changelog, duplicates, and
  forgotten follow-up pages (total > issues in file). GUI
  (`python -m get_data` or the launcher's Get Data card, now launchable):
  both paths as a mode toggle, fetch/check in background threads, DE/EN.
  A contract test guarantees a fetched file and a manual export of the
  same data are processed identically; manual chapter 2 in all five
  languages; one-pager (DE+EN).

## [0.20.0] – 2026-09-03

### Added
- Portfolio: **delta briefing** (roadmap D2, deterministic core) — new CLI
  flags on `python -m portfolio`: `--snapshot FILE` (with `--as-of`) freezes
  the computed report state (metrics per unit and pooled, source confidence,
  all five governance registers) into a schema-v1 JSON (new module
  `portfolio/snapshot.py`); `--delta PREV NOW` (no config needed, new module
  `portfolio/delta.py`) compares two snapshots and answers "what changed?":
  metric deltas at display precision, throughput in the period, confidence
  transitions per source, per register added/removed entries and status
  transitions (worsenings first, red) plus newly overdue items judged
  against each snapshot's as-of date. Output as self-contained HTML page,
  Markdown file, or Markdown to stdout; a delta with no changes says so
  explicitly. Deliberately deterministic — the Markdown is the input
  contract for the optional LLM narration (D2 part 2, not built yet). The
  demo scenario ships `snapshot_prev.json`/`snapshot_now.json` (the same
  world two weeks earlier: fewer completed items, Beta-3 confidence still
  medium, AD-1 only at risk, BR-2 absent, runway gap and assumption AS-B1
  not yet overdue); manual section 5.12 in all five languages.
- Portfolio: **delta briefing in the GUIs** — the Solutions & Portfolios
  window gains *Save snapshot …* (freezes the currently configured
  solution/portfolio to a JSON file, suggested name with today's date) and
  *Delta briefing …* (pick the earlier and the later snapshot, briefing
  opens in the browser); labels in all five languages. The test-data
  generator's demo-portfolio section gains *Open Delta Briefing*, rendering
  the scenario's shipped `snapshot_prev/now.json` pair with one click.
- Docs: **feature one-pagers** — every implemented feature now gets a
  one-page PDF (DE+EN) introducing the new function
  (`docs/generate_feature_onepagers.py` → `docs/onepager/`); first one:
  the delta briefing (incl. the GUI path).

## [0.19.0] – 2026-09-03

### Added
- Testdata generator: **demo-portfolio section in the GUI** — the portfolio
  scenario is now reachable without the command line: a *Generate Demo
  Portfolio…* button builds the complete scenario (2 solutions × 3 ARTs with
  all artifacts and governance registers) into a user-chosen folder (the
  seed field is honoured, default 42), and *Open Portfolio Report* renders
  the portfolio report and opens it in the browser. Two clicks from empty
  folder to a full portfolio evaluation; generation runs in a background
  thread with progress bar and log output, labels in DE/EN.
- Portfolio: **decision / assumption log** (roadmap B4) — a solution config
  can reference a lightweight ADR-style log
  (`"decisions": "decisions.json"`; new module
  `portfolio/decision_config.py`, schema v1: id, kind decision/assumption,
  title, status, owner, logged_on, review_by, supersedes, notes). Decisions
  carry proposed/accepted/superseded, assumptions open/confirmed/invalidated
  — the parser enforces the matching status set and validates that
  `supersedes` names an entry of the same log. The report renders the table
  below the dependency heatmap (PDF: own page): an open assumption whose
  `review_by` date has passed sorts first with a red "review due" cell (the
  hook for red-team/premortem sessions); the title counts
  decisions/assumptions/due-for-review. A portfolio aggregates
  member-solution logs with a Solution column; owners are teams, not
  persons; broken files are logged and skipped. The demo scenario ships a
  log per solution (three decisions, two assumptions; Alpha's stage-map
  decision supersedes an older one, Beta's open assumption is past its
  review date); manual section 5.11 in all five languages.
- Portfolio: **dependency / integration heatmap** (roadmap B5) — a solution
  config can reference a dependency register
  (`"dependencies": "dependencies.json"`; new module
  `portfolio/dependency_config.py`, schema v1: id, title, from, to, status
  blocked/at_risk/on_track/done, due, notes). The report renders a heatmap
  plus a detail table below the NFR dashboard (PDF: own page): the heatmap
  counts open dependencies (status ≠ done) per from/to pair with each cell
  coloured by its most urgent status; the table sorts blocked first, and a
  dependency whose due date has passed while not done renders as overdue
  (red date cell); the title counts blocked/at-risk/overdue. The target (to)
  is deliberately not validated against the member list — integration points
  may name another solution's ART, a vendor, or an external system, so
  cross-solution dependencies become visible in the portfolio report. Broken
  files are logged and skipped. The demo scenario ships a register per
  solution (five dependencies; Alpha-1 → Alpha-3 blocked and overdue,
  Beta-1 → Alpha-1 as a cross-solution integration); manual section 5.10 in
  all five languages.
- Portfolio: **capability map & health** (roadmap B1) — a solution config can
  reference a capability map (`"capabilities": "capabilities.json"`; new
  module `portfolio/capability_config.py`, schema v1: id, title, health
  healthy/at_risk/critical, arts, owner, assessed_on, notes). The report
  renders the table below the quality table (PDF: own page): critical
  capabilities sort first with coloured health cells; a capability with no
  contributing ART is flagged as **uncovered** (business value nobody
  delivers); an ART name that is not among the solution's members produces a
  drift warning in the log. Health is assessed by people in PI
  planning/review; the capability map (business capabilities) is deliberately
  not the stage_map (workflow stages). A portfolio aggregates member-solution
  maps with a Solution column; owners are teams, not persons. The demo
  scenario ships a map per solution (six capabilities; Beta's data-insights
  capability critical, one Alpha capability uncovered); manual section 5.9 in
  all five languages.
- Portfolio: **NFR / architecture-runway dashboard** (roadmap B2) — a solution
  config can reference an NFR register (`"nfr": "nfr.json"`; new module
  `portfolio/nfr_config.py`, schema v1 with `nfrs` — id, title, target,
  actual, status met/at_risk/violated — and `runway` — id, title, status
  in_place/building/gap, needed_by). The report renders both tables below the
  ROAM board (PDF: own page): violated NFRs and gaps sort first with coloured
  status cells; a runway element whose needed_by has passed while not in place
  renders as overdue (red date cell); the title counts violated/at-risk NFRs
  and gaps/overdue elements. Statuses are assessed by people in PI
  planning/review — the tool does not compute target vs. actual. A portfolio
  aggregates member-solution registers with a Solution column; owners are
  teams, not persons; broken files are logged and skipped. The demo scenario
  ships a register per solution (six NFRs, four runway elements; Beta's API
  NFR violated, one overdue gap); manual section 5.8 in all five languages.
- Portfolio: **ROAM risk board** (roadmap B3) — a solution config can
  reference a risk register (`"risks": "risks.json"`; new module
  `portfolio/risks_config.py`, schema v1: id, title, roam, owner, impact,
  status_since, notes). The report renders the board below the quality table
  (PDF: own page): rows grouped in R-O-A-M order with coloured category and
  impact cells; an *owned* risk older than 30 days gets a red aging highlight
  in its Since cell; the title counts total/owned/aging risks. A portfolio
  aggregates the registers of all member solutions and adds a Solution column.
  Owners are teams, not persons. Missing or invalid risks files are logged and
  skipped — governance data never breaks the flow report. The demo scenario
  now ships a register per solution (nine risks, two deliberately aging);
  manual section 5.7 in all five languages.
- Testdata generator: **portfolio scenario** (`--scenario portfolio`) — one
  command generates a complete, consistent demo portfolio: two solutions with
  three ARTs each, including every artifact of the processing chain (workflow
  files, raw Jira JSON, IssueTimes/CFD/Transitions workbooks, solution configs,
  portfolio config, PI config, README). Solution Beta carries its own
  `stage_map` (schema 2); the data window is placed relative to the generation
  date so the quality traffic light rates the sources as current. Built-in
  stories: ART Alpha-3 as cycle-time outlier (comparison highlighting),
  ART Beta-3 as weak source (no CFD, few First Dates, 60-day-old data →
  confidence `low`), Solution Beta pooling via custom stage map. Deterministic
  per seed; `--workflow` is now only required without `--scenario`.
  New module `testdata_generator/scenario.py` with
  `build_portfolio_scenario()`; manual chapter 5b in all five languages.

---

## [0.18.0] – 2026-09-02

### Added
- Portfolio: **data-quality / confidence flag per source** (roadmap A1) — the
  report shows a "Data Quality per Source" table below the management summary
  (HTML) and as page 2 of the PDF: records, share of issues without a First
  Date, open share, CFD present, data freshness, and a traffic-light
  confidence (high/medium/low) with documented thresholds. Pooled mode
  assesses each member ART during loading (no second file pass); comparison mode
  assesses each unit.
- Portfolio: **management-summary extension** (roadmap A2) — two new columns
  for the end-to-end lead time (Created → Closed, median and 85th percentile;
  in pooled mode the solution lead time across all ARTs), a member **share**
  column in the quality table, and the **coverage ratio** ("x/y sources
  delivered data") in its title.
- Portfolio: **outlier highlighting in the comparison summary** (roadmap A3) —
  Median-CT and 95th-percentile cells are marked red when they exceed 1.5×
  the column median (three rows minimum; constants documented).
- Portfolio: **configurable canonical stage map** (roadmap A4) — an optional
  `stage_map` block in the solution config defines custom canonical stages
  (ordered source-stage assignment plus explicit `first_stage`/`closed_stage`
  markers) for pooling heterogeneous workflows. Without the block the fixed
  three-group mapping is unchanged; v1 config files load as before, new files
  write `"schema": 2`.
- Portfolio: 15 CLI unit tests (`portfolio/cli.py` coverage 0 → 100 %).
- Simulate GUI: language selection on par with the other modules — five
  languages (de/en/ro/pt/fr) via a flag button (top right), replacing the former
  de/en combobox, with full RO/PT/FR translations and per-language user manuals.
- Simulate GUI: shared project-template mode — a **Templates** menu (Save/Load)
  that stores the ten form fields and the language via `project_template`
  (new `MODULE_SIMULATE` section) and restores them, interoperable with the
  other modules' templates.

### Security
- transform_data: XLSX outputs are hardened against **formula injection**
  (CWE-1236) — strings with a leading "=" from Jira free-text fields are
  stored as text, never as live formulas; values stay byte-identical.
- pypdf dependency floor raised to >= 6.16.1 (15 known CVEs/PYSECs below).
- CI quality gate now runs **bandit** (medium+ severity) and **pip-audit** on
  every pull request; coverage is enforced with fail_under = 80.

### Fixed
- Simulate manual (all five languages): the cover page's dark-blue background
  bled through every page, making the body text hard to read. The manual now
  switches to the white "normal" page template after the cover, like the other
  module manuals.

---

## [0.17.2] – 2026-07-02

### Fixed
- Simulate: in the Monte-Carlo "days to finish" report the percentile labels
  (50/75/85/95 %) overlapped and became unreadable when two percentiles fell
  close together. The labels are now staggered across several rows above the
  chart, each still directly above its own reference line.

---

## [0.17.1] – 2026-07-01

### Added
- Simulate: forecast "how many items by a fixed target date" — a `--target-date`
  CLI option and a GUI field (alternative to `--horizon`); the report and the
  scope-confidence gauge frame the result around that date.

---

## [0.17.0] – 2026-07-01

### Added
- Simulate module: a throughput-based Monte-Carlo forecast (standard library
  only, no numpy/pandas). Answers "how many items in N days?" (capacity) and
  "when will a backlog of N be done?" (date, with optional scope growth via a
  split rate), and reports exceedance percentiles with 85/75/50 % reference
  lines. Available as a CLI (`python -m simulate <IssueTimes.xlsx> …`) and a
  tkinter GUI; the empirical distribution includes zero-throughput days so the
  forecast is not biased upward. With a backlog given, a scope-confidence gauge
  answers "will we finish the scope by the horizon date?" from the same runs.
- Code-quality gate: Ruff (lint, import order, bugbear, pyupgrade, complexity)
  and mypy (typed analytics core) now run in CI via a new `Quality` workflow,
  on every pull request and on pushes to `main`. The same checks run in the
  git pre-commit hook (`python scripts/setup_hooks.py` to install). Ruff and
  mypy versions are pinned in `pyproject.toml` so local, hook, and CI agree.
- Packaging-consistency test: every module the launcher marks as available is
  asserted to appear in the release and dev-build bundle copy lists, so a
  launchable module can no longer be left out of the build.
- Simulate documentation: mkdocs module page (en+de), an architecture entry, and
  a 5-language user manual (DE/EN/RO/PT/FR), plus a hosted-manual "?" button in
  the GUI.
- Portfolio manual: added the missing GUI screenshot in all five languages.

### Fixed
- Helper and Testdata Generator: an error raised during a background task could
  itself crash with a `NameError` instead of being logged, because the deferred
  log callback referenced the exception variable after Python had cleared it.
  The message is now formatted before the callback is scheduled, so the real
  error is shown.

---

## [0.16.0] – 2026-06-23

### Added
- Solutions & Portfolios GUI: brought in line with the other modules — a
  calendar date picker for the From/To fields, language switching via the flag
  button, and a Terminology selector (SAFe/Global, stored in the config and
  applied to the report) replacing the framework dropdown.
- Process Flow: a toggle to show or hide the edge (transition/time) labels in
  the Process Flow: Transitions and Process Flow: Time diagrams. On by default —
  via the GUI checkbox, the `--hide-edge-labels` CLI flag, or the
  `show_edge_labels` template field.
- Flow Load: each stage's box can be drawn with a width proportional to the
  number of issues in that stage, so the mass of open work is visible at a
  glance. Optional and on by default — toggle via the GUI checkbox, the
  `--flat-box-width` CLI flag, or the `proportional_box_width` template field.

### Fixed
- Flow Distribution "stage prominence" pie counted the workflow's terminal
  Done stage. Because a closed/last stage keeps accumulating time as an issue
  ages, it would eventually dominate without any business meaning — and this
  affected open issues resting in Done as well, not only closed ones. The
  terminal Done-group stage(s) are now excluded from prominence for every issue.

---

## [0.15.0] – 2026-06-22

### Added
- New **portfolio** module ("Solutions & Portfolios") for aggregated flow
  reports across several ARTs. A *solution* groups configured ARTs (by
  referencing their build_reports templates or IssueTimes files); a *portfolio*
  groups saved solution templates (Portfolio ▸ Solutions ▸ ARTs). Two report
  modes: **pooled** (the group treated as one system) and **comparison**
  (units side by side — ARTs for a solution, solutions for a portfolio). The
  report covers Flow Velocity, Flow Time, Flow Distribution and CFD (plus Flow
  Load in comparison), preceded by a management-summary table (items, completed,
  open/WIP, cycle-time percentiles and the target-CT share). CFD is pooled
  across differing ART workflows via a shared canonical stage mapping
  (To Do / In Progress / Done). Output as self-contained HTML or multi-page PDF.
- A tkinter manager GUI (`python -m portfolio`) to create/edit solutions and
  portfolios, plus a matching CLI (`python -m portfolio <config.json>`).
- The launcher entry screen is now split: **Large Solutions & Portfolios** on
  the left, the existing ART/team-group tools on the right.
- A five-language user manual for the new module.

---

## [0.14.4] – 2026-06-22

### Fixed
- The testdata generator's `triangle` and `flat_triangle` patterns (and the
  normal dwell chain for incomplete issues) could produce status transitions
  far beyond `--to-date`. With a rising cycle time wider than the
  `from_date … to_date` window, completed issues were dated years into the
  future (e.g. a 2023–2025 range trailing off, thinned out, until 2031),
  making the generated data unusable. Transition timestamps are now capped at
  `to_date`: an issue whose cycle time does not fit the window stays *in
  progress* at the stage it had reached, matching the manual's definition of
  `--to-date` as the latest transition date. The cluster/batch patterns were
  already clamped and are unaffected.

---

## [0.14.3] – 2026-05-23

### Fixed
- The transform_data user manual was missing the workflow marker names
  `<First>`, `<InProgress>` and `<Closed>` in several tables and sentences
  (e.g. "Erster Eintritt in die -Stage", "Marker: , , ."). ReportLab
  silently dropped them because the angle brackets were not escaped. The
  manual generator now escapes them consistently; all five language editions
  of the transform_data manual were regenerated.

---

## [0.14.2] – 2026-05-23

### Fixed
- The transform_data and build_reports user manuals stated the interface
  language could only be switched between German and English. The GUIs
  support five languages — the manuals now list all of them (German,
  English, Romanian, Portuguese, French).

---

## [0.14.1] – 2026-05-22

### Fixed
- The portable release package was missing `project_template.py`, so the
  transform_data, build_reports, helper and testdata_generator GUIs failed to
  start with `ERROR: ... No module named 'project_template'`. The release and
  dev-build workflows now bundle this root-level module.

---

## [0.14.0] – 2026-05-22

### Added
- Data hand-over from `transform_data` to `build_reports`. After a successful
  transformation, a new **Open in build_reports** button writes the three
  generated XLSX files plus the workflow file into a project template and
  launches `build_reports`, which opens with those file fields pre-filled.
  When a project template is loaded in `transform_data`, its build_reports
  settings (PI config, filters, metric selection) are carried over into the
  hand-over so they reach `build_reports` too. build_reports accepts the new
  `--gui-template <path>` flag for this purpose. The hand-over is currently
  one-way (`transform_data` → `build_reports`); other module pairs remain
  future work.

---

## [0.13.0] – 2026-05-17

### Changed
- English is now the **default language** of the project. The mkdocs site
  serves English at the default URLs (unsuffixed `*.md` files), with German
  available as the secondary language (`*.de.md`); nav labels are English
  with German `nav_translations`. The GUI default/fallback language is now
  English (`project_template.DEFAULT_LANGUAGE`, `build_reports` template
  fallbacks). The multilingual selector (DE/EN/RO/PT/FR) is unchanged.
- `SituationReport_Übersicht.md` → `SituationReport_Overview.md`, translated
  to English and brought up to date.
- PDF manual generators default to English (`lang` parameter) for
  consistency; generated output is unchanged (the build iterates all
  languages).

---

## [0.12.1] – 2026-05-17

### Changed
- `testdata_generator`: promoted from **Alpha** to **Beta**. The launcher card
  now shows the orange BETA badge; the module status in the documentation
  (module page, overview, launcher page) was updated accordingly. `helper`
  remains the only Alpha module.

---

## [0.12.0] – 2026-05-17

### Added
- `testdata_generator`: **"Create Report"** button in the GUI. After a
  successful generation the button becomes active; clicking it runs
  `transform_data` and `build_reports` in-process and opens a combined
  report (a single HTML page, all metrics) in the browser. The report
  covers the **entire generated date range** (no date filter).
- `build_reports.cli.render_combined_html(...)`: returns all metrics as a
  single, self-contained HTML page (reuses `_build_combined_html`, now in
  `build_reports/export.py`).

---

## [0.11.0] – 2026-05-16

### Added
- Shared **project template** for all GUI modules (`build_reports`,
  `transform_data`, `testdata_generator`, `helper`). A single JSON file
  holds one section per module, so the pipeline configuration (workflow,
  paths, project, date range) can be saved once and reused in every module
  GUI via the **Templates → Save/Load** menu. Saving from one module
  preserves the other modules' sections.
- Schema v5 (`project_template.py`). Older `build_reports` templates
  (schema v4, flat structure) are still read and transparently interpreted
  as the `build_reports` section.

---

## [0.9.9] – 2026-05-13

### Added
- `testdata_generator`: Four flow anti-pattern shapes from Vacanti/Singh can
  be simulated: **Triangle** (cycle time increases linearly over time),
  **Flat Triangle** (the increase flattens via tanh), **Cluster of Dots**
  (deliveries cluster in the last 2 weeks of each PI, Beta distribution),
  **Batch Transfers** (PI clustering with highly variable cycle time).
  Shape selectable via radio buttons in the GUI or `--pattern` on the
  command line.
- `testdata_generator`: Lognormal cycle-time control via mean and standard
  deviation (`--mean-cycle-days`, `--std-cycle-days`; GUI: input fields +
  sliders). Replaces the previous min/max dwell behaviour when specified.
- `testdata_generator`: PI cycle length configurable
  (`--pi-duration-weeks`, default 12 weeks) for cluster and batch shapes.

### Fixed
- `testdata_generator`: In shape mode all issues were generated as completed
  (0 open issues). Cause: `completion_rate` was rolled twice internally.
  Fix: completion is pre-rolled in `generate()` and passed to
  `_simulate_issue` as the `_prerolled_incomplete` flag.
- `transform_data`, `build_reports`: `openpyxl` wrote Excel files via a
  temporary file + rename — with active OneDrive sync locks this failed
  with `[Errno 22] Invalid argument`. Fix: a BytesIO buffer +
  `path.write_bytes()` bypasses the problematic rename step.

---

## [0.9.8] – 2026-05-09

### Changed
- `transform_data`, `testdata_generator`, `helper`: Replaced the emoji-flag
  cascade in the menu with pixel-drawn `PhotoImage` flag buttons (32×20 px,
  inline, no external files). Windows does not render regional-indicator
  emoji as flags — they appeared as country codes ("DE", "EN"). New
  behaviour: clicking the flag at the top right of the form cycles through
  DE/EN/RO/PT/FR. Now matches the `build_reports` standard.

---

## [0.9.7] – 2026-05-09

### Changed
- `testdata_generator`, `helper`: Unified GUI language selection and manual
  access. Both modules now follow the `build_reports`/`transform_data`
  standard: 5 languages (DE/EN/RO/PT/FR), persisted language selection
  (`prefs.json`), `Help → Manual` menu entry, flag cascade as language
  switcher. `helper` has a manual menu entry for the first time (URL to
  follow once the PDF is created).

---

## [0.9.6] – 2026-05-08

### Changed
- `get_data`: User manual sections 1.3 and 1.5 updated to the current Jira
  Cloud API v3. The new API (`POST /rest/api/3/search/jql`) uses
  cursor-based pagination with `nextPageToken` instead of `startAt`. Both
  variants are explained: v3 (new, recommended) and v2 (legacy, still
  supported). `startAt` is no longer available in the new v3 endpoint.

---

## [0.9.5] – 2026-05-08

### Added
- `get_data`: New user manual (DE + EN) — describes the manual export of
  real Jira data via the REST API: creating an API token, curl queries,
  required fields, pagination beyond 1,000 issues, deriving the workflow
  file.
- `launcher`: "Open manual" button in the Get-Data workaround dialog —
  opens the new get_data user manual directly in the browser (DE/EN
  depending on language).

### Changed
- `testdata_generator`: Chapter 6 (Jira Cloud export) removed from the user
  manual — the content belongs to `get_data`. The manual now has 7
  chapters; cross-references point to the new Get-Data manual.
- `modules/get_data`: Module documentation updated with workaround steps and
  links to the new user manual.

---

## [0.9.4] – 2026-05-07

### Fixed
- `build_reports`: Flow Time method B computed cycle time incorrectly too
  high when `closed_stage` is not the last stage in the workflow (e.g. ART
  workflows with "Completed" as the closed stage and "Done" as the last
  stage). Cause: the carry-forward of the closed stage (time since entering
  Closed until today) was included in the stage-minutes sum and produced a
  straight line from top-left to bottom-right in the scatter plot. Fix:
  `_cycle_days_method_b` now sums only stages up to but excluding the
  closed stage.
- `testdata_generator`: Completed issues were created uniformly across
  `[from_date, to_date]`; late creation dates caused issues to close after
  `to_date` and be filtered from the scatter plot (right-censoring
  artefact). Fix: creation date for completed issues restricted to
  `[from_date, latest_start]`, where `latest_start` leaves enough buffer
  for the maximum cycle time.

---

## [0.9.3] – 2026-05-04

### Added
- `testdata_generator`: User manuals (DE + EN) as PDF — 8 chapters
  including a complete Jira Cloud export guide (API token, curl,
  pagination, JSON merger) and an ART_A walkthrough example.
  `generate_testdata_generator_manual.py` as a ReportLab script for
  reproducibility.
- `testdata_generator` GUI: "Open user manual" menu entry (DE/EN)

### Fixed
- CI: The coverage badge is now updated automatically via PR instead of
  pushing directly to main (branch protection blocks direct push).
  `coverage.yml` creates a temporary branch + auto-merge PR.

### Changed
- All manuals (launcher 5×, transform_data 2×, build_reports 2×)
  regenerated for version 0.9.3.

---

## [0.9.2] – 2026-05-03

### Added
- `launcher`: The Get-Data card now shows a **How to** button instead of
  just "(coming soon)". Opens a dialog with the 3-step workaround: export
  Jira JSON → Helper → Transform Data. All 5 languages.

---

## [0.9.1] – 2026-05-03

### Fixed
- Windows: BAT start files now show a clear German error message with a
  3-step solution when the embedded `python.exe` is blocked by Windows
  Defender (Mark-of-the-Web on ZIP downloads from the internet). Previously
  the cryptic Microsoft Store Python message appeared.
- `release.yml`: Synced with `dev-build.yml` — `helper` and
  `testdata_generator` are now also included in official releases;
  `TestdataGenerator.bat`, `Helper.bat`, `TestdataGenerator.sh/.command`,
  `Helper.sh/.command` are now generated.

---

## [0.9.0] – 2026-05-03

### Added
- `helper`: New module with a JSON merger tool — merges multiple Jira REST
  API JSON files into a single one. Deduplication by issue ID
  (configurable). Output can be processed directly by `transform_data`.
  GUI + CLI + double-click starter.

### Fixed
- `helper`: Added the missing `_browse_output` method — the file dialog for
  choosing the output file could not be invoked (`AttributeError`).

### Changed
- Docs: Feature overview and process PPTX updated to v0.9.0

---

## [0.8.5] – 2026-05-02

### Added
- `testdata_generator`: New module — generates synthetic Jira issue JSON
  files in Jira REST API format. Configurable via GUI or CLI (workflow
  file, project key, issue count, date range, completion rate, backflow
  probability, seed). Output can be processed directly by `transform_data`.

### Changed
- `launcher`: Global app badge raised from **ALPHA** (red) to **BETA**
  (orange), since the core modules `build_reports` and `transform_data`
  have reached beta maturity.
- `launcher`: Each module card now shows its own maturity badge:
  `transform_data` and `build_reports` → **BETA** (orange),
  `testdata_generator` → **ALPHA** (red); planned modules without a badge.

### Fixed
- `flow_load`: WIP count switched to the current stage position —
  `open_count` now matches boxplot annotations and IssueTimes (PR #62)

---

## [0.8.4] – 2026-04-30

### Added
- `launcher`: User manuals in Romanian (RO), Portuguese (PT) and French
  (FR) — language-specific PDF URLs in the launcher (PR #55)

### Fixed
- `build_reports`: Templates could no longer be loaded — replaced the
  global MouseWheel handler with hover-based binding; added `parent=self`
  to all file dialogs (PR #56)
- `flow_load`: Stage filter changed from `!= GROUP_DONE` to an explicit
  allowlist `in (GROUP_TODO, GROUP_IN_PROGRESS)`; comments added (PR #61)

### Changed
- Docs: Feature overview and process PPTX updated to v0.8.4 (PR #58)

---

## [0.8.3] – 2026-04-30

### Fixed
- `build_reports`: Scrollable form so the log area stays visible on FullHD
  (PR #53)

---

## [0.8.2] – 2026-04-30

### Fixed
- Initial window height capped to the screen size (FullHD fix) (PR #52)

---

## [0.8.1] – 2026-04-30

### Added
- `launcher`: Background update check with a notification banner (PR #51)

---

## [0.8.0] – 2026-04-30

### Added
- `launcher`: Central launcher GUI (`python -m launcher`) to start all
  modules with language selection, ALPHA badge and manual button (PR #48)
- Double-click start scripts (`SituationReport.bat/.sh/.command`) in the
  project root (PR #49)

### Fixed
- Corrected the order of Transform Data / Build Reports in the launcher
  (PR #50)

---

## [0.7.0] – 2026-04-30

### Added
- `build_reports`: Process Flow: Time metric — directed graph with average
  dwell time per transition (PR #32)
- CI/CD: GitHub Actions release workflow with a portable Python package for
  Windows, macOS (ARM) and Linux; flag language switcher (PR #34)
- Languages RO, PT, FR in all GUIs (PR #43)

### Fixed
- Flow Load: To-Do issues and Done stages hidden from the boxplot (PR #46)
- CI: Portable Windows package switched to a full CI Python copy (PR #41)
- CI: macOS builds (PyInstaller error, Chrome exclusion) (PR #35 – #37)
- Start scripts renamed: `SituationReport.*` → `BuildReports.*` (PR #42)

---

## [0.5.1] – 2026-04-26

### Fixed
- `process_flow`: Created node merged into the first workflow stage; label
  overflow fixed (PR #31)

---

## [0.5.0] – 2026-04-26

### Added
- `build_reports`: Process Flow metric — directed graph of status
  transitions with a transitions-file picker in the GUI (PR #29, #30)
- Coverage badge and pytest-cov set up (PR #27)

---

## [0.4.1] – 2026-04-26

### Fixed
- Version number corrected to 0.4.1 in all manuals (PR #10)

---

## [0.4.0] – 2026-04-26

### Added
- DE/EN language selection in GUIs with persisted preference (flag menu)
- Bilingual PDF manuals (DE + EN)
- EN docs, feature-overview PPTX and process capability map

### Changed
- Pre-commit hook now automatically updates the version number in the
  README badge

---

## [0.2.0] – 2026-04-25

### Added
- SemVer versioning introduced (starting with v0.2.0)
- `build_reports`: Flow Distribution (3 charts + Stage Prominence)
- `build_reports`: Exclude zero-day issues (configurable threshold)
- `build_reports`: Configurable target cycle time for Flow Time
- `build_reports`: Collision-free reference-line annotations (label
  repulsion)
- `build_reports`: Issue count per stage in the Flow Load chart
- `build_reports`: Legend for Flow Load reference lines
- `build_reports`: CFD trend lines at visual stage boundaries
- `build_reports`: "Save as PDF" button → "Export reports"
- Help menu with manual link in `build_reports` and `transform_data`
