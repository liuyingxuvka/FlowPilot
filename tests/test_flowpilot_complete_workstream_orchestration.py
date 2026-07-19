from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
SIMULATIONS = ROOT / "simulations"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

host = importlib.import_module("flowpilot_core_runtime.host")
packet_result_contracts = importlib.import_module(
    "flowpilot_core_runtime.packet_result_contracts"
)
review_window_contracts = importlib.import_module(
    "flowpilot_core_runtime.review_window_contracts"
)
role_handoff = importlib.import_module("flowpilot_core_runtime.role_handoff")
runtime = importlib.import_module("flowpilot_core_runtime.runtime")
workstream_runner = importlib.import_module(
    "run_flowpilot_complete_workstream_orchestration_checks"
)


ROLE_CARDS = {
    "pm": ASSETS / "runtime_kit/cards/roles/project_manager.md",
    "worker": ASSETS / "runtime_kit/cards/roles/worker.md",
    "research_worker": ASSETS / "runtime_kit/cards/roles/worker_research_report.md",
    "reviewer": ASSETS / "runtime_kit/cards/roles/human_like_reviewer.md",
    "flowguard_operator": ASSETS / "runtime_kit/cards/roles/flowguard_operator.md",
}


class FlowPilotCompleteWorkstreamOrchestrationTests(unittest.TestCase):
    def test_model_result_paths_are_public_repo_relative(self) -> None:
        report = workstream_runner._implementation_alignment()

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["paths"])
        for path in report["paths"]:
            self.assertFalse(Path(path).is_absolute(), path)
            self.assertNotIn("\\", path)

    def test_every_substantive_role_card_requires_a_complete_numbered_workstream(self) -> None:
        for role, path in ROLE_CARDS.items():
            with self.subTest(role=role):
                text = path.read_text(encoding="utf-8").lower()
                normalized = " ".join(text.split())
                self.assertIn("independently accountable complete workstream", normalized)
                self.assertIn("numbered plan", normalized)
                self.assertIn("workstream_plan_and_completion", normalized)
                self.assertIn("verification", normalized)
                self.assertIn("repair", normalized)
                self.assertIn("integration", normalized)

    def test_runtime_handoff_projects_one_shared_workstream_contract_to_every_role(self) -> None:
        for responsibility in sorted(host.CURRENT_RESPONSIBILITIES):
            with self.subTest(responsibility=responsibility):
                ledger = runtime.new_ledger("Goal", "Acceptance")
                ledger["startup_intake"] = {
                    "sealed": True,
                    "startup_answers": {
                        runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
                    },
                }
                runtime.create_route(ledger, "Route", ["Complete bounded work"])
                packet_id = runtime.issue_task_packet(
                    ledger,
                    responsibility,
                    "Complete current bounded workstream",
                    json.dumps({"instruction": "Complete the assigned work."}),
                    packet_kind=(
                        "flowguard_check"
                        if responsibility == "flowguard_operator"
                        else "task"
                    ),
                )
                lease_id = runtime.lease_agent(
                    ledger,
                    responsibility,
                    agent_id=f"{responsibility}-agent",
                    packet_id=packet_id,
                )
                runtime.assign_packet(ledger, packet_id, lease_id)
                handoff = role_handoff.render_current_packet_handoff(
                    ledger,
                    root=ROOT,
                    script_path=ASSETS / "flowpilot_new.py",
                    run_id="run-complete-workstream",
                    packet_id=packet_id,
                    lease_id=lease_id,
                )
                text = handoff["text"].lower()
                self.assertIn("complete workstream plan and completion", text)
                self.assertIn("specific numbered plan", text)
                self.assertIn("workstream_plan_and_completion", text)
                self.assertIn("role-local flowguard", text)
                self.assertIn("cannot self-approve", text)
                self.assertIn("controller is excluded", text)
                self.assertIn("foreground action ledger", text)

    def test_all_existing_result_families_project_semantic_plan_rows_without_new_family(self) -> None:
        family_ids = tuple(packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY)
        self.assertEqual(len(family_ids), 13)
        for family_id in family_ids:
            with self.subTest(family_id=family_id):
                shape = packet_result_contracts.minimal_valid_shape_for_family(family_id)
                self_check = shape.get("contract_self_check")
                self.assertIsInstance(self_check, dict)
                plan = self_check.get("workstream_plan_and_completion")
                self.assertIsInstance(plan, dict)
                self.assertTrue(plan["plan_written_before_execution"])
                self.assertEqual(
                    [row["step_number"] for row in plan["steps"]],
                    [1, 2, 3, 4],
                )
                self.assertTrue(all(row["status"] == "completed" for row in plan["steps"]))
                self.assertTrue(all(row["evidence_refs"] for row in plan["steps"]))
                self.assertIn("delegation_and_integration", plan)
                self.assertIn("verification", plan)
                self.assertIn("remaining_blockers", plan)
                required_child_fields = packet_result_contracts.required_child_fields_for_family(
                    family_id
                )
                self.assertNotIn(
                    "contract_self_check.workstream_plan_and_completion",
                    required_child_fields,
                )

    def test_terminal_replay_uses_the_same_semantic_section_without_mechanical_requirement(self) -> None:
        family_id = "review.terminal_backward_replay"
        self.assertNotIn(
            "contract_self_check",
            packet_result_contracts.forbidden_fields_for_family(family_id),
        )
        self.assertNotIn(
            "contract_self_check",
            packet_result_contracts.required_fields_for_family(family_id),
        )
        shape = packet_result_contracts.minimal_valid_shape_for_family(family_id)
        self.assertIn(
            "workstream_plan_and_completion",
            shape["contract_self_check"],
        )

    def test_reviewer_audits_plan_rows_against_actual_artifacts(self) -> None:
        challenge = review_window_contracts.review_flow_stage_challenge_rule(
            "worker_node_result_review"
        ).lower()
        for phrase in (
            "workstream_plan_and_completion",
            "actual artifact",
            "numbered step",
            "delegation integration",
            "verification",
            "repair claim",
        ):
            self.assertIn(phrase, challenge)

    def test_leaf_is_complete_workstream_but_pm_authority_is_preserved(self) -> None:
        criteria = " ".join(runtime.ROUTE_DECOMPOSITION_REVIEW_CRITERIA).lower()
        self.assertIn("independently accountable complete workstream", criteria)
        self.assertIn("role-local numbered plan", criteria)
        self.assertIn("worker planning inside the assigned leaf is required", criteria)
        self.assertIn("product scope", criteria)
        self.assertIn("route nodes", criteria)
        self.assertIn("acceptance boundaries", criteria)

    def test_pm_must_disposition_every_sub9_score_without_runtime_autoblock(self) -> None:
        text = ROLE_CARDS["pm"].read_text(encoding="utf-8").lower()
        self.assertIn("every score below `9/10` still requires an explicit current pm disposition", text)
        self.assertIn("do not silently ignore a sub-`9/10` score", text)
        self.assertIn("not itself a reviewer command to open repair work", text)

    def test_pm_records_shared_maintenance_row_through_existing_report_surface(self) -> None:
        text = " ".join(ROLE_CARDS["pm"].read_text(encoding="utf-8").lower().split())
        for phrase in (
            "shared spark-style skill maintenance log",
            "`.codex/skill_maintenance_log.jsonl`",
            "`skill: flowpilot`",
            "main work summary",
            "workspace root",
            "current `run_id`",
            "current run folder",
            "selected log path and entry id",
            "`contract_self_check.workstream_plan_and_completion`",
            "do not create a new result field or packet family",
            "bookkeeping only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn(
            "do not turn it into a route node, review gate, flowguard gate, or acceptance condition",
            text,
        )

    def test_controller_has_no_substantive_plan_authority(self) -> None:
        controller = (
            ASSETS / "runtime_kit/cards/roles/controller.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("foreground action ledger is your only plan", controller)
        self.assertIn("do not create a project plan", controller)
        self.assertIn("not controller", controller)
        handoff_source = (ASSETS / "flowpilot_core_runtime/role_handoff.py").read_text(
            encoding="utf-8"
        ).lower()
        self.assertNotIn('"controller": "controller"', handoff_source)


if __name__ == "__main__":
    unittest.main()
