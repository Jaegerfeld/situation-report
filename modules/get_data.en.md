# get_data

!!! note "Planned"
    This module is not yet implemented. Until it is available, Jira data can be exported manually via the REST API.

Retrieves data from Jira via REST API and produces the JSON export consumed by `transform_data`.

## Manual workaround

Until `get_data` is available, data can be exported manually:

1. **Export Jira JSON** — Export issues via the Jira REST API as JSON (`expand=changelog` is required).
2. **Merge files** — For more than 1,000 issues: use `helper` to merge paginated exports into one file.
3. **Transform data** — Launch `transform_data` with the JSON file.

The complete export process (API token, curl examples, pagination, creating the workflow file) is documented in the user manual.

## User manual

- [get_data Benutzerhandbuch (DE)](../get_data_Benutzerhandbuch.pdf)
- [get_data User Manual (EN)](../get_data_UserManual.pdf)
