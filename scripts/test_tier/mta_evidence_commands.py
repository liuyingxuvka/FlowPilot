"""Build exact file-owned commands for declared MTA evidence."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import hashlib
from pathlib import Path
import sys

from .command_builders import TierCommand, _py


ROOT = Path(__file__).resolve().parents[2]
SIMULATIONS = ROOT / "simulations"


@lru_cache(maxsize=4)
def mta_evidence_commands(
    base_commands: tuple[TierCommand, ...],
) -> tuple[TierCommand, ...]:
    if str(SIMULATIONS) not in sys.path:
        sys.path.insert(0, str(SIMULATIONS))
    from flowpilot_model_test_alignment_common import configure_execution_evidence
    from flowpilot_model_test_alignment_family_plans import (
        build_alignment_plan_entries,
    )
    from flowpilot_model_test_alignment_source_test_evidence import (
        source_test_evidence,
    )

    configure_execution_evidence(
        None,
        declaration_only=True,
        evidence_scope="routine",
    )
    rows = [
        evidence
        for entry in build_alignment_plan_entries()
        for evidence in entry["plan"].test_evidence
    ]
    rows.extend(source_test_evidence())
    from .impact_resolution import _command_direct_inputs, _relative

    direct_inputs = {}
    for command in base_commands:
        try:
            direct_inputs[command.name] = {
                _relative(path)
                for path in _command_direct_inputs(command.command)
            }
        except ValueError:
            direct_inputs[command.name] = set()

    def selects(command: TierCommand, test_name: str) -> bool:
        if "--collect-only" in command.command:
            return False
        explicit_nodes = [
            str(value)
            for value in command.command
            if "::" in str(value)
        ]
        if explicit_nodes:
            return any(test_name in value for value in explicit_nodes)
        filters = [
            str(command.command[index + 1])
            for index, value in enumerate(command.command[:-1])
            if value == "-k"
        ]
        if filters:
            return any(value in test_name for value in filters)
        return True

    by_path: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        path = str(row.path).replace("\\", "/")
        if not path.startswith("tests/"):
            continue
        candidates = [
            command
            for command in base_commands
            if path in direct_inputs[command.name]
            and selects(command, str(row.test_name))
        ]
        if len(candidates) != 1:
            by_path[path].append(str(row.evidence_id))

    commands = []
    for path, evidence_ids in sorted(by_path.items()):
        suffix = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        arguments: list[str] = [
            "scripts/test_tier/mta_evidence_owner.py",
            "--path",
            path,
        ]
        for evidence_id in sorted(evidence_ids):
            arguments.extend(("--evidence-id", evidence_id))
        commands.append(
            TierCommand(
                name=f"mta_evidence_{Path(path).stem}_{suffix}",
                command=_py(*arguments),
                description=(
                    "Execute the exact current MTA evidence functions owned by "
                    f"{path}; zero or duplicate selection blocks."
                ),
                long_running=True,
                background_recommended=True,
                background_stage=4,
            )
        )
    return tuple(commands)
