from __future__ import annotations

import contextlib
import io
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

flowpilot_new = importlib.import_module("flowpilot_new")
flowpilot_new_shared = importlib.import_module("flowpilot_new_shared")
flowpilot_runtime_self_check = importlib.import_module("flowpilot_runtime_self_check")
flowpilot_new_role_commands = importlib.import_module("flowpilot_new_role_commands")
runtime = importlib.import_module("flowpilot_core_runtime.runtime")
fake_e2e = importlib.import_module("flowpilot_core_runtime.fake_e2e")
packet_result_contracts = importlib.import_module("flowpilot_core_runtime.packet_result_contracts")
run_shell = importlib.import_module("flowpilot_core_runtime.run_shell")
entrypoint_runner = importlib.import_module("simulations.run_flowpilot_new_entrypoint_checks")
install_check_common = importlib.import_module("scripts.install_checks.common")


def role_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-runtime-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload)


def flowguard_result_body(summary: str, **fields: object) -> str:
    blocker_class = fields.pop("blocker_class", None)
    recommended_resolution = fields.pop("recommended_resolution", None)
    passed = bool(fields.get("passed", True))
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "flowguard_operator",
        "passed": passed,
        "modeled_boundary": "Current packet and current result only.",
        "blockers": [],
        "pm_suggestion_items": [],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
    }
    if passed is False and blocker_class:
        payload["blockers"] = [
            {
                "blocker_id": "flowguard-blocker-001",
                "blocker_class": blocker_class,
                "recommended_resolution": recommended_resolution or summary,
                "summary": summary,
            }
        ]
    payload.update(fields)
    return json.dumps(payload)


def review_result_body(summary: str, **fields: object) -> str:
    passed = bool(fields.pop("passed", True))
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "human_like_reviewer",
        "passed": passed,
        "findings": [],
        "blockers": [],
        "pm_suggestion_items": [
            "PM decision-support: current minimum gate passes; consider whether a 9/10 quality optimization pass is useful."
        ],
        "contract_self_check": {
            "all_required_fields_present": True,
            "exact_field_names_used": True,
            "empty_required_arrays_explicit": True,
            "runtime_mechanical_validation_passed": True,
            "semantic_sufficiency_reviewed_by_runtime": False,
        },
    }
    payload.update(fields)
    return json.dumps(payload)


def high_standard_contract_body() -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Complete the requested outcome.",
                    "source_user_intent": "sealed_startup_intake",
                    "closure_rule": "Must be satisfied by current evidence, an explicit waiver, or a current blocker.",
                }
            ],
            "acceptance_item_registry": {
                "schema_version": runtime.ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION,
                "items": [
                    {
                        "acceptance_item_id": "acc-001",
                        "source_type": "user_explicit",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Complete the requested outcome.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Later node and terminal packets must cite current evidence or an explicit waiver.",
                        "status": "active",
                    },
                    {
                        "acceptance_item_id": "acc-002",
                        "source_type": "pm_high_standard",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Hold the result to the highest reasonable current-run quality bar.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Later node and terminal packets must cite depth evidence plus review closure.",
                        "status": "active",
                    },
                ],
            },
        }
    )


_PM_REPAIR_OBLIGATION_DISPOSITION_BY_DECISION = {
    "repair_current_scope": "fresh_repair_packet_required",
    "repair_parent_scope": "parent_scope_repair_required",
    "redesign_route": "route_redesign_required",
    "waive_with_authority": "waived_with_authority",
    "stop_for_user": "stop_for_user",
}

_PM_REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION = {
    "repair_current_scope": "flowguard_then_reviewer",
    "repair_parent_scope": "flowguard_then_reviewer",
    "redesign_route": "route_redesign_gate",
    "waive_with_authority": "authority_waiver_gate",
    "stop_for_user": "terminal_user_stop",
}


def pm_repair_body_from_packet(
    packet: dict[str, object],
    *,
    decision: str,
    reason: str,
) -> str:
    packet_body = json.loads(str(packet.get("body") or "{}"))
    payload = dict(packet_body.get("minimal_valid_shape") or {})
    payload["decision"] = decision
    payload["next_action"] = decision
    payload["reason"] = reason
    obligations = packet_body.get("repair_evidence_obligations")
    if isinstance(obligations, list) and obligations:
        payload["repair_obligation_disposition"] = [
            {
                "obligation_id": str(row.get("obligation_id") or ""),
                "disposition": _PM_REPAIR_OBLIGATION_DISPOSITION_BY_DECISION[decision],
                "return_gate": _PM_REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION[decision],
                "evidence_kind": "fresh_current_evidence",
            }
            for row in obligations
            if isinstance(row, dict)
        ]
    return json.dumps(payload)


