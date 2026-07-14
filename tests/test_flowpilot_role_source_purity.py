from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

host = importlib.import_module("flowpilot_core_runtime.host")
role_handoff = importlib.import_module("flowpilot_core_runtime.role_handoff")
runtime = importlib.import_module("flowpilot_core_runtime.runtime")


def _authorize_background_collaboration(ledger: dict[str, object]) -> None:
    ledger["startup_intake"] = {
        "status": "confirmed",
        "current_run_authority": True,
        "controller_may_read_body": False,
        "body_text_included": False,
        "startup_answers": {"background_collaboration_authorized": True},
    }


def _ledger_with_packet(responsibility: str, *, packet_kind: str = "task") -> tuple[dict, str]:
    ledger = runtime.new_ledger("Role-source goal", "Role-source contract")
    _authorize_background_collaboration(ledger)
    runtime.create_route(ledger, "Role-source route", ["Check role source"])
    packet_id = runtime.issue_task_packet(
        ledger,
        responsibility,
        "Check current role source",
        "SEALED_ROLE_SOURCE_BODY",
        packet_kind=packet_kind,
    )
    return ledger, packet_id


def _assigned_current_role(
    responsibility: str,
    *,
    host_kind: str = "live",
    packet_kind: str = "task",
) -> tuple[dict, str, str]:
    ledger, packet_id = _ledger_with_packet(responsibility, packet_kind=packet_kind)
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        host_kind=host_kind,
        agent_id=f"{responsibility}-source-test",
        packet_id=packet_id,
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    return ledger, packet_id, lease_id


class FlowPilotRoleSourcePurityTests(unittest.TestCase):
    def test_only_current_explicit_responsibilities_can_be_leased(self) -> None:
        expected = {
            "pm",
            "worker",
            "research_worker",
            "reviewer",
            "flowguard_operator",
            "ui_qa",
        }
        self.assertEqual(set(host.CURRENT_RESPONSIBILITIES), expected)

        for responsibility in sorted(expected):
            with self.subTest(responsibility=responsibility):
                packet_kind = "flowguard_check" if responsibility == "flowguard_operator" else "task"
                ledger, packet_id, lease_id = _assigned_current_role(
                    responsibility,
                    host_kind="fake",
                    packet_kind=packet_kind,
                )
                handoff = role_handoff.render_current_packet_handoff(
                    ledger,
                    root=ROOT,
                    script_path=ASSETS / "flowpilot_new.py",
                    run_id="run-role-source-test",
                    packet_id=packet_id,
                    lease_id=lease_id,
                )
                self.assertEqual(handoff["responsibility"], responsibility)
                self.assertEqual(handoff["host_kind"], "fake")

    def test_legacy_aliases_unknown_roles_and_ownerless_planner_are_rejected(self) -> None:
        for responsibility in ("project_manager", "human_like_reviewer", "unknown_role", "planner"):
            with self.subTest(responsibility=responsibility):
                ledger = runtime.new_ledger("Role-source goal", "Role-source contract")
                _authorize_background_collaboration(ledger)
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown current responsibility"):
                    host.lease_responsibility(ledger, responsibility, host_kind="fake")
                self.assertEqual(ledger["role_assignments"], {})
                self.assertEqual(ledger["leases"], {})

    def test_daemon_and_unknown_host_sources_are_rejected_before_assignment(self) -> None:
        for host_kind in ("daemon", "router_daemon", "background_role"):
            with self.subTest(host_kind=host_kind):
                ledger = runtime.new_ledger("Role-source goal", "Role-source contract")
                _authorize_background_collaboration(ledger)
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown current host kind"):
                    host.lease_responsibility(ledger, "worker", host_kind=host_kind)
                self.assertEqual(ledger["role_assignments"], {})
                self.assertEqual(ledger["leases"], {})

    def test_handoff_rejects_wrong_role_and_noncurrent_assignment_source(self) -> None:
        ledger, packet_id, lease_id = _assigned_current_role("worker")
        assignment_id = ledger["leases"][lease_id]["role_assignment_id"]

        ledger["leases"][lease_id]["responsibility"] = "reviewer"
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "handoff responsibility mismatch"):
            role_handoff.render_current_packet_handoff(
                ledger,
                root=ROOT,
                script_path=ASSETS / "flowpilot_new.py",
                run_id="run-role-source-test",
                packet_id=packet_id,
                lease_id=lease_id,
            )

        ledger["leases"][lease_id]["responsibility"] = "worker"
        ledger["role_assignments"][assignment_id]["host_kind"] = "daemon"
        ledger["leases"][lease_id]["host_kind"] = "daemon"
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown current host kind"):
            role_handoff.render_current_packet_handoff(
                ledger,
                root=ROOT,
                script_path=ASSETS / "flowpilot_new.py",
                run_id="run-role-source-test",
                packet_id=packet_id,
                lease_id=lease_id,
            )

    def test_flowguard_operator_remains_explicit_and_is_not_downgraded_to_worker(self) -> None:
        ledger, packet_id, lease_id = _assigned_current_role(
            "flowguard_operator",
            packet_kind="flowguard_check",
        )
        handoff = role_handoff.render_current_packet_handoff(
            ledger,
            root=ROOT,
            script_path=ASSETS / "flowpilot_new.py",
            run_id="run-role-source-test",
            packet_id=packet_id,
            lease_id=lease_id,
        )

        self.assertEqual(handoff["responsibility"], "flowguard_operator")
        self.assertIn("Act as the FlowGuard operator role only", handoff["text"])
        self.assertNotIn("Act as the Worker role only", handoff["text"])

    def test_route_node_responsibility_never_defaults_or_downgrades(self) -> None:
        self.assertEqual(
            runtime._normalize_node_responsibility("flowguard_operator"),
            "flowguard_operator",
        )
        for responsibility in ("", "planner", "project_manager", "unknown_role"):
            with self.subTest(responsibility=responsibility):
                with self.assertRaisesRegex(
                    runtime.BlackBoxRuntimeError,
                    "requires an explicit current responsibility",
                ):
                    runtime._normalize_node_responsibility(responsibility)


if __name__ == "__main__":
    unittest.main()
