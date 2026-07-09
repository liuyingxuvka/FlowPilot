from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from scripts.test_tier import background as test_tier_background
from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json
from tests.synthetic_agent_trace_replay import SyntheticTracePackage, start_worker_trace

REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS_ROOT = REPO_ROOT / "simulations"
ASSETS_ROOT = REPO_ROOT / "skills" / "flowpilot" / "assets"
for import_root in (SIMULATIONS_ROOT, ASSETS_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from flowpilot_core_runtime import runtime as core_runtime  # noqa: E402
import flowpilot_core_runtime_scenarios as core_runtime_scenarios  # noqa: E402


HISTORICAL_METADATA_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "flowpilot"
    / "run-20260527-212331-control-plane-metadata.json"
)

CONTRACT_SURFACE_REDUCTION_PACKET_FAMILIES = (
    "task.high_standard_contract",
    "task.discovery",
    "task.skill_standard",
    "task.planning",
    "task.node_acceptance_plan",
    "task.node",
    "flowguard_check.post_result",
    "review.any_current_subject",
    "pm_repair_decision.pm_repair_decision",
    "pm_disposition.node_pm_disposition",
    "review.parent_backward_replay",
    "review.terminal_backward_replay",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _package_background_proof_is_current(root: Path, proof_root: Path, name: str) -> dict[str, Any]:
    evidence = test_tier_background.classify_background_artifact(proof_root, name)
    current = read_json(root / ".flowpilot" / "current.json")
    meta_path = test_tier_background.artifact_paths(proof_root, name)["meta"]
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    reasons = list(evidence.get("reasons") or [])
    current_run_id = current.get("run_id")
    if meta.get("run_id") != current_run_id:
        reasons.append("proof_run_id_not_current")
    return {
        "ok": bool(evidence.get("ok")) and meta.get("run_id") == current_run_id,
        "status": evidence["status"],
        "run_id": meta.get("run_id"),
        "current_run_id": current_run_id,
        "reasons": reasons,
    }


def _historical_snapshot_claim_is_authoritative(root: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    current = read_json(root / ".flowpilot" / "current.json")
    reasons: list[str] = []
    if snapshot.get("run_id") != current.get("run_id"):
        reasons.append("snapshot_run_id_not_current")
    if snapshot.get("display_status") == "complete" and snapshot.get("router_pending_action"):
        reasons.append("display_projection_conflicts_with_router_pending_action")
    if snapshot.get("terminal_ledger_status") != "closed":
        reasons.append("terminal_ledger_not_closed")
    return {"authoritative": not reasons, "reasons": reasons}


def _package_completion_claim_is_mechanically_supported(replay) -> dict[str, Any]:
    record = replay.packet_record()
    missing = []
    if not record.get("active_holder_lease_issued"):
        missing.append("packet_current_assignment_missing")
    if not record.get("active_holder_ack_recorded"):
        missing.append("active_holder_ack_missing")
    if replay.result_envelope is None:
        missing.append("result_envelope_missing")
    else:
        result_open = replay.result_envelope.get("result_body_opened_by_role") or {}
        if not result_open.get("body_hash_verified"):
            missing.append("result_body_hash_not_verified")
    return {"ok": not missing, "missing": missing}


def _write_historical_flowguard_evidence_artifact(
    ledger: dict[str, Any],
    packet_id: str,
    *,
    decision: str,
) -> Path:
    path = Path(str(ledger["run_root"])) / "evidence" / "flowguard" / packet_id / "flowguard_evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": {
                    "decision": decision,
                    "failed_predicates": [] if decision == "pass" else ["semantic_contract_missing"],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _semantic_standard_package_ok(package: dict[str, Any]) -> dict[str, Any]:
    missing = []
    inherited = package.get("inherited_skill_standard_ids") or []
    matrix = package.get("skill_standard_result_matrix") or []
    waivers = {
        str(item.get("standard_id"))
        for item in package.get("approved_waivers") or []
        if isinstance(item, dict) and item.get("approved") is True
    }
    if not inherited:
        missing.append("inherited_standard_ids_missing")
    covered = {str(item.get("standard_id")) for item in matrix if isinstance(item, dict)}
    for standard_id in inherited:
        if standard_id not in covered and standard_id not in waivers:
            missing.append(f"missing_standard_result:{standard_id}")
    return {"ok": not missing, "missing": missing}


def _contract_surface_reduction_baseline_ok(package: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    covered = {str(item) for item in package.get("covered_packet_families") or []}
    missing_families = [
        family for family in CONTRACT_SURFACE_REDUCTION_PACKET_FAMILIES if family not in covered
    ]
    first_packet_failure = package.get("first_packet_failure") or {}
    forbidden = {str(item) for item in package.get("forbidden_shortcuts") or []}

    if package.get("success_run_id") != "run-20260613-140526":
        reasons.append("success_run_id_not_20260613_baseline")
    if package.get("baseline_use") != "process_route_only":
        reasons.append("historical_run_used_as_field_shape_baseline")
    if package.get("historical_field_shape_authority") is not False:
        reasons.append("historical_field_shape_promoted_to_current_contract")
    if missing_families:
        reasons.append("missing_mainline_packet_family_coverage")
    if first_packet_failure.get("blocker_class") != "early_terminal_evidence_requirement":
        reasons.append("first_packet_failure_not_terminal_evidence_regression")
    if first_packet_failure.get("terminal_replay_fields_required_at_first_packet") is not False:
        reasons.append("first_packet_still_requires_terminal_replay_fields")
    if (
        first_packet_failure.get("expected_current_disposition")
        != "invalid_under_reduced_high_standard_contract"
    ):
        reasons.append("first_packet_failure_disposition_not_reduced_contract_invalid")
    for shortcut in {
        "restore_historical_field_shape",
        "treat_first_packet_as_terminal_replay",
        "skip_mainline_packet_family_coverage",
    }:
        if shortcut not in forbidden:
            reasons.append(f"missing_forbidden_shortcut:{shortcut}")

    return {"ok": not reasons, "reasons": reasons, "missing_packet_families": missing_families}


def _install_split_brain_report(repo_skill: Path, installed_skill: Path) -> dict[str, Any]:
    repo_digest = _digest_tree(repo_skill)
    installed_digest = _digest_tree(installed_skill)
    return {
        "ok": repo_digest == installed_digest,
        "repo_digest": repo_digest,
        "installed_digest": installed_digest,
        "install_sync_required": repo_digest != installed_digest,
    }


def _display_projection_is_authoritative(state: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if projection.get("run_id") != state.get("run_id"):
        reasons.append("projection_run_id_not_current")
    if projection.get("route_version") != state.get("route_version"):
        reasons.append("projection_route_version_stale")
    if projection.get("active_node") != state.get("active_node"):
        reasons.append("projection_active_node_stale")
    if state.get("pending_action"):
        reasons.append("router_pending_action_still_authoritative")
    return {"authoritative": not reasons, "reasons": reasons}


def _fixed_router_event_receipts_are_authoritative(fixture: dict[str, Any]) -> dict[str, Any]:
    receipts = fixture["fixed_router_event_receipts"]
    reasons: list[str] = []
    if receipts.get("local_submit_output_receipts", 0) and not receipts.get("router_directed_receipts", 0):
        reasons.append("local_submit_output_receipts_are_not_router_events")
    if receipts.get("router_event_records", 0) < receipts.get("local_submit_output_receipts", 0):
        reasons.append("router_event_count_does_not_match_receipt_count")
    if receipts.get("local_receipt_closes_blocker") is True:
        reasons.append("local_receipt_was_allowed_to_close_blocker")
    return {"authoritative": not reasons, "reasons": reasons}


def _same_family_control_blockers_are_collapsed(fixture: dict[str, Any]) -> dict[str, Any]:
    blockers = fixture["control_blockers"]
    reasons: list[str] = []
    if blockers.get("same_family_should_collapse_to_one_active_or_terminal_record") is not True:
        reasons.append("fixture_does_not_expect_same_family_collapse")
    if blockers.get("dominant_family_count", 0) > 1:
        reasons.append("same_family_blockers_were_materialized_repeatedly")
    return {"collapsed": not reasons, "reasons": reasons}


def _break_glass_incident_has_closed_evidence(fixture: dict[str, Any]) -> dict[str, Any]:
    break_glass = fixture["break_glass"]
    reasons: list[str] = []
    if break_glass.get("open_incidents", 0):
        reasons.append("break_glass_incident_still_open")
    if not break_glass.get("recovery_transactions"):
        reasons.append("break_glass_recovery_transaction_missing")
    if break_glass.get("patch_validation_status") == "not_run":
        reasons.append("break_glass_patch_validation_not_run")
    return {"covered": not reasons, "reasons": reasons}


def _write_databank_control_plane_miss_break_glass(run_root: Path) -> None:
    break_glass_root = run_root / "controller_break_glass"
    incidents = break_glass_root / "incidents"
    patches = break_glass_root / "patches"
    incidents.mkdir(parents=True, exist_ok=True)
    patches.mkdir(parents=True, exist_ok=True)
    (incidents / "incident-blocker-0006.json").write_text(
        json.dumps(
            {
                "incident_id": "incident-blocker-0006",
                "status": "open",
                "final_disposition": None,
                "closed_at": None,
                "related_patch_ids": [
                    "patch-blocker-0006-accepted-review-sync",
                    "patch-active-breakglass-reattach",
                    "patch-repair-blocked-packet-command",
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    for patch_id in [
        "patch-blocker-0006-accepted-review-sync",
        "patch-active-breakglass-reattach",
        "patch-repair-blocked-packet-command",
    ]:
        (patches / f"{patch_id}.json").write_text(
            json.dumps(
                {
                    "patch_id": patch_id,
                    "temporary": True,
                    "permanent_fix_needed": True,
                    "validation_status": "pending",
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )


def _databank_control_plane_miss_ledger(run_root: Path) -> dict[str, Any]:
    ledger = core_runtime.new_ledger(
        "DataBank replay fixture",
        "Final closure requires clean control-plane ledger hygiene.",
    )
    ledger["run_root"] = str(run_root)
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }
    core_runtime.create_route(ledger, "DataBank replay route", ["Final replay"])
    packet_id = core_runtime.issue_task_packet(
        ledger,
        "pm",
        "Absorb FlowGuard report for structural decision pm_decision_gate-0005",
        json.dumps({"decision": "accept", "accepted_flowguard_result_id": "result-0208"}),
        packet_kind="pm_flowguard_acceptance",
        subject_id="pm_decision_gate-0005",
        target_result_id="result-0208",
        route_node_id="node-61-test-suite-update-repair-v3",
        route_scope="pm_flowguard_acceptance",
    )
    packet = ledger["packets"][packet_id]
    packet["packet_id"] = "packet-0205"
    ledger["packets"]["packet-0205"] = packet
    del ledger["packets"][packet_id]
    packet_id = "packet-0205"
    body = json.dumps({"decision": "accept", "accepted_flowguard_result_id": "result-0208"})
    ledger["results"]["result-0209"] = {
        "result_id": "result-0209",
        "packet_id": packet_id,
        "producer_lease_id": "lease-0206",
        "status": "review_blocked",
        "accepted": False,
        "body": body,
        "review_id": "review-0064",
        "envelope": {
            "body_hash": core_runtime.hash_text(body),
            "evidence_generation": ledger["source_generation"],
        },
    }
    ledger["reviews"]["review-0064"] = {
        "review_id": "review-0064",
        "result_id": "result-0209",
        "accepted": False,
        "blockers": ["result_not_mechanically_valid"],
    }
    packet["status"] = "accepted"
    packet["accepted_result_id"] = "result-0209"
    packet["assigned_lease_id"] = "lease-0206"
    packet["repair_blocker_id"] = ""
    packet["envelope"]["repair_blocker_id"] = ""
    packet["envelope"]["current_handoff_contract"]["input_material_manifest"]["blocker_id"] = ""
    ledger["active_blockers"]["blocker-0007"] = {
        "blocker_id": "blocker-0007",
        "status": "active",
        "blocker_class": "system_validation_failure",
        "route_node_id": "node-61-test-suite-update-repair-v3",
        "packet_id": "packet-0207",
        "subject_packet_id": "packet-0205",
        "repair_target_packet_id": "packet-0205",
        "target_result_id": "result-0209",
    }
    final_packet_id = core_runtime.issue_task_packet(
        ledger,
        "reviewer",
        "Execute route node node-65-final-review-and-replay: Final review and backward replay",
        json.dumps({"schema_version": "black_box_flowpilot.node_task_packet.v1"}),
        packet_kind="task",
        route_node_id="node-65-final-review-and-replay",
        route_scope="node",
        authorized_result_reads=[],
    )
    final_packet = ledger["packets"][final_packet_id]
    final_packet["packet_id"] = "packet-0238"
    final_packet["envelope"]["responsibility"] = "reviewer"
    final_packet["envelope"]["authorized_result_reads"] = []
    ledger["packets"]["packet-0238"] = final_packet
    del ledger["packets"][final_packet_id]
    ledger["closure"] = {"decision": "complete", "blockers": []}
    _write_databank_control_plane_miss_break_glass(run_root)
    return ledger


def _databank_control_plane_miss_reasons(ledger: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if core_runtime._accepted_result_pointer_violation(ledger, ledger["packets"]["packet-0205"]):
        reasons.append("accepted_result_pointer_targets_review_blocked_result")
    packet = ledger["packets"]["packet-0205"]
    envelope = packet["envelope"]
    handoff = envelope["current_handoff_contract"]["input_material_manifest"]
    if not packet.get("repair_blocker_id") or not envelope.get("repair_blocker_id") or not handoff.get("blocker_id"):
        reasons.append("pm_flowguard_acceptance_repair_identity_missing")
    final_packet = ledger["packets"]["packet-0238"]
    if (
        final_packet["envelope"].get("responsibility") == "reviewer"
        and "final-review" in str(final_packet["envelope"].get("route_node_id") or "")
        and not final_packet["envelope"].get("authorized_result_reads")
    ):
        reasons.append("final_reviewer_packet_authorized_result_reads_empty")
    closure_blockers = core_runtime._closure_blockers(
        ledger,
        validation_evidence_id="validation-result-0211",
        required_flowguard_target="development_process",
    )
    if any("active_blocker:blocker-0007" in item for item in closure_blockers):
        reasons.append("stale_active_blocker_survived_final_closure")
    if any("break_glass_incident_open" in item for item in closure_blockers):
        reasons.append("break_glass_incident_open_at_final_closure")
    if any("break_glass_patch_pending" in item for item in closure_blockers):
        reasons.append("break_glass_patch_validation_pending_at_final_closure")
    return reasons


class FlowPilotHistoricalLiveRunReplayTests(FlowPilotRouterRuntimeTestBase):
    def test_run_20260527_metadata_fixture_contains_no_sealed_bodies(self) -> None:
        fixture = json.loads(HISTORICAL_METADATA_FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(fixture["run_id"], "run-20260527-212331")
        self.assertEqual(fixture["fixture_scope"], "controller_visible_control_plane_metadata_only")
        self.assertFalse(fixture["sealed_body_policy"]["contains_sealed_packet_bodies"])
        self.assertFalse(fixture["sealed_body_policy"]["contains_sealed_result_bodies"])
        self.assertFalse(fixture["sealed_body_policy"]["contains_sealed_report_bodies"])

    def test_run_20260527_local_pm_receipts_without_router_event_do_not_close_blocker(self) -> None:
        fixture = json.loads(HISTORICAL_METADATA_FIXTURE.read_text(encoding="utf-8"))

        gate = _fixed_router_event_receipts_are_authoritative(fixture)
        self.assertFalse(gate["authoritative"])
        self.assertIn("local_submit_output_receipts_are_not_router_events", gate["reasons"])
        self.assertIn("router_event_count_does_not_match_receipt_count", gate["reasons"])

    def test_run_20260527_same_family_blocker_storm_is_not_a_valid_new_blocker_series(self) -> None:
        fixture = json.loads(HISTORICAL_METADATA_FIXTURE.read_text(encoding="utf-8"))

        gate = _same_family_control_blockers_are_collapsed(fixture)
        self.assertFalse(gate["collapsed"])
        self.assertIn("same_family_blockers_were_materialized_repeatedly", gate["reasons"])

    def test_run_20260527_break_glass_limbo_is_reported_as_uncovered(self) -> None:
        fixture = json.loads(HISTORICAL_METADATA_FIXTURE.read_text(encoding="utf-8"))

        gate = _break_glass_incident_has_closed_evidence(fixture)
        self.assertFalse(gate["covered"])
        self.assertIn("break_glass_incident_still_open", gate["reasons"])
        self.assertIn("break_glass_recovery_transaction_missing", gate["reasons"])
        self.assertIn("break_glass_patch_validation_not_run", gate["reasons"])

    def test_run_20260707_databank_control_plane_miss_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            ledger = _databank_control_plane_miss_ledger(Path(temp_root))

            with self.assertRaises(core_runtime.BlackBoxRuntimeError):
                core_runtime.repair_accepted_packet_assignment(ledger, "packet-0205")

            preflight = core_runtime.final_return_preflight(
                ledger,
                guard={
                    "controller_stop_allowed": True,
                    "decision": "terminal_return",
                    "next_action": {"action_type": "terminal_complete"},
                },
            )
            reasons = _databank_control_plane_miss_reasons(ledger)

        self.assertFalse(preflight["allowed"], preflight)
        self.assertIn("accepted_result_pointer_targets_review_blocked_result", reasons)
        self.assertIn("pm_flowguard_acceptance_repair_identity_missing", reasons)
        self.assertIn("final_reviewer_packet_authorized_result_reads_empty", reasons)
        self.assertIn("stale_active_blocker_survived_final_closure", reasons)
        self.assertIn("break_glass_incident_open_at_final_closure", reasons)
        self.assertIn("break_glass_patch_validation_pending_at_final_closure", reasons)

    def test_contract_surface_reduction_baseline_keeps_success_mainline_and_rejects_first_packet_terminal_evidence(
        self,
    ) -> None:
        baseline_package = {
            "success_run_id": "run-20260613-140526",
            "baseline_use": "process_route_only",
            "historical_field_shape_authority": False,
            "covered_packet_families": list(CONTRACT_SURFACE_REDUCTION_PACKET_FAMILIES),
            "first_packet_failure": {
                "blocker_class": "early_terminal_evidence_requirement",
                "terminal_replay_fields_required_at_first_packet": False,
                "expected_current_disposition": "invalid_under_reduced_high_standard_contract",
            },
            "forbidden_shortcuts": [
                "restore_historical_field_shape",
                "treat_first_packet_as_terminal_replay",
                "skip_mainline_packet_family_coverage",
            ],
        }

        accepted = _contract_surface_reduction_baseline_ok(baseline_package)
        self.assertTrue(accepted["ok"], accepted)
        self.assertEqual(accepted["missing_packet_families"], [])

        old_field_shape_package = {**baseline_package, "historical_field_shape_authority": True}
        old_field_shape = _contract_surface_reduction_baseline_ok(old_field_shape_package)
        self.assertFalse(old_field_shape["ok"])
        self.assertIn("historical_field_shape_promoted_to_current_contract", old_field_shape["reasons"])

        missing_family_package = {
            **baseline_package,
            "covered_packet_families": list(CONTRACT_SURFACE_REDUCTION_PACKET_FAMILIES[:-1]),
        }
        missing_family = _contract_surface_reduction_baseline_ok(missing_family_package)
        self.assertFalse(missing_family["ok"])
        self.assertIn("missing_mainline_packet_family_coverage", missing_family["reasons"])
        self.assertEqual(missing_family["missing_packet_families"], ["review.terminal_backward_replay"])

        wrong_first_packet_package = {
            **baseline_package,
            "first_packet_failure": {
                "blocker_class": "early_terminal_evidence_requirement",
                "terminal_replay_fields_required_at_first_packet": True,
                "expected_current_disposition": "valid_terminal_gate_block",
            },
        }
        wrong_first_packet = _contract_surface_reduction_baseline_ok(wrong_first_packet_package)
        self.assertFalse(wrong_first_packet["ok"])
        self.assertIn("first_packet_still_requires_terminal_replay_fields", wrong_first_packet["reasons"])
        self.assertIn(
            "first_packet_failure_disposition_not_reduced_contract_invalid",
            wrong_first_packet["reasons"],
        )

    def test_historical_skillguard_flowguard_artifact_block_is_not_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            ledger, packet_id, worker = core_runtime_scenarios._base_ledger()
            ledger["run_root"] = temp_root
            core_runtime.ack_lease(ledger, worker, packet_id)
            core_runtime.submit_result(
                ledger,
                worker,
                packet_id,
                core_runtime_scenarios._role_result_body("Historical SkillGuard worker result replay."),
            )
            flowguard_packet = core_runtime_scenarios._open_packet_by_kind(ledger, "flowguard_check")
            _write_historical_flowguard_evidence_artifact(
                ledger,
                flowguard_packet,
                decision="missing_code_contract",
            )
            flowguard_lease = core_runtime.lease_agent(
                ledger,
                "flowguard_operator",
                agent_id="historical-skillguard-flowguard",
                packet_id=flowguard_packet,
            )
            core_runtime.assign_packet(ledger, flowguard_packet, flowguard_lease)
            core_runtime.ack_lease(ledger, flowguard_lease, flowguard_packet)
            core_runtime.open_authorized_input_materials_for_role(ledger, flowguard_packet, flowguard_lease)

            result_id = core_runtime.submit_result(
                ledger,
                flowguard_lease,
                flowguard_packet,
                core_runtime_scenarios._flowguard_result_body(
                    "Historical FlowGuard body claims pass while artifact blocks."
                ),
            )
            result = ledger["results"][result_id]

            self.assertEqual(result["status"], "mechanical_contract_blocked")
            self.assertIn(
                "flowguard_evidence.json.model_test_alignment_report.decision",
                result["missing_required_fields"],
            )
            self.assertFalse(
                [
                    packet
                    for packet in ledger["packets"].values()
                    if packet["envelope"].get("packet_kind") == "review"
                ]
            )

    def test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence(self) -> None:
        root = self.make_project()
        run_a = self.write_minimal_run(root, "run-historical-a")
        run_b = self.write_minimal_run(root, "run-historical-b")
        self.write_current_focus(root, run_b)

        stale_snapshot = {
            "run_id": "run-historical-a",
            "display_status": "complete",
            "router_pending_action": {"action_type": "relay_current_node_packet"},
            "terminal_ledger_status": "open",
        }
        snapshot_gate = _historical_snapshot_claim_is_authoritative(root, stale_snapshot)
        self.assertFalse(snapshot_gate["authoritative"])
        self.assertIn("snapshot_run_id_not_current", snapshot_gate["reasons"])
        self.assertIn("display_projection_conflicts_with_router_pending_action", snapshot_gate["reasons"])

        proof_dir = root / ".flowpilot" / "historical-proofs"
        proof_paths = test_tier_background.artifact_paths(proof_dir, "historical_peer_proof")
        proof_paths["combined"].parent.mkdir(parents=True, exist_ok=True)
        proof_paths["out"].write_text("historical peer proof passed\n", encoding="utf-8")
        proof_paths["err"].write_text("", encoding="utf-8")
        proof_paths["combined"].write_text("historical peer proof passed\n", encoding="utf-8")
        proof_paths["exit"].write_text("0\n", encoding="utf-8")
        proof_paths["meta"].write_text(
            json.dumps(
                {
                    "name": "historical_peer_proof",
                    "status": "passed",
                    "exit_code": 0,
                    "proof_reused": False,
                    "run_id": run_a.name,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        stale_proof = _package_background_proof_is_current(root, proof_dir, "historical_peer_proof")
        self.assertEqual(stale_proof["status"], "passed")
        self.assertFalse(stale_proof["ok"])
        self.assertEqual(stale_proof["run_id"], "run-historical-a")
        self.assertEqual(stale_proof["current_run_id"], "run-historical-b")
        self.assertIn("proof_run_id_not_current", stale_proof["reasons"])

        progress_paths = test_tier_background.artifact_paths(proof_dir, "historical_progress_only")
        progress_paths["combined"].write_text("model checks still running\n", encoding="utf-8")
        progress = test_tier_background.classify_background_artifact(proof_dir, "historical_progress_only")
        self.assertEqual(progress["status"], "progress_only")
        self.assertFalse(progress["ok"])
        self.assertIn("missing_exit", progress["reasons"])

    def test_host_role_lifecycle_resume_requires_current_target_rehydrate_evidence(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)
        router.record_external_event(root, "manual_resume_requested")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "load_resume_state")
        router.apply_action(root, "load_resume_state")
        resume_evidence = read_json(run_root / "continuation" / "resume_reentry.json")
        self.assertTrue(resume_evidence["role_rehydration_required"])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "rehydrate_role_bindings")
        target_roles = action["role_keys"]
        missing_payload = self.resume_role_agent_payload(root, action)
        missing_payload["rehydrated_role_bindings"] = missing_payload["rehydrated_role_bindings"][:-1]
        with self.assertRaisesRegex(router.RouterError, "missing rehydrated live role binding records"):
            router.apply_action(root, "rehydrate_role_bindings", missing_payload)

        timeout_payload = self.resume_role_agent_payload(root, router.next_action(root))
        timeout_payload["rehydrated_role_bindings"][0].update(
            {
                "rehydration_result": "live_agent_continuity_confirmed",
                "host_liveness_status": "timeout_unknown",
                "liveness_decision": "confirmed_existing_agent",
                "bounded_wait_result": "timeout_unknown",
                "wait_agent_timeout_treated_as_active": True,
            }
        )
        with self.assertRaisesRegex(router.RouterError, "timeout_unknown|wait_agent_timeout_treated_as_active"):
            router.apply_action(root, "rehydrate_role_bindings", timeout_payload)

        valid_payload = self.resume_role_agent_payload(root, router.next_action(root))
        router.apply_action(root, "rehydrate_role_bindings", valid_payload)
        rehydration = read_json(run_root / "continuation" / "role_binding_recovery_report.json")
        self.assertTrue(rehydration["required_role_bindings_ready"])
        self.assertEqual(rehydration["liveness_preflight"]["roles_checked"], target_roles)
        self.assertFalse(rehydration["liveness_preflight"]["wait_agent_timeout_treated_as_active"])

    def test_relay_lifecycle_and_semantic_contract_packages_block_overclaims(self) -> None:
        replay = start_worker_trace(SyntheticTracePackage(name="historical_relay_done_without_mutation"))
        premature_claim = _package_completion_claim_is_mechanically_supported(replay)
        self.assertFalse(premature_claim["ok"])
        self.assertIn("active_holder_ack_missing", premature_claim["missing"])
        self.assertIn("result_envelope_missing", premature_claim["missing"])

        replay.ack()
        replay.open_packet_body()
        replay.submit_result()
        submitted_claim = _package_completion_claim_is_mechanically_supported(replay)
        self.assertFalse(submitted_claim["ok"])
        self.assertIn("result_body_hash_not_verified", submitted_claim["missing"])

        replay.relay_result()
        replay.open_result_body(role="project_manager")
        final_claim = _package_completion_claim_is_mechanically_supported(replay)
        self.assertTrue(final_claim["ok"], final_claim)

        missing_matrix = _semantic_standard_package_ok(
            {
                "inherited_skill_standard_ids": ["frontend-design.verify.visible_controls"],
                "contract_self_check": "pass",
                "skill_standard_result_matrix": [],
                "approved_waivers": [],
            }
        )
        self.assertFalse(missing_matrix["ok"])
        self.assertIn(
            "missing_standard_result:frontend-design.verify.visible_controls",
            missing_matrix["missing"],
        )

        approved = _semantic_standard_package_ok(
            {
                "inherited_skill_standard_ids": ["frontend-design.verify.visible_controls"],
                "skill_standard_result_matrix": [
                    {
                        "standard_id": "frontend-design.verify.visible_controls",
                        "status": "passed",
                        "evidence_path": "artifacts/visible-control-check.json",
                    }
                ],
                "approved_waivers": [],
            }
        )
        self.assertTrue(approved["ok"], approved)

    def test_install_split_brain_and_ui_projection_packages_do_not_count_as_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-install-split-") as tmp_name:
            root = Path(tmp_name)
            repo_skill = root / "repo" / "flowpilot"
            installed_skill = root / "installed" / "flowpilot"
            repo_skill.mkdir(parents=True)
            installed_skill.mkdir(parents=True)
            (repo_skill / "SKILL.md").write_text("repo source v2\n", encoding="utf-8")
            (installed_skill / "SKILL.md").write_text("installed source v1\n", encoding="utf-8")

            split = _install_split_brain_report(repo_skill, installed_skill)

        self.assertFalse(split["ok"])
        self.assertTrue(split["install_sync_required"])
        self.assertNotEqual(split["repo_digest"], split["installed_digest"])

        state = {
            "run_id": "run-ui-current",
            "route_version": 3,
            "active_node": "node-current",
            "pending_action": {"action_type": "relay_current_node_packet"},
        }
        projection = {
            "run_id": "run-ui-current",
            "route_version": 2,
            "active_node": "node-old",
            "display_status": "complete",
        }
        authority = _display_projection_is_authoritative(state, projection)

        self.assertFalse(authority["authoritative"])
        self.assertIn("projection_route_version_stale", authority["reasons"])
        self.assertIn("projection_active_node_stale", authority["reasons"])
        self.assertIn("router_pending_action_still_authoritative", authority["reasons"])

    def test_windows_filesystem_package_uses_lock_and_partial_json_as_recoverable_mechanical_state(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-windows-fs")
        state_path = router.run_state_path(run_root)
        lock_path = router._json_write_lock_path(state_path)  # type: ignore[attr-defined]
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        router.write_json(
            lock_path,
            {
                "schema_version": "flowpilot.runtime_json_write_lock.v1",
                "path": str(state_path),
                "owner": {"pid": 999999999, "process_name": "historical-fs-fixture"},
                "created_at": "2000-01-01T00:00:00Z",
                "status": "active",
            },
        )

        liveness = router._json_write_lock_liveness(state_path)  # type: ignore[attr-defined]
        self.assertTrue(liveness["exists"])
        self.assertIn(liveness["classification"], {"active_unknown_owner", "stale", "stale_unknown_owner"})
        self.assertFalse(liveness["owner_process_live"])
        self.assertTrue(lock_path.exists())

        partial_path = run_root / "runtime" / "partial_state.json"
        partial_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path.write_text('{"schema_version": "flowpilot.partial", ', encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            json.loads(partial_path.read_text(encoding="utf-8"))

        outside = root.parent / "outside.json"
        with self.assertRaises(ValueError):
            router.project_relative(root, outside)

        self.assertEqual(_sha256(state_path), hashlib.sha256(state_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()