class FlowPilotNewEntrypointTests(unittest.TestCase):
    def test_fake_e2e_high_standard_contract_matches_packet_contract(self) -> None:
        body = json.loads(
            fake_e2e._body_for_packet(
                {
                    "envelope": {
                        "packet_kind": "task",
                        "route_scope": "high_standard_contract",
                    }
                }
            )
        )

        self.assertIn("requirements", body)
        self.assertIn("acceptance_item_registry", body)
        self.assertNotIn("decision", body)
        self.assertNotIn("pm_visible_summary", body)

    def test_fake_e2e_success_bodies_use_declared_contract_fields(self) -> None:
        packets = [
            {"packet_id": "packet-hs", "envelope": {"packet_kind": "task", "route_scope": "high_standard_contract"}},
            {"packet_id": "packet-discovery", "envelope": {"packet_kind": "task", "route_scope": "discovery"}},
            {"packet_id": "packet-skill", "envelope": {"packet_kind": "task", "route_scope": "skill_standard"}},
            {"packet_id": "packet-plan", "envelope": {"packet_kind": "task", "route_scope": "planning"}},
            {
                "packet_id": "packet-context",
                "envelope": {"packet_kind": "task", "route_scope": "node_acceptance_plan", "route_node_id": "node-001"},
            },
            {
                "packet_id": "packet-replay",
                "envelope": {"packet_kind": "task", "route_scope": "parent_backward_replay", "route_node_id": "node-001"},
            },
            {"packet_id": "packet-node", "envelope": {"packet_kind": "task", "route_scope": "node"}},
            {"packet_id": "packet-flowguard", "envelope": {"packet_kind": "flowguard_check", "route_scope": "node"}},
            {"packet_id": "packet-review", "envelope": {"packet_kind": "review", "route_scope": "node"}},
            {
                "packet_id": "packet-terminal",
                "envelope": {"packet_kind": "review", "route_scope": "terminal_backward_replay"},
            },
            {
                "packet_id": "packet-repair",
                "envelope": {"packet_kind": "pm_repair_decision", "route_scope": "pm_repair_decision"},
            },
            {"packet_id": "packet-pm", "envelope": {"packet_kind": "pm_disposition", "route_scope": "node_pm_disposition"}},
            {
                "packet_id": "packet-pm-flowguard",
                "envelope": {
                    "packet_kind": "pm_flowguard_acceptance",
                    "route_scope": "pm_flowguard_acceptance",
                },
            },
        ]
        covered_families = {runtime._packet_result_family_id(packet) for packet in packets}
        contract_families = {str(row["family_id"]) for row in packet_result_contracts.PACKET_RESULT_CONTRACTS}
        self.assertEqual(contract_families, covered_families)

        for packet in packets:
            with self.subTest(packet=packet["packet_id"]):
                family_id = runtime._packet_result_family_id(packet)
                body = json.loads(fake_e2e._body_for_packet(packet))
                self.assertFalse(
                    packet_result_contracts.undeclared_success_fields_for_family(family_id, body),
                    (family_id, body),
                )
                self.assertFalse(
                    packet_result_contracts.forbidden_success_fields_for_family(family_id, body),
                    (family_id, body),
                )

    def test_split_entrypoint_modules_are_install_required(self) -> None:
        required = set(install_check_common.REQUIRED_FILES)

        for path in (
            "skills/flowpilot/assets/flowpilot_new.py",
            "skills/flowpilot/assets/flowpilot_new_cli.py",
            "skills/flowpilot/assets/flowpilot_new_role_commands.py",
            "skills/flowpilot/assets/flowpilot_new_run_commands.py",
            "skills/flowpilot/assets/flowpilot_new_shared.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
            "skills/flowpilot/assets/flowpilot_runtime_self_check.py",
        ):
            self.assertIn(path, required)

    def test_role_handoff_uses_public_entrypoint_after_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-handoff-entrypoint",
                headless_startup_text="Check split entrypoint handoff.",
                require_formal_ui=False,
            )
            packet_id = str(started["next_action"]["subject_id"])
            dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=packet_id,
                responsibility="pm",
                host_kind="fake",
                agent_id="pm-handoff-agent",
            )
            self.assertTrue(dispatch["ok"], dispatch)

            rendered = json.dumps(dispatch["role_handoff"], sort_keys=True)
            self.assertIn("flowpilot_new.py", rendered)
            self.assertNotIn("flowpilot_new_role_commands.py", rendered)
            self.assertNotIn("flowpilot_new_cli.py", rendered)

    def test_start_run_records_portable_runtime_self_check_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-runtime-self-check",
                headless_startup_text="Check portable FlowPilot runtime self-check.",
                require_formal_ui=False,
            )

            receipt = started["flowpilot_runtime_self_check"]
            receipt_path = Path(receipt["receipt_path"])
            shell = run_shell.load_run_shell(root, run_id="run-runtime-self-check")
            ledger = run_shell.load_run_ledger(shell)

            self.assertTrue(receipt["ok"], receipt)
            self.assertTrue(receipt_path.is_file())
            self.assertFalse(receipt["dev_repo_simulations_required"])
            self.assertEqual(receipt, ledger["flowpilot_runtime_self_check"])
            self.assertTrue((shell.run_root / "runtime" / "flowpilot_runtime_self_check_receipt.json").is_file())

    def test_record_runtime_self_check_receipt_writes_run_scoped_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(
                root,
                "Check portable FlowPilot runtime self-check.",
                "Runtime self-check receipt must be run-scoped.",
                run_id="run-runtime-self-check-direct",
            )

            receipt = flowpilot_new_shared._record_runtime_self_check_receipt(shell)
            ledger = run_shell.load_run_ledger(shell)
            receipt_path = Path(receipt["receipt_path"])

            self.assertTrue(receipt["ok"], receipt)
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(receipt, ledger["flowpilot_runtime_self_check"])
            self.assertEqual(receipt_path, shell.run_root / "runtime" / "flowpilot_runtime_self_check_receipt.json")

    def test_runtime_self_check_does_not_require_target_project_simulations(self) -> None:
        receipt = flowpilot_runtime_self_check.runtime_self_check(assets_root=ASSETS)

        self.assertTrue(receipt["ok"], receipt)
        self.assertFalse(receipt["dev_repo_simulations_required"])
        self.assertNotIn(
            "simulations/run_flowpilot_model_test_alignment_checks.py",
            "\n".join(receipt["required_runtime_assets"]),
        )

    def test_open_packet_returns_submission_checklist_from_packet_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-open-packet-checklist",
                headless_startup_text="Check open-packet submission checklist.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-open-packet-checklist")
            ledger = run_shell.load_run_ledger(shell)
            packet_id = runtime.issue_task_packet(
                ledger,
                "pm",
                "Check role-facing submission checklist.",
                json.dumps(
                    {
                        "schema_version": "flowpilot.test_packet.v1",
                        "required_result_body_fields": ["decision", "reason", "repair_obligation_disposition"],
                        "conditional_required_fields": {
                            "repair_current_scope": ["repair_obligation_disposition"]
                        },
                        "forbidden_fields": ["summary"],
                        "minimal_valid_shape": {
                            "decision": "repair_current_scope",
                            "reason": "Concrete PM repair reason.",
                            "repair_obligation_disposition": [
                                {
                                    "obligation_id": "obligation-001",
                                    "disposition": "fresh_repair_packet_required",
                                    "return_gate": "flowguard_then_reviewer",
                                    "evidence_kind": "fresh_current_evidence",
                                }
                            ],
                        },
                    }
                ),
                packet_kind="pm_repair_decision",
                route_scope="pm_repair_decision",
            )
            run_shell.save_run_ledger(shell, ledger)

            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="pm",
                agent_id="pm-checklist-agent",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            opened = flowpilot_new.open_packet(root, lease_id=lease_id, packet_id=packet_id)

            checklist = opened["submission_checklist"]
            self.assertEqual(checklist["schema_version"], "black_box_flowpilot.submission_checklist.v1")
            self.assertEqual(
                checklist["required_result_body_fields"],
                ["decision", "reason", "repair_obligation_disposition"],
            )
            self.assertEqual(checklist["result_skeleton"]["decision"], "repair_current_scope")
            self.assertIn("repair_obligation_disposition", checklist["result_skeleton"])
            self.assertNotIn("forbidden_fields", checklist)
            self.assertFalse(opened["controller_may_read_submission_checklist"])

    def test_open_packet_submission_checklist_projects_current_handoff_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-open-packet-handoff-checklist",
                headless_startup_text="Check complete handoff checklist projection.",
                require_formal_ui=False,
            )
            source_packet_id = str(started["next_action"]["subject_id"])
            _, source_result_id = self._complete_open_packet(
                root,
                packet_id=source_packet_id,
                responsibility="pm",
                agent_id="pm-source-result-agent",
                body=role_result_body("Source result for authorized-read checklist."),
            )
            shell = run_shell.load_run_shell(root, run_id="run-open-packet-handoff-checklist")
            ledger = run_shell.load_run_ledger(shell)
            packet_id = runtime.issue_task_packet(
                ledger,
                "flowguard_operator",
                "Check handoff-derived submission checklist.",
                json.dumps({"schema_version": "flowpilot.test_packet.v1"}),
                packet_kind="flowguard_check",
                route_scope="post_result",
                authorized_result_reads=[
                    {
                        "result_id": source_result_id,
                        "allowed_roles": ["flowguard_operator"],
                        "required_before_submit": True,
                        "purpose": "semantic_recheck_input",
                    }
                ],
            )
            run_shell.save_run_ledger(shell, ledger)

            lease_id = self._lease_packet(
                root,
                packet_id=packet_id,
                responsibility="flowguard_operator",
                agent_id="flowguard-checklist-agent",
            )
            flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
            opened = flowpilot_new.open_packet(root, lease_id=lease_id, packet_id=packet_id)

            checklist = opened["submission_checklist"]
            report_contract = opened["packet"]["current_handoff_contract"]["required_report_contract"]
            output_contract = opened["packet"]["output_contract"]
            self.assertTrue(checklist["current_handoff_contract_inspected"])
            self.assertEqual(checklist["contract_family_id"], "flowguard_check.post_result")
            self.assertEqual(
                checklist["required_result_body_fields"],
                list(packet_result_contracts.required_fields_for_family("flowguard_check.post_result")),
            )
            self.assertEqual(checklist["required_child_fields"], list(report_contract["required_child_fields"]))
            self.assertEqual(checklist["explicit_array_fields"], list(report_contract["explicit_array_fields"]))
            self.assertEqual(checklist["non_empty_array_fields"], list(report_contract["non_empty_array_fields"]))
            self.assertNotIn("forbidden_fields", checklist)
            self.assertNotIn("forbidden_result_body_fields", checklist)
            self.assertNotIn("forbidden_result_body_fields", report_contract)
            self.assertEqual(
                report_contract["output_contract"]["forbidden_fields"],
                list(packet_result_contracts.forbidden_fields_for_family("flowguard_check.post_result")),
            )
            self.assertEqual(checklist["result_skeleton"], report_contract["minimal_valid_shape"])
            self.assertEqual(checklist["branch_valid_shapes"], report_contract["branch_valid_shapes"])
            self.assertEqual(
                report_contract["allowed_value_options"],
                packet_result_contracts.allowed_value_options_json_for_family("flowguard_check.post_result"),
            )
            self.assertEqual(output_contract["allowed_value_options"], report_contract["allowed_value_options"])
            self.assertEqual(
                report_contract["allowed_value_options"]["reviewed_by_role"],
                ["flowguard_operator"],
            )
            self.assertEqual(
                report_contract["allowed_value_options"]["passed"],
                [True, False],
            )
            self.assertEqual(checklist["required_authorized_result_read_ids"], [source_result_id])
            self.assertEqual(checklist["required_authorized_read_count"], 1)
            self.assertTrue(checklist["all_required_authorized_result_bodies_must_be_opened_before_submit"])
            self.assertIn(source_result_id, checklist["input_material_manifest"]["required_authorized_reads_before_submit"])
            self.assertFalse(opened["controller_may_read_submission_checklist"])

    def test_resolve_stopped_blocker_cli_exposes_reattach_required_recheck(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "flowpilot_new.py"),
                "resolve-stopped-blocker",
                "--help",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("reattach_required_recheck", completed.stdout)

    def _complete_open_packet(
        self,
        root: Path,
        *,
        packet_id: str,
        responsibility: str,
        agent_id: str,
        body: str,
    ) -> tuple[str, str]:
        lease_id = self._lease_packet(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=agent_id,
        )
        flowpilot_new.ack(root, lease_id=lease_id, packet_id=packet_id)
        flowpilot_new.open_packet(root, lease_id=lease_id, packet_id=packet_id)
        if responsibility == "flowguard_operator":
            self._write_flowguard_evidence_artifact_for_packet(
                root,
                packet_id,
                decision=self._flowguard_artifact_decision_for_body(body),
            )
        result_id = flowpilot_new.submit_result(
            root,
            lease_id=lease_id,
            packet_id=packet_id,
            body=body,
        )["result_id"]
        return lease_id, result_id

    def _flowguard_artifact_decision_for_body(self, body: str) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return "blocked"
        if isinstance(payload, dict) and payload.get("passed") is False:
            return "blocked"
        return "pass"

    def _write_flowguard_evidence_artifact_for_packet(
        self,
        root: Path,
        packet_id: str,
        *,
        decision: str,
    ) -> Path:
        shell = run_shell.load_run_shell(root)
        ledger = run_shell.load_run_ledger(shell)
        packet = ledger["packets"][packet_id]
        path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
        self.assertIsNotNone(path)
        assert path is not None
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

    def _lease_packet(
        self,
        root: Path,
        *,
        packet_id: str,
        responsibility: str,
        agent_id: str,
        host_kind: str = "fake",
    ) -> str:
        dispatch = flowpilot_new.dispatch_current_role(
            root,
            packet_id=packet_id,
            responsibility=responsibility,
            host_kind=host_kind,
            agent_id=agent_id,
        )
        self.assertTrue(dispatch["ok"], dispatch)
        return str(dispatch["lease_id"])

    def _open_authorized_result_reads(self, root: Path, *, packet_id: str, lease_id: str) -> None:
        flowpilot_new.open_packet(root, lease_id=lease_id, packet_id=packet_id)

    def _open_packet_by_kind(self, ledger: dict[str, object], packet_kind: str) -> str:
        packets = ledger["packets"]
        self.assertIsInstance(packets, dict)
        for packet_id, packet in packets.items():
            self.assertIsInstance(packet, dict)
            envelope = packet["envelope"]
            self.assertIsInstance(envelope, dict)
            if envelope.get("packet_kind", "task") == packet_kind and packet.get("status") == "open":
                return str(packet_id)
        self.fail(f"missing open {packet_kind} packet")

    def test_start_rehearsal_reuses_old_startup_ui_and_enters_new_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.start_run(
                root,
                run_id="run-new-entry",
                headless_startup_text="Build a tiny project through new FlowPilot.",
                require_formal_ui=False,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["mode"], "rehearsal")
            self.assertEqual(result["next_action"]["action_type"], "dispatch_current_role")
            self.assertEqual(result["next_action"]["responsibility"], "pm")
            self.assertEqual(result["progress_fraction"]["display"], "0/1")
            self.assertEqual(result["status"]["progress_fraction"]["display"], "0/1")
            shell = run_shell.load_run_shell(root, run_id="run-new-entry")
            ledger = run_shell.load_run_ledger(shell)
            self.assertTrue(ledger["startup_intake"]["current_run_authority"])
            self.assertTrue(ledger["contract_frozen"])
            self.assertEqual(ledger["active_route_version"], 1)
            self.assertEqual(len(ledger["packets"]), 1)
            packet = next(iter(ledger["packets"].values()))
            self.assertEqual(packet["envelope"]["responsibility"], "pm")
            rendered = json.dumps(result["status"], sort_keys=True)
            self.assertNotIn("Build a tiny project through new FlowPilot.", rendered)
            self.assertIn("flowpilot_startup_intake.ps1", " ".join(flowpilot_new.startup_ui_command(root, "run-new-entry")[0]))

    def test_manual_resume_uses_lifecycle_guard_without_heartbeat_or_role_prewarm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-lifecycle-resume",
                headless_startup_text="Exercise current lifecycle resume.",
                require_formal_ui=False,
            )

            resumed = flowpilot_new.resume(root, reason="manual_resume")
            shell = run_shell.load_run_shell(root, run_id="run-lifecycle-resume")
            ledger = run_shell.load_run_ledger(shell)

            self.assertEqual(resumed["next_action"]["action_type"], "dispatch_current_role")
            self.assertEqual(resumed["next_action"]["responsibility"], "pm")
            self.assertEqual(resumed["foreground_duty"]["action"], "process_next_action")
            self.assertEqual(ledger["lifecycle"]["resume_source"], "manual_resume")
            self.assertTrue(ledger.get("lifecycle_guard_history"))
            self.assertEqual(ledger.get("role_assignments"), {})
            self.assertEqual(ledger.get("leases"), {})
            rendered = json.dumps({"result": resumed, "ledger": ledger}, sort_keys=True)
            self.assertNotIn("heartbeat", rendered.lower())

            packet_id = resumed["next_action"]["subject_id"]
            dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=packet_id,
                responsibility="pm",
                host_kind="fake",
                agent_id="pm-agent",
            )
            self.assertTrue(dispatch["ok"], dispatch)
            self.assertEqual(dispatch["role_assignment"]["packet_id"], packet_id)
            self.assertEqual(dispatch["role_assignment"]["responsibility"], "pm")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(len(ledger["role_assignments"]), 1)
            self.assertEqual({row["responsibility"] for row in ledger["role_assignments"].values()}, {"pm"})
            self.assertEqual(len(ledger["leases"]), 1)
            lease_id = str(dispatch["lease_id"])
            self.assertEqual(ledger["leases"][lease_id]["responsibility"], "pm")
            self.assertEqual(ledger["leases"][lease_id]["packet_id"], packet_id)
            self.assertEqual(set(ledger["role_continuity"]["roles"]), {"pm"})

    def test_fake_end_to_end_rehearsal_reaches_final_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e",
                startup_text="Build and validate a toy command.",
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertEqual(result["next_action"]["action_type"], "terminal_complete")
            shell = run_shell.load_run_shell(root, run_id="run-e2e")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(next(iter(ledger["reviews"].values()))["decision"], "accept")
            self.assertEqual(next(iter(ledger["flowguard_work_orders"].values()))["modeled_target"], "development_process")
            packet_kinds = [packet["envelope"].get("packet_kind", "task") for packet in ledger["packets"].values()]
            route_scopes = [packet["envelope"].get("route_scope", "") for packet in ledger["packets"].values()]
            self.assertTrue(
                all(packet["envelope"].get("current_handoff_contract") for packet in ledger["packets"].values())
            )
            review_packets = [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("packet_kind") == "review"
            ]
            self.assertTrue(review_packets)
            ordinary_review_packets = [
                packet
                for packet in review_packets
                if packet["envelope"].get("route_scope") != "terminal_backward_replay"
            ]
            for packet in ordinary_review_packets:
                with self.subTest(review_scope=packet["envelope"].get("route_scope")):
                    body = json.loads(packet["body"])
                    requires_flowguard_read = body.get("flowguard_evidence_manifest", {}).get(
                        "matching_flowguard_result_reads_required",
                        True,
                    )
                    has_flowguard_read = any(
                        read.get("purpose") == "matching_flowguard_result_for_review"
                        for read in packet["envelope"].get("authorized_result_reads", [])
                    )
                    if requires_flowguard_read:
                        self.assertTrue(has_flowguard_read)
                    else:
                        self.assertEqual(packet["envelope"].get("route_scope"), "node_acceptance_plan")
                        self.assertFalse(has_flowguard_read)
            terminal_reviews = [
                packet
                for packet in review_packets
                if packet["envelope"].get("route_scope") == "terminal_backward_replay"
            ]
            self.assertEqual(len(terminal_reviews), 1)
            self.assertTrue(ledger["terminal_backward_replays"])
            for expected_scope in (
                "high_standard_contract",
                "discovery",
                "skill_standard",
                "planning",
                "node_acceptance_plan",
                "node",
                "node_pm_disposition",
                "terminal_backward_replay",
            ):
                self.assertIn(expected_scope, route_scopes)
            for expected_kind in ("flowguard_check", "review", "pm_disposition"):
                self.assertIn(expected_kind, packet_kinds)
            self.assertNotIn("validation", packet_kinds)
            self.assertNotIn("closure", packet_kinds)
            self.assertTrue(ledger["system_closures"])
            self.assertEqual(packet_kinds.count("pm_disposition"), len(result["accepted_node_ids"]))
            self.assertEqual(len(ledger["node_acceptance_plans"]), len(result["accepted_node_ids"]))
            self.assertTrue(result["folded_boundaries"])
            self.assertTrue(all(boundary["command"] == "run-until-wait" for boundary in result["folded_boundaries"]))
            self.assertFalse(
                [
                    boundary
                    for boundary in result["folded_boundaries"]
                    if boundary["boundary_class"] not in {"role_dispatch", "terminal"}
                ]
            )
            self.assertEqual(ledger["final_requirement_evidence_matrix"]["status"], "clean")
            self.assertTrue(all(lease["status"] == "closed" for lease in ledger["leases"].values()))
            self.assertTrue(all(lease["ack_received"] for lease in ledger["leases"].values()))
            self.assertTrue(all(lease["packet_id"] for lease in ledger["leases"].values()))
            status = json.loads((shell.run_root / "console" / "status.json").read_text(encoding="utf-8"))
            self.assertFalse(status["sealed_bodies_visible"])
            self.assertFalse([lease for lease in status["leases"] if lease["status"] == "active"])

    def test_fake_end_to_end_parent_replay_is_single_reviewer_closure_before_pm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-parent-replay",
                startup_text="Build and validate a toy command with a parent route.",
                use_parent_route=True,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            shell = run_shell.load_run_shell(root, run_id="run-e2e-parent-replay")
            ledger = run_shell.load_run_ledger(shell)
            parent_replay_packets = [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("packet_kind") == "review"
                and packet["envelope"].get("route_scope") == "parent_backward_replay"
            ]
            self.assertEqual(len(parent_replay_packets), 1)
            parent_replay_packet = parent_replay_packets[0]
            second_reviews = [
                packet
                for packet in ledger["packets"].values()
                if packet["envelope"].get("packet_kind") == "review"
                and packet["packet_id"] != parent_replay_packet["packet_id"]
                and packet["envelope"].get("subject_id") == parent_replay_packet["packet_id"]
            ]
            self.assertEqual(second_reviews, [])
            replay_result_id = parent_replay_packet["accepted_result_id"]
            replay_result = ledger["results"][replay_result_id]
            self.assertEqual(replay_result["status"], "accepted")
            self.assertTrue(ledger["parent_backward_replays"])
            replay_record = next(iter(ledger["parent_backward_replays"].values()))
            self.assertEqual(replay_record["source_review_packet_id"], parent_replay_packet["packet_id"])
            self.assertEqual(replay_record["source_review_result_id"], replay_result_id)
            self.assertEqual(replay_record["reviewed_by_role"], "human_like_reviewer")
            reviewed_rows = [
                row
                for row in ledger["final_requirement_evidence_matrix"]["rows"]
                if row["kind"] == "parent_backward_review"
            ]
            self.assertEqual(len(reviewed_rows), 1)
            self.assertEqual(reviewed_rows[0]["status"], "covered")

    def test_fake_end_to_end_contract_chaos_reissues_missing_fields_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-contract-chaos",
                startup_text="Build and validate a toy command with contract chaos.",
                inject_contract_faults=True,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            blocks = result["mechanical_contract_blocks"]
            families = {block["contract_family_id"] for block in blocks}
            self.assertTrue(
                {
                    "task.high_standard_contract",
                    "task.skill_standard",
                    "task.node_acceptance_plan",
                    "flowguard_check.post_result",
                    "review.any_current_subject",
                    "review.terminal_backward_replay",
                    "pm_disposition.node_pm_disposition",
                }.issubset(families),
                blocks,
            )
            high_standard = next(block for block in blocks if block["contract_family_id"] == "task.high_standard_contract")
            self.assertIn("requirements", high_standard["missing_required_fields"])
            self.assertIn("overall_contract", high_standard["forbidden_fields_seen"])
            self.assertIn("contract_rows", high_standard["forbidden_fields_seen"])
            disposition = next(block for block in blocks if block["contract_family_id"] == "pm_disposition.node_pm_disposition")
            self.assertEqual(
                set(disposition["missing_required_fields"]),
                {
                    "reason",
                    "acceptance_item_disposition",
                },
            )
            self.assertEqual(disposition["forbidden_fields_seen"], ["summary"])
            flowguard_block = next(block for block in blocks if block["contract_family_id"] == "flowguard_check.post_result")
            self.assertIn("passed", flowguard_block["missing_required_fields"])
            self.assertIn("decision", flowguard_block["forbidden_fields_seen"])
            review_block = next(block for block in blocks if block["contract_family_id"] == "review.any_current_subject")
            self.assertIn("passed", review_block["missing_required_fields"])
            self.assertIn("reviewed_by_role", review_block["missing_required_fields"])
            self.assertIn("contract_self_check", review_block["missing_required_fields"])
            self.assertIn("decision", review_block["forbidden_fields_seen"])
            shell = run_shell.load_run_shell(root, run_id="run-e2e-contract-chaos")
            ledger = run_shell.load_run_ledger(shell)
            self.assertTrue(
                any(
                    packet.get("status") == "superseded_after_repair"
                    for packet in ledger["packets"].values()
                )
            )

    def test_fake_end_to_end_flowguard_consistency_chaos_reissues_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-flowguard-consistency-chaos",
                startup_text="Build and validate a toy command with FlowGuard consistency chaos.",
                inject_consistency_faults=True,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertIn(
                "flowguard_check.post_result",
                set(result["injected_consistency_fault_families"]),
            )
            blocks = [
                block
                for block in result["mechanical_contract_blocks"]
                if block["contract_family_id"] == "flowguard_check.post_result"
                and "evidence_consistency" in block["quarantine_reason"]
            ]
            self.assertTrue(blocks, result["mechanical_contract_blocks"])

    def test_fake_end_to_end_flowguard_artifact_chaos_reissues_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-flowguard-artifact-chaos",
                startup_text="Build and validate a toy command with FlowGuard artifact chaos.",
                inject_artifact_consistency_faults=True,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertIn(
                "flowguard_check.post_result",
                set(result["injected_artifact_consistency_fault_families"]),
            )
            blocks = [
                block
                for block in result["mechanical_contract_blocks"]
                if block["contract_family_id"] == "flowguard_check.post_result"
                and "flowguard_evidence.json.model_test_alignment_report.decision"
                in block["missing_required_fields"]
            ]
            self.assertTrue(blocks, result["mechanical_contract_blocks"])

    def test_fake_end_to_end_flowguard_formal_artifact_fault_modes_are_explicit(self) -> None:
        fault_modes = (
            ("missing", "flowguard_evidence.json"),
            ("wrong_path", "flowguard_evidence.json"),
            ("invalid_json", "flowguard_evidence.json"),
            ("missing_decision", "flowguard_evidence.json.model_test_alignment_report.decision"),
            ("wrong_decision", "flowguard_evidence.json.model_test_alignment_report.decision"),
            ("blocked_decision", "flowguard_evidence.json.model_test_alignment_report.decision"),
        )
        for mode, missing_field in fault_modes:
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    result = flowpilot_new.run_fake_e2e(
                        root,
                        run_id=f"run-e2e-flowguard-artifact-{mode.replace('_', '-')}",
                        startup_text=f"Build and validate a toy command with FlowGuard artifact fault {mode}.",
                        flowguard_artifact_fault_mode=mode,
                    )

                    self.assertTrue(result["ok"], result)
                    self.assertEqual(result["closure"]["decision"], "complete")
                    self.assertEqual(
                        result["injected_flowguard_artifact_fault_modes"][0]["mode"],
                        mode,
                    )
                    blocks = [
                        block
                        for block in result["mechanical_contract_blocks"]
                        if block["contract_family_id"] == "flowguard_check.post_result"
                        and missing_field in block["missing_required_fields"]
                    ]
                    self.assertTrue(blocks, result["mechanical_contract_blocks"])

    def test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-terminal-replay-blocker",
                startup_text="Build and validate a toy command with terminal replay blocker.",
                inject_terminal_replay_blocker=True,
            )

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "blocked")
            self.assertEqual(result["injected_terminal_replay_blockers"][0]["status"], "review_blocked")
            self.assertFalse(
                [
                    block
                    for block in result["mechanical_contract_blocks"]
                    if block["contract_family_id"] == "review.terminal_backward_replay"
                ],
                result["mechanical_contract_blocks"],
            )
            self.assertFalse(
                [
                    block
                    for block in result["mechanical_contract_blocks"]
                    if block["contract_family_id"] == "pm_repair_decision.pm_repair_decision"
                ],
                result["mechanical_contract_blocks"],
            )
            terminal_blockers = [
                blocker
                for blocker in result["active_blockers"].values()
                if blocker.get("route_scope") == "terminal_backward_replay"
            ]
            self.assertTrue(terminal_blockers, result["active_blockers"])
            self.assertIn("delivered-product signposting", terminal_blockers[0]["recommended_resolution"])
            self.assertEqual(result["next_action"]["action_type"], "dispatch_current_role")
            self.assertEqual(result["next_action"]["responsibility"], "pm")

    def test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = flowpilot_new.run_fake_e2e(
                root,
                run_id="run-e2e-terminal-replay-repair",
                startup_text="Build and validate a toy command with terminal replay repair.",
                inject_terminal_replay_blocker=True,
                repair_terminal_replay_blocker=True,
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["closure"]["decision"], "complete")
            self.assertEqual(result["injected_terminal_replay_blockers"][0]["status"], "review_blocked")
            self.assertFalse(
                [
                    block
                    for block in result["mechanical_contract_blocks"]
                    if block["contract_family_id"] == "review.terminal_backward_replay"
                ],
                result["mechanical_contract_blocks"],
            )
            terminal_blockers = [
                blocker
                for blocker in result["active_blockers"].values()
                if blocker.get("route_scope") == "terminal_backward_replay"
            ]
            self.assertTrue(terminal_blockers, result["active_blockers"])
            self.assertEqual(terminal_blockers[0]["status"], "cleared")
            supplemental_rows = result["final_route_wide_gate_ledger"]["supplemental_repair_closure"]
            self.assertTrue(supplemental_rows)
            self.assertEqual(supplemental_rows[0]["contract_id"], "terminal-supplemental-repair-r1")
            self.assertEqual(supplemental_rows[0]["status"], "covered")
            self.assertEqual(result["final_route_wide_gate_ledger"]["unresolved"], [])
            self.assertEqual(result["next_action"]["action_type"], "terminal_complete")

    def test_ack_only_and_pm_only_result_do_not_reach_terminal_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-no-shortcut",
                headless_startup_text="Exercise no-shortcut closure.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-no-shortcut")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))
            dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                host_kind="fake",
                agent_id="pm-agent",
            )
            self.assertTrue(dispatch["ok"], dispatch)
            pm_lease = str(dispatch["lease_id"])
            flowpilot_new.ack(root, lease_id=pm_lease, packet_id=pm_packet)

            ack_only_status = flowpilot_new.status(root)
            self.assertEqual(ack_only_status["next_action"]["action_type"], "wait_for_result")
            self.assertEqual(ack_only_status["status"]["closure"]["decision"], "not_attempted")

            after_pm = flowpilot_new.submit_result(
                root,
                lease_id=pm_lease,
                packet_id=pm_packet,
                body=high_standard_contract_body(),
            )
            self.assertEqual(after_pm["next_action"]["action_type"], "dispatch_current_role")
            self.assertEqual(after_pm["next_action"]["responsibility"], "flowguard_operator")
            self.assertNotEqual(after_pm["next_action"]["action_type"], "terminal_complete")
            after_pm_status = flowpilot_new.status(root)
            self.assertEqual(after_pm_status["status"]["closure"]["decision"], "not_attempted")
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][pm_packet]["status"], "result_submitted")
            flowguard_packet = self._open_packet_by_kind(ledger, "flowguard_check")
            self.assertEqual(flowguard_packet, after_pm["next_action"]["subject_id"])
            flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
            policy = flowguard_body["evidence_output_policy"]
            self.assertIn(f"/evidence/flowguard/{flowguard_packet}", policy["run_local_evidence_root"])
            self.assertTrue(policy["required_for_formal_run"])
            self.assertIn("simulations/meta_thin_parent_results.json", policy["tracked_baseline_paths_forbidden_unless_explicit_baseline_update"])
            self.assertNotIn("recommended_runner_commands", flowguard_body)
            self.assertIn("Simulate the current route", flowguard_body["instruction"])
            matrix = flowguard_body["subject_stage_evidence_matrix"]
            self.assertEqual(matrix["family_id"], "task.high_standard_contract")
            self.assertEqual(matrix["lifecycle_stage"], "preplanning_contract_definition")
            self.assertIn("requirements", matrix["current_required_fields"])
            self.assertIn("acceptance_item_registry", matrix["current_required_fields"])
            self.assertNotIn("moved_fields", matrix)
            self.assertNotIn("deleted_fields", matrix)
            targets = " ".join(flowguard_body["modeled_subject_policy"]["required_simulation_targets"])
            self.assertIn("requirements list defines current", targets)
            self.assertIn("acceptance_item_registry.items records active acceptance items", targets)
            self.assertNotIn("validation/check evidence freshness", targets)

    def test_resolve_stopped_blocker_requires_explicit_user_request_before_reissue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = flowpilot_new.start_run(
                root,
                run_id="run-stopped-blocker",
                headless_startup_text="Exercise stopped blocker recovery.",
                require_formal_ui=False,
            )
            pm_packet = started["next_action"]["subject_id"]
            pm_dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                host_kind="fake",
                agent_id="pm-agent",
            )
            self.assertTrue(pm_dispatch["ok"], pm_dispatch)
            pm_lease = str(pm_dispatch["lease_id"])
            flowpilot_new.ack(root, lease_id=pm_lease, packet_id=pm_packet)
            self._open_authorized_result_reads(root, packet_id=pm_packet, lease_id=pm_lease)
            flowpilot_new.submit_result(
                root,
                lease_id=pm_lease,
                packet_id=pm_packet,
                body=high_standard_contract_body(),
            )
            shell = run_shell.load_run_shell(root, run_id="run-stopped-blocker")
            ledger = run_shell.load_run_ledger(shell)
            flowguard_packet = self._open_packet_by_kind(ledger, "flowguard_check")
            flowguard_lease = self._lease_packet(
                root,
                packet_id=flowguard_packet,
                responsibility="flowguard_operator",
                agent_id="flowguard-agent",
            )
            flowpilot_new.ack(root, lease_id=flowguard_lease, packet_id=flowguard_packet)
            self._open_authorized_result_reads(root, packet_id=flowguard_packet, lease_id=flowguard_lease)
            self._write_flowguard_evidence_artifact_for_packet(root, flowguard_packet, decision="blocked")
            flowpilot_new.submit_result(
                root,
                lease_id=flowguard_lease,
                packet_id=flowguard_packet,
                body=flowguard_result_body(
                    "FlowGuard identified a blocker that needs a user decision.",
                    passed=False,
                    blocker_class="flowguard_failure",
                    recommended_resolution="needs user decision",
                ),
            )
            ledger = run_shell.load_run_ledger(shell)
            blocker_id = next(iter(ledger["active_blockers"]))
            repair_packet = ledger["active_blockers"][blocker_id]["pm_repair_packet_id"]
            repair_lease = self._lease_packet(
                root,
                packet_id=repair_packet,
                responsibility="pm",
                agent_id="pm-repair",
            )
            flowpilot_new.ack(root, lease_id=repair_lease, packet_id=repair_packet)
            self._open_authorized_result_reads(root, packet_id=repair_packet, lease_id=repair_lease)
            ledger = run_shell.load_run_ledger(shell)
            flowpilot_new.submit_result(
                root,
                lease_id=repair_lease,
                packet_id=repair_packet,
                body=pm_repair_body_from_packet(
                    ledger["packets"][repair_packet],
                    decision="stop_for_user",
                    reason="Need explicit user decision.",
                ),
            )

            resumed = flowpilot_new.resume(root, reason="plain_resume")
            with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "explicit user request"):
                flowpilot_new.resolve_stopped_blocker(
                    root,
                    blocker_id=blocker_id,
                    resolution="reissue_pm_repair_decision",
                    reason="Plain resume must not continue current repair.",
                )
            recovered = flowpilot_new.resolve_stopped_blocker(
                root,
                blocker_id=blocker_id,
                resolution="reissue_pm_repair_decision",
                reason="User selected continued repair.",
                user_requested=True,
            )
            ledger = run_shell.load_run_ledger(shell)
            fresh_packet = ledger["packets"][recovered["recovery"]["fresh_packet_id"]]

            self.assertEqual(resumed["next_action"]["action_type"], "wait_for_resume")
            self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "active")
            self.assertNotEqual(fresh_packet["packet_id"], repair_packet)
            self.assertEqual(fresh_packet["envelope"]["packet_kind"], "pm_repair_decision")
            self.assertTrue(recovered["recovery"]["user_requested"])
            self.assertEqual(recovered["next_action"]["action_type"], "dispatch_current_role")

    def test_flowguard_operator_is_leased_through_its_own_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-symmetric",
                headless_startup_text="Exercise symmetric packet flow.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-symmetric")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))

            with self.assertRaisesRegex(Exception, "assignment responsibility does not match packet"):
                flowpilot_new.dispatch_current_role(
                    root,
                    packet_id=pm_packet,
                    responsibility="flowguard_operator",
                    host_kind="fake",
                    agent_id="flowguard-agent",
                )

            pm_lease = self._lease_packet(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                agent_id="pm-agent",
            )
            flowpilot_new.ack(root, lease_id=pm_lease, packet_id=pm_packet)
            after_pm = flowpilot_new.submit_result(
                root,
                lease_id=pm_lease,
                packet_id=pm_packet,
                body=high_standard_contract_body(),
            )

            self.assertEqual(after_pm["next_action"]["action_type"], "dispatch_current_role")
            self.assertEqual(after_pm["next_action"]["responsibility"], "flowguard_operator")
            flowguard_packet = after_pm["next_action"]["subject_id"]
            ledger = run_shell.load_run_ledger(shell)
            flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
            self.assertIn(f"/evidence/flowguard/{flowguard_packet}", flowguard_body["evidence_output_policy"]["run_local_evidence_root"])
            self.assertNotIn("recommended_runner_commands", flowguard_body)
            self.assertIn("Simulate the current route", flowguard_body["instruction"])
            self.assertIn("do not mutate routes", flowguard_body["modeled_subject_policy"]["forbidden_authority"])
            flowguard_dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=flowguard_packet,
                responsibility="flowguard_operator",
                host_kind="fake",
                agent_id="flowguard-agent",
            )
            self.assertTrue(flowguard_dispatch["ok"], flowguard_dispatch)
            flowguard_lease = str(flowguard_dispatch["lease_id"])
            flowpilot_new.ack(root, lease_id=flowguard_lease, packet_id=flowguard_packet)
            self._open_authorized_result_reads(root, packet_id=flowguard_packet, lease_id=flowguard_lease)
            self._write_flowguard_evidence_artifact_for_packet(root, flowguard_packet, decision="pass")
            flowpilot_new.submit_result(
                root,
                lease_id=flowguard_lease,
                packet_id=flowguard_packet,
                body=flowguard_result_body("FlowGuard result"),
            )

            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][flowguard_packet]["envelope"]["packet_kind"], "flowguard_check")
            self.assertEqual(ledger["packets"][flowguard_packet]["status"], "accepted")
            self.assertEqual(ledger["leases"][flowguard_lease]["status"], "closed")
            reviewer_packets = [
                packet for packet in ledger["packets"].values() if packet["envelope"].get("packet_kind") == "review"
            ]
            self.assertEqual(len(reviewer_packets), 1)

    def test_reviewer_packet_lease_projection_is_clean_before_and_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-reviewer-clean",
                headless_startup_text="Exercise reviewer lease cleanliness.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-reviewer-clean")
            ledger = run_shell.load_run_ledger(shell)
            pm_packet = next(iter(ledger["packets"]))
            self._complete_open_packet(
                root,
                packet_id=pm_packet,
                responsibility="pm",
                agent_id="pm-agent",
                body=high_standard_contract_body(),
            )
            ledger = run_shell.load_run_ledger(shell)
            flowguard_packet = self._open_packet_by_kind(ledger, "flowguard_check")
            self._complete_open_packet(
                root,
                packet_id=flowguard_packet,
                responsibility="flowguard_operator",
                agent_id="flowguard-agent",
                body=flowguard_result_body("FlowGuard result"),
            )
            ledger = run_shell.load_run_ledger(shell)
            review_packet = self._open_packet_by_kind(ledger, "review")
            reviewer_dispatch = flowpilot_new.dispatch_current_role(
                root,
                packet_id=review_packet,
                responsibility="reviewer",
                host_kind="fake",
                agent_id="reviewer-agent",
            )
            self.assertTrue(reviewer_dispatch["ok"], reviewer_dispatch)
            reviewer_lease = str(reviewer_dispatch["lease_id"])

            before_ack = flowpilot_new.status(root)["status"]
            reviewer_rows = [row for row in before_ack["leases"] if row["lease_id"] == reviewer_lease]
            self.assertEqual(len(reviewer_rows), 1)
            self.assertEqual(reviewer_rows[0]["lease_id"], reviewer_lease)
            self.assertEqual(reviewer_rows[0]["agent_id"], "reviewer-agent")
            self.assertEqual(reviewer_rows[0]["responsibility"], "reviewer")
            self.assertEqual(reviewer_rows[0]["status"], "active")
            self.assertFalse(reviewer_rows[0]["ack_received"])
            self.assertEqual(reviewer_rows[0]["packet_id"], review_packet)

            flowpilot_new.ack(root, lease_id=reviewer_lease, packet_id=review_packet)
            after_ack = flowpilot_new.status(root)["status"]
            reviewer_rows = [row for row in after_ack["leases"] if row["lease_id"] == reviewer_lease]
            self.assertEqual(reviewer_rows[0]["packet_id"], review_packet)
            self.assertTrue(reviewer_rows[0]["ack_received"])

            self._open_authorized_result_reads(root, packet_id=review_packet, lease_id=reviewer_lease)
            flowpilot_new.submit_result(
                root,
                lease_id=reviewer_lease,
                packet_id=review_packet,
                body=review_result_body("Reviewer accepted the FlowGuard-backed result."),
            )
            after_review = flowpilot_new.status(root)["status"]
            self.assertFalse(
                [
                    row
                    for row in after_review["leases"]
                    if row["responsibility"] == "reviewer" and row["status"] == "active"
                ]
            )
            ledger = run_shell.load_run_ledger(shell)
            self.assertEqual(ledger["packets"][review_packet]["status"], "accepted")
            self.assertEqual(ledger["leases"][reviewer_lease]["status"], "closed")
            self.assertTrue(ledger["leases"][reviewer_lease]["ack_received"])
            packet_kinds = [packet["envelope"].get("packet_kind", "task") for packet in ledger["packets"].values()]
            self.assertNotIn("validation", packet_kinds)
            self.assertNotIn("closure", packet_kinds)
            self.assertTrue(ledger["system_closures"])
            self.assertNotEqual(after_review["next_action"].get("responsibility"), "validator")

    def test_status_is_read_only_but_patrol_refreshes_current_run_duty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-status-readonly",
                headless_startup_text="Exercise status read-only behavior.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-status-readonly")
            before = run_shell.load_run_ledger(shell)
            before_history = len(before.get("lifecycle_guard_history") or [])
            before_events = len(before.get("events") or [])

            flowpilot_new.status(root)
            compact_status = flowpilot_new.status(root)
            full_status = flowpilot_new.status(root, full=True)
            after_status = run_shell.load_run_ledger(shell)

            self.assertEqual(len(after_status.get("lifecycle_guard_history") or []), before_history)
            self.assertEqual(len(after_status.get("events") or []), before_events)
            self.assertEqual(compact_status["status_mode"], "compact")
            self.assertEqual(compact_status["status"]["projection"], "compact_controller_status")
            self.assertEqual(full_status["status_mode"], "full")
            self.assertNotEqual(full_status["status"].get("projection"), "compact_controller_status")

            flowpilot_new.patrol(root, sleep_seconds=0)
            after_patrol = run_shell.load_run_ledger(shell)
            self.assertGreater(len(after_patrol.get("lifecycle_guard_history") or []), before_history)

    def test_formal_public_surface_omits_unsupported_side_command_paths(self) -> None:
        unsupported_functions = (
            "complete_flowguard",
            "review",
            "record_validation",
            "close",
            "resolve_role_assignment",
            "lease_agent",
        )
        for name in unsupported_functions:
            self.assertFalse(hasattr(flowpilot_new, name), name)
        for name in ("resolve_role_assignment", "lease_agent"):
            self.assertFalse(hasattr(flowpilot_new_role_commands, name), name)

        direct_help = io.StringIO()
        with self.assertRaises(SystemExit) as help_exit:
            with contextlib.redirect_stdout(direct_help):
                flowpilot_new.main(["--help"])
        self.assertEqual(help_exit.exception.code, 0)
        self.assertIn("run-until-wait", direct_help.getvalue())
        self.assertIn("repair-accepted-packet", direct_help.getvalue())

        direct_error = io.StringIO()
        with self.assertRaises(SystemExit) as error_exit:
            with contextlib.redirect_stderr(direct_error):
                flowpilot_new.main(["complete-flowguard"])
        self.assertEqual(error_exit.exception.code, 2)
        self.assertIn("invalid choice", direct_error.getvalue())

        completed = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("run-until-wait", completed.stdout)
        self.assertIn("dispatch-current-role", completed.stdout)
        self.assertNotIn("resolve-role-assignment", completed.stdout)
        self.assertNotIn("lease-agent", completed.stdout)
        self.assertIn("repair-accepted-packet", completed.stdout)
        self.assertNotIn("run-fake-e2e", completed.stdout)
        self.assertNotIn("headless-startup-text", completed.stdout)
        for command in ("complete-flowguard", "record-validation"):
            self.assertNotIn(command, completed.stdout)

        dispatch_help = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "dispatch-current-role", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(dispatch_help.returncode, 0, dispatch_help.stderr)
        self.assertIn("--agent-id", dispatch_help.stdout)
        self.assertNotIn("--assignment-id", dispatch_help.stdout)
        self.assertIn("{live,fake,dry_run}", dispatch_help.stdout)
        self.assertIn("live=real host-supported role surface", dispatch_help.stdout)
        self.assertIn("role surface", dispatch_help.stdout)
        self.assertIn("Do not invent values outside", dispatch_help.stdout)
        self.assertIn("this menu", dispatch_help.stdout)

        rejected = subprocess.run(
            [sys.executable, str(ASSETS / "flowpilot_new.py"), "--root", str(Path.cwd()), "complete-flowguard"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("invalid choice", rejected.stderr)

        old_lease = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "flowpilot_new.py"),
                "--root",
                str(Path.cwd()),
                "lease-agent",
                "--packet-id",
                "packet-0001",
                "--responsibility",
                "pm",
                "--agent-id",
                "agent-1",
                "--host-kind",
                "fake",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(old_lease.returncode, 0)
        self.assertIn("invalid choice", old_lease.stderr)

    def test_invalid_host_kind_is_rejected_instead_of_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flowpilot_new.start_run(
                root,
                run_id="run-host-kind-reject",
                headless_startup_text="Exercise host kind rejection.",
                require_formal_ui=False,
            )
            shell = run_shell.load_run_shell(root, run_id="run-host-kind-reject")
            ledger = run_shell.load_run_ledger(shell)
            packet_id = next(iter(ledger["packets"]))

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(ASSETS / "flowpilot_new.py"),
                    "--root",
                    str(root),
                    "dispatch-current-role",
                    "--packet-id",
                    packet_id,
                    "--responsibility",
                    "pm",
                    "--host-kind",
                    "codex_background_worker",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("invalid choice", rejected.stderr)

            direct_error = io.StringIO()
            with self.assertRaises(SystemExit) as direct_exit:
                with contextlib.redirect_stderr(direct_error):
                    flowpilot_new.main(
                        [
                            "--root",
                            str(root),
                            "dispatch-current-role",
                            "--packet-id",
                            packet_id,
                            "--responsibility",
                            "pm",
                            "--host-kind",
                            "codex_background_worker",
                        ]
                    )
            self.assertEqual(direct_exit.exception.code, 2)
            self.assertIn("invalid choice", direct_error.getvalue())

    def test_formal_mode_rejects_headless_startup_result_as_formal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_result = flowpilot_new.start_run(
                root,
                run_id="run-formal-source",
                headless_startup_text="Headless text should stay rehearsal-only.",
                require_formal_ui=False,
            )
            result_path = Path(command_result["run"]["run_root"]) / "startup_intake" / "startup_intake_result.json"
            with self.assertRaisesRegex(Exception, "formal FlowPilot startup requires"):
                flowpilot_new._assert_formal_interactive_result(result_path)

    def test_formal_mode_rejects_confirmed_startup_without_background_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "startup_intake_result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "schema_version": "flowpilot.startup_intake_result.v1",
                        "status": "confirmed",
                        "source": "native_wpf_startup_intake",
                        "launch_mode": "interactive_native",
                        "headless": False,
                        "formal_startup_allowed": True,
                        "startup_answers": {"background_collaboration_authorized": False},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(Exception, "background_collaboration_authorized=true required"):
                flowpilot_new._assert_formal_interactive_result(result_path)

    def test_blocked_startup_intake_records_structured_stop_without_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shell = run_shell.create_run_shell(root, "Goal", "Contract", run_id="run-blocked-startup")
            receipt_path = root / "startup_intake_receipt.json"
            result_path = root / "startup_intake_result.json"
            startup_answers = {"background_collaboration_authorized": False}
            receipt_path.write_text(
                json.dumps(
                    {
                        "schema_version": "flowpilot.startup_intake_receipt.v1",
                        "status": "blocked",
                        "source": "native_wpf_startup_intake",
                        "launch_mode": "interactive_native",
                        "headless": False,
                        "formal_startup_allowed": True,
                        "startup_answers": startup_answers,
                        "block_reason": "background_collaboration_required",
                    }
                ),
                encoding="utf-8",
            )
            result_path.write_text(
                json.dumps(
                    {
                        "schema_version": "flowpilot.startup_intake_result.v1",
                        "status": "blocked",
                        "source": "native_wpf_startup_intake",
                        "launch_mode": "interactive_native",
                        "headless": False,
                        "formal_startup_allowed": True,
                        "startup_answers": startup_answers,
                        "receipt_path": str(receipt_path),
                        "controller_visibility": "block_status_only",
                        "block_reason": "background_collaboration_required",
                        "body_text_included": False,
                    }
                ),
                encoding="utf-8",
            )

            flowpilot_new._assert_formal_interactive_result(result_path)
            record = run_shell.record_startup_intake_result(shell, result_path)
            ledger = run_shell.load_run_ledger(shell)

            self.assertEqual(record["status"], "blocked")
            self.assertEqual(runtime.terminal_lifecycle_status(ledger), "stopped_by_user")
            self.assertEqual(ledger["terminal_lifecycle"]["startup_block_reason"], "background_collaboration_required")
            self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_lifecycle")
            self.assertEqual(ledger["packets"], {})
            self.assertIsNone(ledger["active_route_version"])

    def test_flowguard_new_entrypoint_model_is_green_and_catches_hazards(self) -> None:
        result = entrypoint_runner.run_checks()
        self.assertTrue(result["ok"], result)
        self.assertIn("old_router_authority", result["hazard_detection"]["hazards"])
        self.assertIn("monitor_ui_required", result["hazard_detection"]["hazards"])
        self.assertIn("headless_formal_overclaim", result["hazard_detection"]["hazards"])
        self.assertIn("missing_host_kind_menu", result["hazard_detection"]["hazards"])
        self.assertIn("invented_host_kind_value", result["hazard_detection"]["hazards"])
        self.assertIn("active_prompt_historical_role_topology_residue", result["hazard_detection"]["hazards"])
        self.assertIn("tracked_baseline_flowguard_evidence", result["hazard_detection"]["hazards"])
        self.assertIn("nonterminal_stop_allowed", result["hazard_detection"]["hazards"])
        self.assertIn("terminal_without_lifecycle_guard", result["hazard_detection"]["hazards"])
        self.assertTrue(result["target_plan"]["state"]["host_kind_value_menu_presented"])
        self.assertTrue(result["target_plan"]["state"]["flowguard_evidence_run_local"])
        self.assertTrue(result["target_plan"]["state"]["terminal_controller_stop_allowed"])


if __name__ == "__main__":
    unittest.main()
