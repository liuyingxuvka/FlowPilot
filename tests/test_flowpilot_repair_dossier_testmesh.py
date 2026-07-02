from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

from flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_role_packet_depth_authorization_cartesian_mesh() -> None:
    roles = ["pm", "worker", "reviewer", "flowguard_operator"]
    packet_kinds = ["pm_repair_decision", "task", "review", "flowguard_check"]
    depths = [0, 1, 2, 4, 5]
    blocker_classes = ["evidence_gap", "flowguard_failure", "route_decomposition"]

    for role, packet_kind, depth, blocker_class in itertools.product(roles, packet_kinds, depths, blocker_classes):
        if (role, packet_kind) not in {
            ("pm", "pm_repair_decision"),
            ("worker", "task"),
            ("reviewer", "review"),
            ("flowguard_operator", "flowguard_check"),
        }:
            continue
        ledger, blocker_id = seeded_ledger(repair_depth=depth, blocker_class=blocker_class)
        packet_id = runtime.issue_task_packet(
            ledger,
            role,
            f"{role} repair mesh packet",
            json.dumps({"schema_version": "test.mesh.v1"}, sort_keys=True),
            packet_kind=packet_kind,
            subject_id=blocker_id if packet_kind == "pm_repair_decision" else ledger["active_blockers"][blocker_id]["subject_packet_id"],
            target_result_id=ledger["active_blockers"][blocker_id]["target_result_id"],
            route_node_id=ledger["active_blockers"][blocker_id]["route_node_id"],
            route_scope="pm_repair_decision" if packet_kind == "pm_repair_decision" else "node",
            repair_blocker_id=blocker_id,
        )
        packet = ledger["packets"][packet_id]
        body = json.loads(packet["body"])

        assert body["repair_dossier_context"]["repair_depth"] == depth
        assert packet["envelope"]["authorized_result_reads"]
        assert all(role in row["allowed_roles"] for row in packet["envelope"]["authorized_result_reads"])


def test_context_only_results_are_not_marked_current_evidence() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="evidence_gap")

    dossier = runtime._repair_dossier_projection(ledger, ledger["active_blockers"][blocker_id])

    assert "result-worker-blocked" in dossier["context_only_result_ids"]
    assert "result-review-blocker" in dossier["context_only_result_ids"]
    assert not dossier["current_evidence_result_ids"]


def _repair_dossier_testmesh_report() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "simulations/run_flowpilot_repair_dossier_testmesh_checks.py",
            "--json",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_repair_dossier_testmesh_model_script_passes() -> None:
    assert _repair_dossier_testmesh_report()["ok"] is True


def test_stage_precedence_cartesian_cells_cover_plan_result_and_claim_cases() -> None:
    report = _repair_dossier_testmesh_report()
    cells = [
        cell
        for cell in report["cells"]
        if cell.get("dimension_family") == "stage_precedence"
    ]

    assert report["stage_precedence_cell_count"] == 120
    assert {
        (
            cell["subject_case"],
            cell["evidence_state"],
            cell["subject_completion_claim_state"],
            cell["actual_outcome"],
        )
        for cell in cells
    } == {
        (
            "pm_plan_stage_no_completion_claim",
            "pm_plan_only",
            "no_completion_claim",
            "allow_plan_stage_review",
        ),
        (
            "pm_plan_stage_claims_worker_evidence",
            "pm_plan_only",
            "claims_worker_evidence_complete",
            "block_missing_claimed_current_evidence",
        ),
        (
            "worker_result_stage_plan_only",
            "pm_plan_only",
            "result_stage_subject",
            "block_missing_current_worker_evidence",
        ),
        (
            "worker_result_stage_current_worker_evidence",
            "current_worker_evidence",
            "result_stage_subject",
            "allow_worker_result_review",
        ),
    }
