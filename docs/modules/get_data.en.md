# get_data

Retrieve data from Jira via REST API.

**Status:** planned

---

## Workaround (until the module is available)

Until `get_data` is available, Jira data can be fetched manually.
The Launcher shows a **How to** button on the Get Data card for this purpose.

### Step 1 — Export Jira JSON

Export issues via the **Jira REST API**:

```
https://<jira-host>/rest/api/2/search?jql=project=MYPROJECT&expand=changelog&maxResults=1000
```

!!! info "Pagination"
    Jira returns at most **1,000 issues per request**. For larger projects, multiple pages are needed — proceed to Step 2.

### Step 2 — Merge files (only if you have more than one)

Launch `helper` → add all JSON files to the list → click **Merge**.

Result: a single `merged.json` file, ready for `transform_data`.

→ [helper](helper.md)

### Step 3 — Transform data

Launch `transform_data` → load the merged (or single) JSON file → specify a workflow file → process.

→ [transform_data](transform_data.md)
