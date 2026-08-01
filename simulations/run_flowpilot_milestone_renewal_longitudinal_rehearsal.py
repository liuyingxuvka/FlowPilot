"""Run the current milestone-renewal behavior through the public CLI dispatcher.

This is a deterministic conformance rehearsal, not an AI quality experiment.
It suppresses only repeated run-artifact projection while keeping the public
command parser, current-run resolution, packet/lease/read/submit path, runtime
state transitions, and ledger persistence active.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ASSETS = REPO_ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowpilot_core_runtime import run_shell  # noqa: E402
from flowpilot_new_cli import main as public_cli_main  # noqa: E402

import flowpilot_fake_project_rehearsal_cli as rehearsal_cli  # noqa: E402
import flowpilot_fake_project_rehearsal_scenarios as scenarios  # noqa: E402


RESULTS_PATH = ROOT / "flowpilot_milestone_renewal_longitudinal_rehearsal_results.json"
SCENARIOS = (
    ("unchanged_resume_terminal", scenarios.scenario_milestone_unchanged_resume_terminal),
    ("changed_suffix", scenarios.scenario_milestone_changed_suffix),
    ("nested_child", scenarios.scenario_milestone_nested_child),
)


def _public_cli_in_process(
    root: Path,
    args: tuple[str, ...],
    *,
    json_mode: bool,
) -> Any:
    argv = ["--root", str(root.resolve())]
    if json_mode:
        argv.append("--json")
    argv.extend(args)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            returncode = int(public_cli_main(argv) or 0)
        except SystemExit as exc:
            code = exc.code
            returncode = int(code) if isinstance(code, int) else 1
        except BaseException as exc:  # pragma: no cover - reported in receipt
            returncode = 1
            stderr.write(repr(exc))
    from subprocess import CompletedProcess

    return CompletedProcess(
        args=[sys.executable, str(rehearsal_cli.ENTRYPOINT), *argv],
        returncode=returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def _skip_repeated_artifact_projection(*_args: Any, **_kwargs: Any) -> None:
    return None


def run_rehearsal(work_root: Path) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with (
        mock.patch.object(
            rehearsal_cli,
            "_run_public_cli",
            side_effect=_public_cli_in_process,
        ),
        mock.patch.object(
            run_shell,
            "materialize_run_artifacts",
            side_effect=_skip_repeated_artifact_projection,
        ),
    ):
        for scenario_id, scenario_fn in SCENARIOS:
            try:
                result = scenario_fn(work_root)
            except BaseException as exc:  # pragma: no cover - receipt owns failure
                result = {
                    "name": scenario_id,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            rows.append(result)
            rehearsal_cli.close_all_cli_workers()

    reviewer_block = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_flowpilot_recursive_route_execution_runtime.py::FlowPilotRecursiveRouteExecutionRuntimeTests::test_reviewer_block_keeps_milestone_and_frontier_uncommitted",
            "-q",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    rows.append(
        {
            "name": "milestone_reviewer_block",
            "ok": reviewer_block.returncode == 0,
            "evidence_role": "focused_direct_runtime_regression",
            "command": (
                "python -m pytest "
                "tests/test_flowpilot_recursive_route_execution_runtime.py::"
                "FlowPilotRecursiveRouteExecutionRuntimeTests::"
                "test_reviewer_block_keeps_milestone_and_frontier_uncommitted -q"
            ),
            "output": (reviewer_block.stdout + reviewer_block.stderr).strip(),
        }
    )

    status_by_name = {
        str(row.get("name") or ""): row.get("ok") is True
        for row in rows
    }
    return {
        "schema_version": "flowpilot.milestone_renewal_longitudinal_rehearsal.v1",
        "ok": all(row.get("ok") is True for row in rows),
        "evidence_role": "scripted_current_runtime_conformance_not_live_ai_quality",
        "public_entrypoint": str(rehearsal_cli.ENTRYPOINT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "execution_boundary": {
            "public_cli_parser_and_dispatcher_used": True,
            "current_run_resolution_used": True,
            "packet_lease_ack_authorized_read_submit_used": True,
            "runtime_state_and_ledger_persistence_used": True,
            "repeated_run_artifact_projection_suppressed": True,
            "suppression_reason": (
                "Artifact projection is independently covered; suppressing it keeps this behavior rehearsal "
                "bounded without changing packet, gate, route, or ledger state transitions."
            ),
        },
        "required_coverage": {
            "unchanged_renewal": status_by_name.get(
                "milestone_unchanged_resume_terminal", False
            ),
            "interruption_resume": status_by_name.get(
                "milestone_unchanged_resume_terminal", False
            ),
            "terminal_empty_plan": status_by_name.get(
                "milestone_unchanged_resume_terminal", False
            ),
            "changed_suffix": status_by_name.get(
                "milestone_changed_suffix", False
            ),
            "nested_child_local_closure": status_by_name.get(
                "milestone_nested_child", False
            ),
            "reviewer_block_prevents_commit": status_by_name.get(
                "milestone_reviewer_block", False
            ),
        },
        "scenarios": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    if args.work_root is None:
        with tempfile.TemporaryDirectory(prefix="flowpilot_milestone_longitudinal_") as tmp:
            result = run_rehearsal(Path(tmp))
    else:
        result = run_rehearsal(args.work_root)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        temp_path = args.json_out.with_name(args.json_out.name + ".tmp")
        temp_path.write_text(output, encoding="utf-8")
        temp_path.replace(args.json_out)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
