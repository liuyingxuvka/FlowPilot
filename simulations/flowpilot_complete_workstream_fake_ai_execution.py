"""Execute the finite complete-workstream fake-AI universe through FlowPilot.

This is an execution harness, not a second responder. Every payload is built by
``ContractDrivenFakeAIResponder.from_open_packet_result`` and submitted through
the current public ACK/open/submit commands. The resulting receipt keeps
declared, selected, executed, passed, failed, stale, not-run, and proof-backed
profile ids separate.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
for path in (ASSETS, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import flowpilot_new  # noqa: E402
import flowpilot_contract_driven_fake_ai as fake_ai  # noqa: E402
from flowpilot_core_runtime import fake_e2e, run_shell, runtime  # noqa: E402
from scripts.compile_flowpilot_acceptance_testmesh_evidence import source_fingerprint  # noqa: E402


RESULT_SCHEMA_VERSION = "flowpilot.complete_workstream_fake_ai_execution.v1"
RESOURCE_CASES = {
    "mandatory_local_skill_inventory": ("discovery", "pm", "mechanically_valid"),
    "selected_skill_deep_read": ("skill_standard", "pm", "mechanically_valid"),
    "ordinary_material_evidence_work": ("node", "research_worker", "mechanically_valid"),
    "optional_material_map_absent": ("node", "research_worker", "mechanically_valid"),
    "forbidden_old_discovery_fields": ("discovery", "pm", "mechanical_contract_blocked"),
}


def _require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _authorize_current_run(ledger: dict[str, Any]) -> None:
    ledger["startup_intake"] = {
        "sealed": True,
        "startup_answers": {runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True},
    }


def _create_shell(root: Path, *, run_id: str) -> tuple[run_shell.RunShell, dict[str, Any]]:
    shell = run_shell.create_run_shell(root, "Goal", "Acceptance", run_id=run_id)
    ledger = run_shell.load_run_ledger(shell)
    _authorize_current_run(ledger)
    runtime.create_route(ledger, "High-standard route", ["Plan", "Execute", "Verify"])
    return shell, ledger


def _open_public_packet(
    root: Path,
    *,
    packet_id: str,
    responsibility: str,
    agent_id: str,
) -> tuple[str, dict[str, Any], fake_ai.ContractDrivenFakeAIResponder]:
    dispatched = flowpilot_new.dispatch_current_role(
        root,
        packet_id=packet_id,
        responsibility=responsibility,
        host_kind="fake",
        agent_id=agent_id,
    )
    _require(bool(dispatched.get("ok")), dispatched)
    lease_id = str(dispatched["lease_id"])
    acked = flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
    _require(bool(acked.get("ok")), acked)
    opened = flowpilot_new.open_packet(root, lease_id=lease_id, packet_id=packet_id)
    responder = fake_ai.ContractDrivenFakeAIResponder.from_open_packet_result(opened)
    return lease_id, opened, responder


def _submit_public_payload(
    root: Path,
    *,
    lease_id: str,
    packet_id: str,
    payload: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    path = root / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return flowpilot_new.submit_result(
        root,
        lease_id=lease_id,
        packet_id=packet_id,
        body_file=path,
    )


def assert_public_constructor_is_single_authority() -> None:
    responder = fake_ai.ContractDrivenFakeAIResponder(
        {
            "minimal_valid_shape": {
                "contract_self_check": {
                    "workstream_plan_and_completion": {
                        "steps": [{"step_number": 1, "status": "completed"}]
                    }
                }
            }
        }
    )
    for action in (
        lambda: responder.complete_workstream_payload("complete_workstream_pass"),
        lambda: responder.resource_discovery_payload("optional_material_map_absent"),
    ):
        try:
            action()
        except ValueError as exc:
            _require("from_open_packet_result" in str(exc), exc)
        else:
            raise AssertionError("semantic profile bypassed the public open-packet constructor")


def execute_workstream_profile(profile_id: str) -> dict[str, Any]:
    _require(profile_id in fake_ai.COMPLETE_WORKSTREAM_PROFILE_IDS, profile_id)
    with tempfile.TemporaryDirectory(prefix=f"flowpilot-workstream-{profile_id}-") as tmp:
        root = Path(tmp)
        shell, ledger = _create_shell(root, run_id=f"run-{profile_id}")
        subject_packet_id = runtime._ensure_high_standard_contract_packet(ledger)
        run_shell.save_run_ledger(shell, ledger)

        subject_lease, subject_open, subject_responder = _open_public_packet(
            root,
            packet_id=subject_packet_id,
            responsibility="pm",
            agent_id=f"pm-{profile_id}",
        )
        _require(
            subject_open["submission_checklist"]["contract_family_id"] == "task.high_standard_contract",
            subject_open,
        )
        subject_payload = subject_responder.complete_workstream_payload(profile_id)
        subject_result = _submit_public_payload(
            root,
            lease_id=subject_lease,
            packet_id=subject_packet_id,
            payload=subject_payload,
            name=f"subject-{profile_id}",
        )
        ledger = run_shell.load_run_ledger(run_shell.load_run_shell(root))
        subject_row = ledger["results"][subject_result["result_id"]]
        _require(subject_row["status"] == "mechanically_valid", subject_row)

        flowguard_action = subject_result["run_until_wait"]["next_action"]
        _require(flowguard_action["responsibility"] == "flowguard_operator", flowguard_action)
        flowguard_packet_id = str(flowguard_action["subject_id"])
        flowguard_lease, flowguard_open, flowguard_responder = _open_public_packet(
            root,
            packet_id=flowguard_packet_id,
            responsibility="flowguard_operator",
            agent_id=f"flowguard-{profile_id}",
        )
        ledger = run_shell.load_run_ledger(run_shell.load_run_shell(root))
        fake_e2e._write_flowguard_evidence_artifact_for_packet(
            ledger,
            ledger["packets"][flowguard_packet_id],
            decision="pass",
        )
        run_shell.save_run_ledger(run_shell.load_run_shell(root), ledger)
        flowguard_payload = flowguard_responder.complete_workstream_payload(
            "formal_flowguard_independence_preserved"
        )
        flowguard_result = _submit_public_payload(
            root,
            lease_id=flowguard_lease,
            packet_id=flowguard_packet_id,
            payload=flowguard_payload,
            name=f"flowguard-{profile_id}",
        )

        review_action = flowguard_result["run_until_wait"]["next_action"]
        _require(review_action["responsibility"] == "reviewer", review_action)
        review_packet_id = str(review_action["subject_id"])
        review_lease, review_open, review_responder = _open_public_packet(
            root,
            packet_id=review_packet_id,
            responsibility="reviewer",
            agent_id=f"reviewer-{profile_id}",
        )
        _require(
            review_open["submission_checklist"]["contract_family_id"] == "review.any_current_subject",
            review_open,
        )
        review_payload = review_responder.complete_workstream_review_payload(profile_id)
        review_result = _submit_public_payload(
            root,
            lease_id=review_lease,
            packet_id=review_packet_id,
            payload=review_payload,
            name=f"review-{profile_id}",
        )
        ledger = run_shell.load_run_ledger(run_shell.load_run_shell(root))
        review_row = ledger["results"][review_result["result_id"]]
        should_block = profile_id in fake_ai.WORKSTREAM_REVIEW_BLOCKING_PROFILE_IDS
        expected_semantic_decision = "block" if should_block else "pass"
        _require(review_row["status"] == "accepted", review_row)
        _require(review_row["semantic_decision"] == expected_semantic_decision, review_row)

        matching_blockers = [
            row
            for row in ledger["active_blockers"].values()
            if row.get("result_id") == review_result["result_id"]
        ]
        if should_block:
            _require(len(matching_blockers) == 1, matching_blockers)
            _require(matching_blockers[0]["status"] == "active", matching_blockers[0])
            next_action = review_result["run_until_wait"]["next_action"]
            _require(next_action["responsibility"] == "pm", next_action)
            _require(next_action["action_type"] == "dispatch_current_role", next_action)
        else:
            _require(not matching_blockers, matching_blockers)
            audit = review_payload["contract_self_check"]["workstream_plan_audit"]
            _require(
                audit["decision"] in {"pass", "pass_with_pm_disposition_required"},
                audit,
            )

        if profile_id == "reviewer_sub9_pm_disposition_required":
            _require(bool(review_payload["passed"]), review_payload)
            _require(
                "score alone is not a blocker" in review_payload["pm_suggestion_items"][0],
                review_payload,
            )
        if profile_id == "pm_sub9_disposition_recorded":
            context = subject_payload["contract_self_check"]["workstream_plan_and_completion"]["reviewer_score_context"]
            _require(context["pm_disposition_status"] != "pending", context)
        if profile_id == "corrected_workstream_retry":
            section = subject_payload["contract_self_check"]["workstream_plan_and_completion"]
            _require(section["repair_attempt"] == 2 and bool(section["repair_delta"]), section)
        if profile_id == "repeated_incomplete_plan_repair":
            section = subject_payload["contract_self_check"]["workstream_plan_and_completion"]
            _require(section["repair_delta"] == "No effective delta.", section)

        return {
            "profile_id": profile_id,
            "profile_family": "complete_workstream",
            "execution_status": "passed",
            "generated_from_public_open_packet": True,
            "subject_contract_family_id": subject_open["submission_checklist"]["contract_family_id"],
            "subject_contract_fingerprint": subject_open["submission_checklist"]["contract_fingerprint"],
            "flowguard_contract_fingerprint": flowguard_open["submission_checklist"]["contract_fingerprint"],
            "review_contract_fingerprint": review_open["submission_checklist"]["contract_fingerprint"],
            "subject_result_status": subject_row["status"],
            "review_result_status": review_row["status"],
            "review_semantic_decision": review_row["semantic_decision"],
            "expected_semantic_decision": expected_semantic_decision,
            "pm_repair_routed": should_block,
            "proof_backed": True,
        }


def execute_resource_profile(profile_id: str) -> dict[str, Any]:
    _require(profile_id in fake_ai.RESOURCE_DISCOVERY_PROFILE_IDS, profile_id)
    route_scope, responsibility, expected_status = RESOURCE_CASES[profile_id]
    with tempfile.TemporaryDirectory(prefix=f"flowpilot-resource-{profile_id}-") as tmp:
        root = Path(tmp)
        shell, ledger = _create_shell(root, run_id=f"run-resource-{profile_id}")
        if route_scope == "discovery":
            packet_id = runtime._ensure_discovery_packet(ledger)
        elif route_scope == "skill_standard":
            packet_id = runtime._ensure_skill_standard_packet(ledger)
        else:
            packet_id = runtime.issue_task_packet(
                ledger,
                responsibility,
                "Perform ordinary bounded evidence work",
                json.dumps({"instruction": "Verify the current evidence question."}),
                route_scope="node",
            )
        run_shell.save_run_ledger(shell, ledger)
        lease_id, opened, responder = _open_public_packet(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=f"{responsibility}-{profile_id}",
        )
        payload = responder.resource_discovery_payload(profile_id)
        submitted = _submit_public_payload(
            root,
            lease_id=lease_id,
            packet_id=packet_id,
            payload=payload,
            name=f"resource-{profile_id}",
        )
        ledger = run_shell.load_run_ledger(run_shell.load_run_shell(root))
        row = ledger["results"][submitted["result_id"]]
        _require(row["status"] == expected_status, row)
        _require(
            responder.open_packet_identity["contract_fingerprint"]
            == opened["submission_checklist"]["contract_fingerprint"],
            opened,
        )
        if profile_id == "forbidden_old_discovery_fields":
            _require(
                set(row["forbidden_fields_seen"])
                == {"material_sources", "material_sufficiency"},
                row,
            )
        return {
            "profile_id": profile_id,
            "profile_family": "resource_discovery",
            "execution_status": "passed",
            "generated_from_public_open_packet": True,
            "contract_family_id": opened["submission_checklist"]["contract_family_id"],
            "contract_fingerprint": opened["submission_checklist"]["contract_fingerprint"],
            "result_status": row["status"],
            "expected_result_status": expected_status,
            "proof_backed": True,
        }


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def run_all_profiles() -> dict[str, Any]:
    declared_ids = _ordered_unique(
        [*fake_ai.COMPLETE_WORKSTREAM_PROFILE_IDS, *fake_ai.RESOURCE_DISCOVERY_PROFILE_IDS]
    )
    source_start = source_fingerprint()
    selected_ids = list(declared_ids)
    executed_ids: list[str] = []
    generated_ids: list[str] = []
    passed_ids: list[str] = []
    failed_ids: list[str] = []
    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    constructor_gate_ok = True
    try:
        assert_public_constructor_is_single_authority()
    except Exception as exc:  # noqa: BLE001 - record the complete finite run.
        constructor_gate_ok = False
        failures.append({"profile_id": "public_constructor_gate", "error": repr(exc)})

    for profile_id in selected_ids:
        executed_ids.append(profile_id)
        try:
            if profile_id in fake_ai.COMPLETE_WORKSTREAM_PROFILE_IDS:
                receipt = execute_workstream_profile(profile_id)
            else:
                receipt = execute_resource_profile(profile_id)
            generated_ids.append(profile_id)
            passed_ids.append(profile_id)
            receipts.append(receipt)
        except Exception as exc:  # noqa: BLE001 - preserve every failed profile id.
            failed_ids.append(profile_id)
            failures.append({"profile_id": profile_id, "error": repr(exc)})

    source_end = source_fingerprint()
    source_current = source_start == source_end
    stale_ids = [] if source_current else list(executed_ids)
    not_run_ids = sorted(set(declared_ids) - set(executed_ids))
    proof_backed_ids = [
        str(row["profile_id"])
        for row in receipts
        if row.get("proof_backed") and row.get("execution_status") == "passed"
    ]
    exact_accounting = (
        set(declared_ids) == set(selected_ids)
        and set(selected_ids) == set(executed_ids)
        and set(executed_ids) == set(passed_ids) | set(failed_ids)
        and not (set(passed_ids) & set(failed_ids))
        and set(proof_backed_ids) == set(passed_ids)
    )
    ok = (
        constructor_gate_ok
        and source_current
        and exact_accounting
        and not failed_ids
        and not not_run_ids
        and set(generated_ids) == set(declared_ids)
    )
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "ok": ok,
        "selection_policy": "full_finite_profile_enumeration",
        "canonical_responder": "ContractDrivenFakeAIResponder.from_open_packet_result",
        "constructor_gate_ok": constructor_gate_ok,
        "source_fingerprint_start": source_start,
        "source_fingerprint_end": source_end,
        "source_fingerprint_current": source_current,
        "accounting": {
            "declared_count": len(declared_ids),
            "declared_ids": declared_ids,
            "applicable_count": len(declared_ids),
            "applicable_ids": declared_ids,
            "excluded_count": 0,
            "excluded_ids": [],
            "generated_count": len(generated_ids),
            "generated_ids": generated_ids,
            "selected_count": len(selected_ids),
            "selected_ids": selected_ids,
            "executed_count": len(executed_ids),
            "executed_ids": executed_ids,
            "passed_count": len(passed_ids),
            "passed_ids": passed_ids,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
            "stale_count": len(stale_ids),
            "stale_ids": stale_ids,
            "not_run_count": len(not_run_ids),
            "not_run_ids": not_run_ids,
            "proof_backed_count": len(proof_backed_ids),
            "proof_backed_ids": proof_backed_ids,
            "exact_accounting": exact_accounting,
        },
        "profile_receipts": receipts,
        "failures": failures,
        "claim_boundary": (
            "Full finite coverage of the declared 15 complete-workstream and 5 resource-discovery profiles; "
            "this is not a claim about arbitrary future natural-language behavior."
        ),
    }

