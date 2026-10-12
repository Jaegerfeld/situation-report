# harmonisation

Harmonisation score per end-to-end process: a structured assessment in three dimensions
(**business value · transparency · IT and operations**), stored versioned, one score with
confidence per dimension, rendered as a **decision matrix** for the board. Origin:
Wolfsburg workshop 08/2026, priority P3.

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
illustrates the workshop structure; your own questions go into the same file. Every
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

## Deliberately absent

- No harmonisation proposal, no ranking, no recommended depth.
- No AI: standard library only, deterministic, reproducible.
- No overall score.

## Tests

```bash
python -m pytest tests/harmonisation/
```
