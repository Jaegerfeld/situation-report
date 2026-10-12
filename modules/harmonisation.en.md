# harmonisation

Harmonisation score per end-to-end process: a structured assessment in three dimensions
(**business value · transparency · IT and operations**), stored versioned, one score with
confidence per dimension, rendered as a **decision matrix** for the board. Origin:
roadmap, priority P3.

!!! info "A finding, not a judgement"
    The module recommends nothing — neither *what* to harmonise nor *how deep*. It computes
    the finding and records what the board decided. The judgement line stays with people,
    the same non-feature as the missing recommendation button in the AI layer.

## Start

```bash
python -m harmonisation
```

Opens the GUI: choose a workspace or **create the example**, maintain processes, enter an
assessment, record the decision, generate the matrix.

```bash
python -m harmonisation <folder> --lang en --browser
python -m harmonisation <folder> --example      # write the example workspace and render it
```

| Option | Meaning |
|---|---|
| `--output FILE` | HTML file (default: `<folder>/matrix.<lang>.html`) |
| `--lang de\|en\|ro\|pt\|fr` | matrix language (default: de) |
| `--example` | writes the example workspace into the folder |
| `--browser` | opens the matrix in the browser |
| `--since YYYY-MM-DD` | the **change** since that date instead of the matrix (`<folder>/delta.<lang>.html`) |
| `--delta FOLDER` | change against a second workspace (the earlier state) |
| `--narrate [PROVIDER]` | **AI reading (draft)** below the matrix or the change; default `ollama`, also `claude`, `mock` |
| `--llm-model`, `--llm-base-url` | model or address for `--narrate` (otherwise the provider's defaults) |

## Workspace

One folder with four things, all JSON with a `schema_version`:

```
<folder>/
├── catalogue.json      question catalogue: dimensions → questions (text per language)
├── processes.json      end-to-end processes (id, name, owner, brands)
├── decisions.json      the board's decision per process (optional)
└── assessments/        one file per assessment: process, assessor, date, answers
```

**The catalogue is data, not code.** The bundled example catalogue with 3 × 8 questions
illustrates the structure; your own questions go into the same file. Every
question is phrased so that strong agreement speaks *for* harmonisation — only then can
the values of a dimension be added up.

## Answers and arithmetic

- **Scale per question:** 0 "does not apply" … 4 "fully applies" — and **"unknown" as a
  permitted answer**. A situational picture that cannot show ignorance fakes certainty.
- **Evidence per answer:** documented (document, measurement) · estimated · hearsay.
- **Score per dimension:** mean of the answered questions, 0–100; plus "n of 8 answered".
- **Confidence:** share of documented answers over *all* questions of the dimension — high
  from ⅔, medium from ⅓, otherwise low. "Unknown" lowers the confidence, not the score.
- **Several assessments of the same process:** **median** as the score, **spread**
  (max − min) next to it. Two people who see the same process very differently are a
  finding, not noise to average away.
- **No overall score** across dimensions: three numbers side by side are more honest than
  one that nets three different things.

## The matrix

Rows = processes, columns = dimensions; per cell the score (shades of blue — a finding, not
a traffic light), number of assessments, questions answered, spread, and the confidence as a
traffic-light badge. On the right the columns **the board fills in**: decision (standardise ·
brand-specific · open) and depth in the board's own wording. Colour key and legend come
before the first table. Below, the second reading: every assessment with every answer and
its evidence level.

## Change between two states (step 2)

"What has changed since the last assessment?" — after the delta-briefing pattern.
Assessments are dated, so `--since 2026-09-20` recomputes the earlier state from today's
files; `--delta <folder>` compares against a second workspace. Compared per process and
dimension: **score, confidence, spread and number of assessments** (old → new), plus new
assessments (date only, no names), the board's decisions, processes added or removed. A
changed question catalogue is flagged as a warning — the scores are not comparable then.

- "No changes" is said explicitly.
- **A lower score is not a worsening** but a different finding. The table is ordered by
  process, not by good and bad.
- Decisions without a date count as present in both states; the page counts them.

```bash
python -m harmonisation <folder> --since 2026-09-20 --lang en --browser
```

## AI reading (draft)

`--narrate` (or the checkbox in the GUI) adds a reading below the matrix or the change —
the same pattern as the executive summary of the portfolio reports:

- The model sees **only a contract** with every number of the matrix or the change:
  processes, dimensions, brands, board decisions — **never persons** (owners and
  assessors are structurally absent from the contract).
- Every number in the draft must appear in the contract, otherwise it is discarded
  (retried once).
- The versioned prompt additionally forbids **any recommendation** on what to harmonise
  or how deep — the score is a finding, the judgement rests with the board.
- The draft sits labeled (Art. 50 banner) directly below the table and additionally in
  `<output>.reading.md` for editing; the operator evidence goes to `llm_audit.jsonl` next
  to the output (purpose `p3_reading`).
- If the AI fails, the deterministic page still stands; the command line reports it with
  exit code 3, the GUI in the status line.

```bash
python -m harmonisation <folder> --narrate            # locally via Ollama
python -m harmonisation <folder> --since 2026-09-20 --narrate mock   # stand-in, no model
```

## In the conference pre-read

In the portfolio module a solution carries the optional field `"harmonisation"` with the
**folder** of the workspace (data-sources dialog, tenth field with a folder picker;
"Take from data folder" recognises `registers/harmonisation/` by its catalogue). The
pre-read then shows the matrix as an **annex after input 4** — a board view, deliberately
not a fifth conference input. A missing or inconsistent workspace is skipped with a
warning; the pre-read still stands.

## Deliberately absent

- No harmonisation proposal, no ranking, no recommended depth — not in the AI reading
  either.
- No AI in the core: the computation is deterministic, standard library only. The optional
  AI reading only phrases, labeled as a draft, and computes nothing.
- No overall score.
- No diff at answer level: the matrix's second reading shows every answer; a diff on it
  would be a diff on individual people's statements.

## Tests

```bash
python -m pytest tests/harmonisation/
```
