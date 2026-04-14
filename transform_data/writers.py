# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       09.04.2026
# Geändert:       14.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Schreibt die verarbeiteten Issue-Daten in drei XLSX-Ausgabedateien:
#   Transitions (chronologische Statuswechsel je Issue), IssueTimes
#   (Verweildauer in Minuten je Stage pro Issue) und CFD (Cumulative Flow
#   Diagram mit täglichen Stage-Belegungszahlen). Alle Ausgaben enthalten
#   fett gedruckte Kopfzeilen.
# =============================================================================

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from .processor import IssueRecord, fmt_dt
from .workflow import Workflow


def _new_wb(headers: list[str]) -> tuple[Workbook, object]:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    return wb, ws


def write_transitions(records: list[IssueRecord], output_path: Path) -> None:
    """
    Write Transitions XLSX.
    One row per transition per issue, sorted by timestamp within each issue.

    Columns: Key | Transition | Timestamp
    """
    wb, ws = _new_wb(["Key", "Transition", "Timestamp"])
    for record in records:
        for t in record.transitions:
            ws.append([t.key, t.label, t.timestamp.strftime("%d.%m.%Y %H:%M:%S")])
    wb.save(output_path)


def write_issue_times(records: list[IssueRecord], workflow: Workflow, output_path: Path) -> None:
    """
    Write IssueTimes XLSX.
    One row per issue with time spent (in minutes) in each workflow stage.

    Columns: Project, Group, Key, Issuetype, Status, Created Date, Component,
             Category, First Date, Implementation Date, Closed Date,
             <stage columns...>, Resolution
    """
    stage_cols = workflow.stages
    header = (
        ["Project", "Group", "Key", "Issuetype", "Status", "Created Date",
         "Component", "Category", "First Date", "Implementation Date", "Closed Date"]
        + stage_cols
        + ["Resolution"]
    )
    wb, ws = _new_wb(header)
    for r in records:
        row = [
            r.project,
            "",
            r.key,
            r.issuetype,
            r.status,
            fmt_dt(r.created),
            r.component,
            "",
            fmt_dt(r.first_date),
            fmt_dt(r.inprogress_date),
            fmt_dt(r.closed_date),
        ] + [r.stage_minutes.get(s, 0) for s in stage_cols] + [r.resolution]
        ws.append(row)
    wb.save(output_path)


def write_cfd(
    records: list[IssueRecord],
    workflow: Workflow,
    output_path: Path,
    reference_dt: datetime,
) -> None:
    """
    Write Cumulative Flow Diagram XLSX.
    One row per calendar day from the earliest issue creation to reference_dt.
    Each stage column contains the count of issues in that stage on that day.

    Columns: Day, <stage columns...>
    """
    if not records:
        return

    stage_cols = workflow.stages
    min_date = min(r.created.date() for r in records)
    max_date = reference_dt.date()

    def stage_at_day(record: IssueRecord, day: date) -> str | None:
        if record.created.date() > day:
            return None
        current = record.initial_stage
        for t in record.transitions[1:]:   # skip "Created" entry
            if t.timestamp.date() <= day:
                # carry-forward: only advance if the transition target is mapped
                mapped_stage = workflow.status_to_stage.get(t.label)
                if mapped_stage is not None:
                    current = mapped_stage
            else:
                break
        return current

    wb, ws = _new_wb(["Day"] + stage_cols)

    current_date = min_date
    while current_date <= max_date:
        counts: dict[str, int] = {s: 0 for s in stage_cols}
        for record in records:
            stage = stage_at_day(record, current_date)
            if stage and stage in counts:
                counts[stage] += 1
        ws.append([current_date.strftime("%d.%m.%Y")] + [counts[s] for s in stage_cols])
        current_date += timedelta(days=1)

    wb.save(output_path)
