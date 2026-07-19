"""Execute one exact file-owned Model-Test Alignment evidence set."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
SIMULATIONS = ROOT / "simulations"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))


def _declared_evidence() -> dict[str, Any]:
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
    return {row.evidence_id: row for row in rows}


class _ExactNameSelection:
    def __init__(self, names: set[str]) -> None:
        self.names = names
        self.counts = {name: 0 for name in names}
        self.definition_locations: dict[str, set[tuple[str, int]]] = {
            name: set() for name in names
        }

    def pytest_collection_modifyitems(self, session, config, items) -> None:
        selected = []
        deselected = []
        for item in items:
            base_name = str(item.name).split("[", 1)[0]
            if base_name in self.names:
                self.counts[base_name] += 1
                self.definition_locations[base_name].add(
                    (str(item.location[0]), int(item.location[1]))
                )
                selected.append(item)
            else:
                deselected.append(item)
        items[:] = selected
        if deselected:
            config.hook.pytest_deselected(items=deselected)


def _executable_test_name(row: Any) -> str | None:
    values = shlex.split(str(row.command))
    for value in values:
        if "::" in value:
            candidate = value.rsplit("::", 1)[-1]
            if candidate.startswith("test_"):
                return candidate
    for index, value in enumerate(values[:-1]):
        if value == "-k":
            candidate = values[index + 1]
            if candidate.startswith("test_") and " " not in candidate:
                return candidate
    if len(values) >= 4 and values[1:3] == ["-m", "unittest"]:
        target = values[-1]
        target_module = ROOT.joinpath(*target.split(".")).with_suffix(".py")
        if target_module.is_file():
            return None
        candidate = target.rsplit(".", 1)[-1]
        if candidate.startswith("test_"):
            return candidate
    declared = str(row.test_name)
    if declared.startswith("test_") and " " not in declared:
        return declared
    return None


def _run_test_file(path: str, rows: Sequence[Any]) -> int:
    import pytest

    names = {_executable_test_name(row) for row in rows}
    if None in names:
        raise ValueError("exact_test_name_required")
    selector = _ExactNameSelection(names)
    result = int(
        pytest.main(
            [path, "-q"],
            plugins=[selector],
        )
    )
    invalid = {
        name: {
            "collected_items": selector.counts[name],
            "definition_locations": len(selector.definition_locations[name]),
        }
        for name in selector.names
        if len(selector.definition_locations[name]) != 1
    }
    if invalid:
        print(
            f"MTA exact test selection does not resolve to one definition: {invalid}",
            file=sys.stderr,
        )
        return 2
    return result


def _run_declared_commands(rows: Sequence[Any]) -> int:
    commands: list[tuple[str, ...]] = []
    for row in rows:
        values = shlex.split(str(row.command))
        if not values:
            print(f"empty MTA evidence command: {row.evidence_id}", file=sys.stderr)
            return 2
        values[0] = sys.executable
        command = tuple(values)
        if command not in commands:
            commands.append(command)
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            return int(completed.returncode)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--evidence-id", action="append", required=True)
    args = parser.parse_args(argv)

    declared = _declared_evidence()
    if len(args.evidence_id) != len(set(args.evidence_id)):
        print("duplicate MTA evidence id", file=sys.stderr)
        return 2
    missing = [value for value in args.evidence_id if value not in declared]
    if missing:
        print(f"unknown MTA evidence ids: {missing}", file=sys.stderr)
        return 2
    rows = [declared[value] for value in args.evidence_id]
    wrong_path = [
        row.evidence_id
        for row in rows
        if str(row.path).replace("\\", "/") != args.path.replace("\\", "/")
    ]
    if wrong_path:
        print(f"MTA evidence path mismatch: {wrong_path}", file=sys.stderr)
        return 2

    exact_test_names = [_executable_test_name(row) for row in rows]
    if (
        args.path.replace("\\", "/").startswith("tests/")
        and all(name is not None for name in exact_test_names)
    ):
        return _run_test_file(args.path, rows)
    return _run_declared_commands(rows)


if __name__ == "__main__":
    raise SystemExit(main())
