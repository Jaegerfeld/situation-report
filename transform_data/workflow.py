from dataclasses import dataclass
from pathlib import Path


@dataclass
class Workflow:
    stages: list[str]               # ordered canonical stage names
    status_to_stage: dict[str, str] # any status/alias -> canonical stage name
    first_stage: str | None         # stage that sets the "First Date"
    closed_stage: str | None        # stage that sets the "Closed Date"
    inprogress_stage: str | None    # stage that sets the "Implementation Date"


def parse_workflow(filepath: Path) -> Workflow:
    """
    Parse a workflow definition file.

    Line formats:
        StageName:Alias1:Alias2   -> canonical stage with optional status aliases
        <First>StageName          -> which stage sets the First Date
        <Closed>StageName         -> which stage sets the Closed Date
        <InProgress>StageName     -> which stage sets the Implementation Date
                                     (defaults to "Implementation" if present)
    """
    stages: list[str] = []
    status_to_stage: dict[str, str] = {}
    first_stage = None
    closed_stage = None
    inprogress_stage = None

    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("<First>"):
            first_stage = line[7:]
        elif line.startswith("<Closed>"):
            closed_stage = line[8:]
        elif line.startswith("<InProgress>"):
            inprogress_stage = line[12:]
        else:
            parts = line.split(":")
            canonical = parts[0]
            stages.append(canonical)
            for name in parts:
                status_to_stage[name] = canonical

    if inprogress_stage is None and "Implementation" in stages:
        inprogress_stage = "Implementation"

    # Validate that marker stages actually exist in the workflow
    for marker, name in (
        ("<First>", first_stage),
        ("<Closed>", closed_stage),
        ("<InProgress>", inprogress_stage),
    ):
        if name is not None and name not in stages:
            raise ValueError(
                f"Workflow-Fehler: {marker}{name} ist kein bekannter Stage-Name. "
                f"Bekannte Stages: {', '.join(stages)}"
            )

    return Workflow(stages, status_to_stage, first_stage, closed_stage, inprogress_stage)
