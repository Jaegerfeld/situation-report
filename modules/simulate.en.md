# simulate

Monte-Carlo forecast based on historical daily throughput. Answers two questions
probabilistically – without story-point estimation:

- **How many items** will we complete in a given period? (capacity forecast)
- **When will** a backlog of N items **be done**? (date forecast, optionally with
  scope growth via a split rate)
- **Will we finish the scope by date X?** – when `--backlog` is set, the report
  adds a confidence gauge: P(at least the backlog items by the horizon date). This
  is the same value as the exceedance curve evaluated at the backlog size.

Results are shown as exceedance percentiles – e.g. "at least X items with 85 %
confidence" or "by day Y / date Z at the latest" – with reference lines at
85/75/50 %.

## Usage

GUI (no arguments):

```
python -m simulate
```

CLI:

```
python -m simulate ART_A_IssueTimes.xlsx --horizon 84 --backlog 50 \
    --runs 25000 --split-rate 0.1 --seed 1 --output forecast.html
```

| Option | Meaning |
|---|---|
| `--cfd FILE` | Optional CFD file. |
| `--history-days N` | History window length (default 180). |
| `--history-end YYYY-MM-DD` | Exclusive end date (default: today). |
| `--horizon DAYS` | Forecast horizon (default 84). |
| `--backlog N` | Also run the date forecast for N items. |
| `--runs N` | Number of Monte-Carlo runs (default 25000). |
| `--split-rate R` | Expected new items per completed item (scope growth). |
| `--seed N` | Seed for reproducible runs. |
| `--output FILE` | HTML report destination. |

## GUI: language & templates

Like the other module GUIs, simulate supports five languages (German, English,
Romanian, Portuguese, French). The **flag button** at the top right switches the
interface; the choice is stored in `~/.situation_report/prefs.json` and shared
across all modules.

The **Templates** menu saves and loads the current inputs:

- **Save** stores files and parameters together with the language in the shared
  project template (`project_template`, `simulate` section).
- **Load** restores inputs and language. The same template file is shared with
  the other modules – each module only writes its own section.

## Method

Standard library only (no numpy/pandas): the empirical daily-throughput
distribution is built from the history window – **including zero days** – and
resampled across `runs` runs. Inspired by the team's R prototype and by
Daniel Vacanti, *Actionable Agile Metrics for Predictability*.
