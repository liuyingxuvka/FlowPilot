from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import barrier_bundle  # noqa: E402
import flowpilot_controller_break_glass as break_glass  # noqa: E402
import flowpilot_paths  # noqa: E402
import flowpilot_prompt_store as prompt_store  # noqa: E402
import flowpilot_router_action_providers as action_providers  # noqa: E402
import flowpilot_router_card_returns as card_returns  # noqa: E402
import flowpilot_router_errors as router_errors  # noqa: E402
import packet_runtime_audit  # noqa: E402
import packet_runtime_contracts  # noqa: E402
import packet_runtime_paths  # noqa: E402
import packet_runtime_schema  # noqa: E402
import run_packet_control_plane_checks  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotRuntimeOwnerContractTests(unittest.TestCase):
    def test_barrier_bundle_contract_validates_required_obligations_and_roles(self) -> None:
        pending = barrier_bundle.make_pending_bundle(
            bundle_id="bundle-startup",
            barrier_id="startup",
            member_packet_ids=("packet-1",),
            node_id="node-start",
            route_version=2,
        )
        blocked = barrier_bundle.validate_barrier_bundle(pending)

        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["bundle_id"], "bundle-startup")
        self.assertIn("missing_required_obligations", blocked["failures"])
        self.assertIn("missing_required_role_slices", blocked["failures"])

        complete = dict(pending)
        complete["obligations"] = {
            obligation: "passed"
            for obligation in barrier_bundle.required_obligation_ids("startup")
        }
        complete["role_slices"] = {
            role: {"status": "approved"}
            for role in barrier_bundle._BARRIER_BY_ID["startup"].required_role_slices
        }
        passed = barrier_bundle.validate_barrier_bundle(complete)
        summary = barrier_bundle.barrier_bundle_summary(complete)

        self.assertTrue(passed["ok"])
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(
            set(barrier_bundle.passed_obligation_ids(complete)),
            set(barrier_bundle.required_obligation_ids("startup")),
        )

        final_bundle = barrier_bundle.make_pending_bundle(
            bundle_id="bundle-final",
            barrier_id="final_closure",
            member_packet_ids=("packet-final",),
            node_id="node-final",
            route_version=2,
        )
        final_bundle["obligations"] = {
            obligation: "passed"
            for obligation in barrier_bundle.required_obligation_ids("final_closure")
        }
        final_bundle["role_slices"] = {
            role: {"status": "approved"}
            for role in barrier_bundle._BARRIER_BY_ID["final_closure"].required_role_slices
        }
        final_bundle["final_ledger_clean"] = True
        final_bundle["terminal_backward_replay_passed"] = True
        cumulative = {
            obligation: "passed"
            for obligation in barrier_bundle.all_legacy_obligation_ids()
        }
        missing_cumulative = dict(cumulative)
        missing_cumulative.pop("packet_ledger_mail_delivery")

        blocked_final = barrier_bundle.validate_barrier_bundle(
            final_bundle,
            cumulative_obligations=missing_cumulative,
        )
        passed_final = barrier_bundle.validate_barrier_bundle(
            final_bundle,
            cumulative_obligations=cumulative,
        )

        self.assertIn(
            "final_closure_missing_cumulative_legacy_obligations",
            blocked_final["failures"],
        )
        self.assertEqual(
            blocked_final["missing_cumulative_obligations"],
            ["packet_ledger_mail_delivery"],
        )
        self.assertTrue(passed_final["ok"])

    def test_break_glass_contract_records_controller_only_incident_patch_and_close(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-break-glass-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            source = project_root / "runtime" / "controller_action_ledger.json"
            source.parent.mkdir(parents=True)
            source.write_text("{}", encoding="utf-8")

            incident_result = break_glass.open_incident(
                project_root,
                run_root,
                incident_id="Incident 1",
                trigger_summary="Controller loop cannot produce legal next action.",
                failure_kind="controller_loop_dead_end",
                sources=["runtime/controller_action_ledger.json"],
                normal_lanes=["router_reconciliation"],
            )
            patch_result = break_glass.record_patch(
                project_root,
                run_root,
                incident_id="Incident 1",
                patch_id="Patch 1",
                reason="Record diagnostic-only break-glass recovery evidence.",
                touched_paths=["runtime/controller_action_ledger.json"],
                validation=["python scripts/check_install.py"],
            )
            close_result = break_glass.close_incident(
                project_root,
                run_root,
                incident_id="Incident 1",
                disposition="normal lane restored",
            )

            self.assertTrue(incident_result["ok"])
            self.assertTrue(patch_result["ok"])
            self.assertTrue(close_result["ok"])
            self.assertEqual(incident_result["incident"]["opened_by_role"], "controller")
            self.assertFalse(
                incident_result["incident"]["sources_inspected"][0]["sealed_body_content_read"]
            )
            self.assertTrue(
                incident_result["incident"]["forbidden_actions_acknowledged"]["route_mutation"]
            )
            self.assertEqual(close_result["incident"]["status"], "closed")

    def test_path_and_prompt_store_contracts_resolve_active_run_and_hash_checked_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-paths-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            write_json(
                project_root / ".flowpilot" / "current.json",
                {
                    "current_run_id": "run-test",
                    "current_run_root": ".flowpilot/runs/run-test",
                },
            )

            resolved = flowpilot_paths.resolve_flowpilot_paths(project_root)
            relative = flowpilot_paths.resolve_project_relative_path(
                project_root,
                ".flowpilot/runs/run-test/state.json",
                default_key="state_path",
            )

            self.assertEqual(resolved["layout"], "run_scoped")
            self.assertEqual(resolved["path_status"], "ok")
            self.assertEqual(resolved["run_root"], run_root.resolve())
            self.assertEqual(relative, project_root.resolve() / ".flowpilot" / "runs" / "run-test" / "state.json")

        manifest = prompt_store.load_prompt_manifest()
        text = prompt_store.load_prompt_text("cards.post_ack_policy")
        rendered = prompt_store.render_prompt_text("cards.post_ack_policy", {})
        store = prompt_store.PromptStore()
        entry = prompt_store.prompt_entry("cards.post_ack_policy")

        self.assertEqual(manifest["schema_version"], prompt_store.PROMPT_MANIFEST_SCHEMA)
        self.assertEqual(rendered, text)
        self.assertEqual(store.text("cards.post_ack_policy"), text)
        self.assertEqual(store.content_hash("cards.post_ack_policy"), entry["sha256"])

    def test_packet_runtime_contracts_paths_schema_and_audit_boundaries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-packet-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            packet_dir = run_root / "packets" / "packet-1"
            packet_dir.mkdir(parents=True)
            body = packet_dir / "packet_body.md"
            body.write_text("packet body", encoding="utf-8")
            write_json(
                project_root / ".flowpilot" / "current.json",
                {
                    "current_run_id": "run-test",
                    "current_run_root": ".flowpilot/runs/run-test",
                },
            )
            write_json(
                packet_dir / "packet_envelope.json",
                {
                    "schema_version": packet_runtime_schema.PACKET_ENVELOPE_SCHEMA,
                    "packet_id": "packet-1",
                    "packet_body_path": ".flowpilot/runs/run-test/packets/packet-1/packet_body.md",
                    "packet_body_hash": packet_runtime_schema.sha256_file(body),
                    "to_role": "worker_a",
                },
            )

            contract = packet_runtime_contracts.normalize_output_contract(
                {"contract_id": "custom.contract.v1"},
                packet_type="work_packet",
                from_role="project_manager",
                to_role="worker_a",
                node_id="node-1",
            )
            reminder = packet_runtime_contracts.mutual_role_reminder(
                source_role="project_manager",
                target_role="worker_a",
                envelope_kind="packet",
            )
            envelope = packet_runtime_paths.load_envelope(
                project_root,
                ".flowpilot/runs/run-test/packets/packet-1/packet_envelope.json",
            )
            audit = packet_runtime_audit.audit_barrier_bundles(project_root, run_id="run-missing")

            complete_bundle = barrier_bundle.make_pending_bundle(
                bundle_id="bundle-startup",
                barrier_id="startup",
                member_packet_ids=("packet-1",),
                node_id="node-1",
                route_version=1,
            )
            complete_bundle["obligations"] = {
                obligation: "passed"
                for obligation in barrier_bundle.required_obligation_ids("startup")
            }
            complete_bundle["role_slices"] = {
                role: {"status": "approved"}
                for role in barrier_bundle._BARRIER_BY_ID["startup"].required_role_slices
            }
            write_json(
                run_root / "packet_ledger.json",
                {
                    "schema_version": packet_runtime_schema.PACKET_LEDGER_SCHEMA,
                    "packets": [
                        {
                            "packet_id": "packet-1",
                            "node_id": "node-1",
                            "barrier_bundle": complete_bundle,
                        }
                    ],
                    "barrier_bundles": [],
                },
            )
            written_audit = packet_runtime_audit.audit_barrier_bundles(
                project_root,
                run_id="run-test",
                node_id="node-1",
                bundle_id="bundle-startup",
            )
            updated_ledger = json.loads((run_root / "packet_ledger.json").read_text(encoding="utf-8"))

            self.assertEqual(contract["recipient_role"], "worker_a")
            self.assertEqual(packet_runtime_contracts.output_contract_id(contract), "custom.contract.v1")
            self.assertIn("Controller only", reminder["controller_reminder"])
            self.assertEqual(envelope["body_path"], ".flowpilot/runs/run-test/packets/packet-1/packet_body.md")
            self.assertTrue(
                packet_runtime_paths.verify_body_hash(
                    project_root,
                    ".flowpilot/runs/run-test/packets/packet-1/packet_body.md",
                    packet_runtime_schema.sha256_file(body),
                )
            )
            self.assertTrue(audit["passed"])
            self.assertTrue(audit["ledger_missing"])
            self.assertTrue(written_audit["passed"])
            self.assertEqual(written_audit["checked_bundle_count"], 1)
            self.assertTrue((run_root / "barrier_bundle_audit.json").exists())
            self.assertEqual(
                updated_ledger["latest_barrier_bundle_audit_path"],
                ".flowpilot/runs/run-test/barrier_bundle_audit.json",
            )

    def test_small_runtime_owner_helpers_return_stable_external_shapes(self) -> None:
        class FakeRouter:
            @staticmethod
            def _run_lifecycle_terminal_action(project_root: Path, run_state: dict, run_root: Path) -> None:
                return None

        class FakeLifecycleRouter:
            @staticmethod
            def _run_lifecycle_terminal_action(
                project_root: Path,
                run_state: dict,
                run_root: Path,
            ) -> dict:
                return {"action_type": "finalize_run", "source": "lifecycle"}

            @staticmethod
            def append_history(run_state: dict, event: str, payload: dict) -> None:
                run_state.setdefault("history", []).append(
                    {"event": event, "payload": payload}
                )

            @staticmethod
            def save_run_state(run_root: Path, run_state: dict) -> None:
                run_state["saved_to"] = str(run_root)

        run_state: dict[str, object] = {}
        run_root = Path(".flowpilot/runs/run-test")
        outcome = action_providers.ProviderOutcome({"action_type": "wait"}, finalized=True)
        lifecycle_action = action_providers.lifecycle_provider(
            FakeRouter(),
            Path("."),
            {},
            Path("."),
        )
        terminal_action = action_providers.lifecycle_provider(
            FakeLifecycleRouter(),
            Path("."),
            run_state,
            run_root,
        )
        card_ids = card_returns._pending_return_card_ids(
            object(),
            {
                "return_kind": "system_card_bundle",
                "card_id": "pm.core",
                "card_ids": ["reviewer.fact", "pm.core"],
            }
        )
        error = router_errors.RouterError(
            "blocked",
            control_blocker={"code": "missing_packet"},
        )
        write_lock_error = router_errors.RouterLedgerWriteInProgress(
            Path("state.json"),
            {"status": "writing"},
            "busy",
        )
        write_lock_record = router_errors.router_error_record(write_lock_error)

        self.assertEqual(outcome.action["action_type"], "wait")
        self.assertTrue(outcome.finalized)
        self.assertIsNone(lifecycle_action)
        self.assertEqual(terminal_action, {"action_type": "finalize_run", "source": "lifecycle"})
        self.assertEqual(run_state["pending_action"], terminal_action)
        self.assertEqual(
            run_state["history"],
            [
                {
                    "event": "router_computed_terminal_lifecycle_action",
                    "payload": {"action_type": "finalize_run"},
                }
            ],
        )
        self.assertEqual(run_state["saved_to"], str(run_root))
        self.assertEqual(card_ids, {"pm.core", "reviewer.fact"})
        self.assertEqual(error.control_blocker, {"code": "missing_packet"})
        error_record = router_errors.router_error_record(error)
        self.assertEqual(error_record["error_type"], "RouterError")
        self.assertEqual(error_record["message"], "blocked")
        self.assertEqual(error_record["control_blocker"], {"code": "missing_packet"})
        self.assertEqual(write_lock_record["error_type"], "RouterLedgerWriteInProgress")
        self.assertEqual(write_lock_record["path"], "state.json")
        self.assertEqual(write_lock_record["write_lock_status"], "writing")
        with self.assertRaises(router_errors.RouterLedgerCorruptionError):
            raise router_errors.RouterLedgerCorruptionError(Path("state.json"), "bad json")

    def test_packet_control_plane_runner_main_uses_flowguard_report_exit_contract(self) -> None:
        case = self

        class FakeReport:
            ok = True

            def format_text(self) -> str:
                return "fake packet control plane report"

        class FakeExplorer:
            def __init__(self, **kwargs: object) -> None:
                self.required_labels = tuple(kwargs["required_labels"])  # type: ignore[index]

            def explore(self) -> FakeReport:
                self_outer = self
                case.assertIn("packet_physical_files_written", self_outer.required_labels)
                case.assertIn("pm_advanced", self_outer.required_labels)
                return FakeReport()

        original_explorer = run_packet_control_plane_checks.Explorer
        run_packet_control_plane_checks.Explorer = FakeExplorer  # type: ignore[assignment]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                exit_code = run_packet_control_plane_checks.main()
        finally:
            run_packet_control_plane_checks.Explorer = original_explorer

        self.assertEqual(exit_code, 0)
        self.assertIn("fake packet control plane report", output.getvalue())


if __name__ == "__main__":
    unittest.main()
