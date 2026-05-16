# Modules

| Module | Description | Status |
|--------|-------------|--------|
| [launcher](launcher.md) | Central entry point – launches all modules | available |
| [transform_data](transform_data.md) | Transform raw Jira data into stage-time metrics | available |
| [build_reports](build_reports.md) | Generate metrics and reports | available |
| [helper](helper.md) | Merge JSON files (Jira pagination) | available (Alpha) |
| [testdata_generator](testdata_generator.md) | Generate synthetic test data | available (Alpha) |
| [get_data](get_data.md) | Retrieve data from Jira via REST API | planned |
| [simulate](simulate.md) | Simulations and prediction models | planned |

## Shared project template

`transform_data`, `build_reports`, `testdata_generator` and `helper` share a
common project template: a single JSON file with one section per module. Via
the **Templates → Save / Load** menu the pipeline configuration (workflow,
paths, project key, date range) can be saved once and reloaded in every module
GUI. Saving from one module preserves the other modules' sections. Older
`build_reports` templates (schema v4) are still read.
