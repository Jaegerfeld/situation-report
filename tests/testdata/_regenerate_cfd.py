"""Regenerate tests/testdata/ART_A/ART_A_CFD.xlsx from ART_A.json.

Why this file exists
--------------------
Commit f6fb537 (22.04.2026) changed ``transform_data.write_cfd`` from writing
daily *occupancy* snapshots to writing daily *entry counts* -- ``build_reports``
accumulates them into the running total itself. The ART_A fixture was not
regenerated with that commit, so from April to September 2026 every test and
every manual figure that used it ran against data the pipeline no longer
produces. There was no documented regeneration path, which is exactly why the
step was forgotten.

Run it from the repository root::

    ./.venv/Scripts/python.exe tests/testdata/_regenerate_cfd.py

``REFERENCE_DT`` is pinned so the day range of the fixture stays stable across
regenerations. It is the only input that decides the last row; the CFD values
themselves come from ``created``, ``initial_stage`` and ``transitions``.

ART_E has no ``ART_E.json`` in the repository, so its CFD cannot be regenerated
here. It already carries entry-count semantics and needs no fix.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from transform_data.processor import process_issues  # noqa: E402
from transform_data.workflow import parse_workflow  # noqa: E402
from transform_data.writers import write_cfd  # noqa: E402

ART_A = Path(__file__).resolve().parent / "ART_A"

# Pinned so the fixture keeps its day range (02.12.2023 - 15.04.2026).
REFERENCE_DT = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)


def main() -> int:
    workflow = parse_workflow(ART_A / "workflow_ART_A.txt")
    records, unmapped = process_issues(ART_A / "ART_A.json", workflow, REFERENCE_DT)
    if unmapped:
        print(f"Nicht abgebildete Status: {sorted(unmapped)}")
    out = ART_A / "ART_A_CFD.xlsx"
    write_cfd(records, workflow, out, REFERENCE_DT)
    print(f"{len(records)} Vorgaenge -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
