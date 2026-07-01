# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
