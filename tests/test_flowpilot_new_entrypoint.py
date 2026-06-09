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
flowpilot_new_role_commands = importlib.import_module("flowpilot_new_role_commands")
runtime = importlib.import_module("flowpilot_core_runtime.runtime")
fake_e2e = importlib.import_module("flowpilot_core_runtime.fake_e2e")
packet_result_contracts = importlib.import_module("flowpilot_core_runtime.packet_result_contracts")
run_shell = importlib.import_module("flowpilot_core_runtime.run_shell")
entrypoint_runner = importlib.import_module("simulations.run_flowpilot_new_entrypoint_checks")
install_check_common = importlib.import_module("scripts.install_checks.common")


def role_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {"decision": "pass", "pm_visible_summary": [summary]}
    payload.update(fields)
    return json.dumps(payload)


def flowguard_result_body(summary: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "flowguard_operator",
        "passed": True,
        "modeled_boundary": "Current packet and current result only.",
        "commands_run": ["python simulations/run_flowpilot_model_test_alignment_checks.py"],
        "counterexamples_or_absence": ["No counterexample in the current modeled boundary."],
        "hard_invariants": ["Current packet-result contracts use only current fields."],
        "skipped_checks": [],
        "model_obligations": ["Current FlowGuard packet report fields are present."],
        "ordinary_test_evidence": ["Targeted new-entrypoint regression."],
        "missing_test_kinds": [],
        "conformance_boundary": "Runtime checks mechanics only.",
        "confidence_boundary": "Scoped to this current packet.",
        "residual_blindspots": [],
        "background_artifact_completion": [],
        "pm_suggestion_items": [],
        "evidence_consistency": {
            "self_check_passed": True,
            "child_reports_all_passed": True,
            "blocking_child_reports": [],
            "hard_evidence_decision": "pass",
        },
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


def review_result_body(summary: str, **fields: object) -> str:
    passed = bool(fields.pop("passed", True))
    payload: dict[str, object] = {
        "pm_visible_summary": [summary],
        "reviewed_by_role": "human_like_reviewer",
        "passed": passed,
        "direct_evidence_paths_checked": ["current result body"],
        "independent_challenge": {
            "scope_restatement": "Review the current packet result against current acceptance criteria.",
            "explicit_and_implicit_commitments": ["current contract fields", "quality sufficient for next gate"],
            "failure_hypotheses": ["The result may satisfy fields without satisfying the task."],
            "challenge_actions": ["Checked current evidence and challenged the strongest likely failure."],
            "blocking_findings": [],
            "non_blocking_findings": [],
            "pass_or_block": "pass" if passed else "block",
            "reroute_request": [],
            "challenge_waivers": [],
        },
        "findings": [],
        "blockers": [],
        "residual_risks": [],
        "pm_suggestion_items": [],
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
                    "evidence_rule": "Direct current evidence or explicit waiver required.",
                    "closure_blocking": True,
                    "report_only_closure_allowed": False,
                }
            ]
        }
    )


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
            {"packet_id": "packet-pm", "envelope": {"packet_kind": "pm_disposition", "route_scope": "node_pm_disposition"}},
        ]

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
        result_id = flowpilot_new.submit_result(
            root,
            lease_id=lease_id,
            packet_id=packet_id,
            body=body,
        )["result_id"]
        return lease_id, result_id

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
            self.assertTrue(
                all(
                    any(
                        read.get("purpose") == "matching_flowguard_result_for_review"
                        for read in packet["envelope"].get("authorized_result_reads", [])
                    )
                    for packet in ordinary_review_packets
                )
            )
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
                    "covered_requirement_ids",
                    "reviewer_absorption",
                    "flowguard_absorption",
                    "residual_risk_disposition",
                    "semantic_downgrade_disposition",
                    "validation_evidence_ids",
                    "waived_requirement_ids",
                },
            )
            self.assertEqual(disposition["forbidden_fields_seen"], ["summary"])
            flowguard_block = next(block for block in blocks if block["contract_family_id"] == "flowguard_check.post_result")
            self.assertIn("passed", flowguard_block["missing_required_fields"])
            self.assertIn("decision", flowguard_block["forbidden_fields_seen"])
            review_block = next(block for block in blocks if block["contract_family_id"] == "review.any_current_subject")
            self.assertIn("passed", review_block["missing_required_fields"])
            self.assertIn("independent_challenge", review_block["missing_required_fields"])
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
                if block["contract_family_id"] in {
                    "flowguard_check.node_prework_flowguard",
                    "flowguard_check.post_result",
                }
                and "evidence_consistency" in block["quarantine_reason"]
            ]
            self.assertTrue(blocks, result["mechanical_contract_blocks"])

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
            self.assertIn("select or create suitable FlowGuard evidence", flowguard_body["instruction"])

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
            flowpilot_new.submit_result(
                root,
                lease_id=flowguard_lease,
                packet_id=flowguard_packet,
                body=flowguard_result_body(
                    "FlowGuard identified a blocker that needs a user decision.",
                    passed=False,
                    blocker_class="needs_user",
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
            flowpilot_new.submit_result(
                root,
                lease_id=repair_lease,
                packet_id=repair_packet,
                body=json.dumps(
                    {
                        "decision": "stop_for_user",
                        "reason": "Need explicit user decision.",
                    }
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
            self.assertIn("select or create suitable FlowGuard evidence", flowguard_body["instruction"])
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
