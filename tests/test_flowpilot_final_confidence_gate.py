from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "simulations" / "flowpilot_final_confidence_gate.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("flowpilot_final_confidence_gate", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(MODULE_PATH.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


gate = load_gate_module()


PASSING_PAYLOADS = {
    "control_plane": {
        "ok": True,
        "live_run_audit": {
            "ok": True,
            "skipped": False,
            "run_id": "run-current",
            "findings": [],
        },
    },
    "event_idempotency": {
        "ok": True,
        "flowguard_explorer": {"ok": True},
        "safe_graph": {"ok": True},
        "progress": {"ok": True},
        "hazard_detection": {"ok": True},
    },
    "model_test_alignment": {
        "ok": True,
        "alignment_ok": True,
        "full_diagnostic_ok": True,
        "evidence_status": "passed",
        "claim_scope": "done",
        "execution_evidence": {"ok": True},
        "full_coverage_ok": True,
        "release_convergence_ok": True,
        "full_model_test_code_diagnostic": {
            "deferred_structure_split_count": 0,
            "gap_counts": {},
            "gap_surface_count": 0,
            "unresolved_non_deferred_gap_count": 0,
        },
    },
    "known_friction": {
        "ok": True,
        "defect_family_gate_ok": True,
        "defect_family_gate_report": {
            "gate_report": {
                "confidence": "full",
                "decision": "defect_family_gate_full_confidence",
            },
            "risk_ledger_report": {
                "confidence": "full",
                "decision": "risk_evidence_full_confidence",
            },
        },
    },
    "terminal_return": {
        "ok": True,
        "final_return_preflight": {
            "allowed": True,
            "blockers": [],
            "closure_decision": "terminal_return",
            "controller_stop_allowed": True,
            "guard_decision": "terminal_return",
            "next_action_type": "",
        },
        "foreground_duty": {
            "action": "terminal_return",
            "controller_stop_allowed": True,
            "run_id": "run-current",
        },
        "next_action": {},
    },
}


class FlowPilotFinalConfidenceGateTests(unittest.TestCase):
    def test_evidence_rows_project_repository_paths_without_machine_prefixes(self) -> None:
        row = gate._row(
            "terminal_return",
            ROOT / "simulations" / "flowpilot_terminal_return_preflight_results.json",
        )

        self.assertEqual(
            row["path"],
            "simulations/flowpilot_terminal_return_preflight_results.json",
        )

    def evaluate(self, payloads: dict[str, dict]) -> dict:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                result_paths[name] = path
            return gate.evaluate_final_confidence(result_paths)

    def test_all_required_evidence_allows_full_confidence(self) -> None:
        report = self.evaluate(copy.deepcopy(PASSING_PAYLOADS))

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["decision"], gate.DECISION_FULL)
        self.assertEqual(report["claim_scope"], "formal_exit")
        self.assertTrue(report["formal_exit_authority"])
        self.assertEqual(report["blockers"], [])

    def test_startup_intake_preflight_blocks_formal_exit_confidence(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["terminal_return"] = {
            "ok": False,
            "final_return_preflight": {
                "allowed": False,
                "blockers": [
                    "closure:not_attempted",
                    "guard_decision:process_next_action",
                    "lifecycle_guard_disallows_stop",
                    "next_action:open_startup_intake",
                ],
                "closure_decision": "not_attempted",
                "controller_stop_allowed": False,
                "guard_decision": "process_next_action",
                "next_action_type": "open_startup_intake",
            },
            "foreground_duty": {
                "action": "process_next_action",
                "controller_stop_allowed": False,
                "run_id": "run-startup",
            },
            "next_action": {
                "action_type": "open_startup_intake",
            },
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        self.assertFalse(report["formal_exit_authority"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "terminal_return")
        self.assertIn("next_action:open_startup_intake", blocker["codes"])
        self.assertIn("foreground_duty_not_terminal_return", blocker["codes"])
        self.assertIn("controller_stop_not_allowed", blocker["codes"])
        self.assertEqual(blocker["details"]["next_action_type"], "open_startup_intake")

    def test_repository_only_mode_scopes_out_terminal_return_authority(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads.pop("terminal_return")
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-repo-only-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                result_paths[name] = path

            report = gate.evaluate_final_confidence(
                result_paths,
                terminal_return_required=False,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["decision"], gate.DECISION_REPOSITORY_ONLY)
        self.assertEqual(report["claim_scope"], "repository_only")
        self.assertFalse(report["formal_exit_authority"])
        row = next(item for item in report["evidence_rows"] if item["name"] == "terminal_return")
        self.assertTrue(row["details"]["scoped_out"])

    def test_skipped_live_audit_blocks_final_confidence(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["control_plane"]["ok"] = True
        payloads["control_plane"]["live_run_audit"] = {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "findings": [],
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], gate.DECISION_BLOCKED)
        self.assertIn("live_run_audit_skipped", report["blockers"][0]["codes"])

    def test_failed_live_audit_preserves_finding_codes(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["control_plane"]["ok"] = False
        payloads["control_plane"]["live_run_audit"] = {
            "ok": False,
            "skipped": False,
            "run_id": "run-current",
            "findings": [
                {"code": "break_glass_patch_validation_pending", "severity": "error"},
            ],
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "control_plane")
        self.assertIn("live_run_audit_failed", blocker["codes"])
        self.assertIn("control_plane_check_failed", blocker["codes"])
        self.assertIn("break_glass_patch_validation_pending", blocker["details"]["live_finding_codes"])

    def test_deferred_structure_split_only_allows_release_convergence(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["model_test_alignment"]["full_coverage_ok"] = False
        payloads["model_test_alignment"]["release_convergence_ok"] = True
        payloads["model_test_alignment"]["full_model_test_code_diagnostic"] = {
            "deferred_structure_split_count": 3,
            "gap_counts": {"needs_structure_split": 3},
            "gap_surface_count": 3,
            "unresolved_non_deferred_gap_count": 0,
        }

        report = self.evaluate(payloads)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["decision"], gate.DECISION_RELEASE_CONVERGED)
        self.assertEqual(report["blockers"], [])
        row = next(item for item in report["evidence_rows"] if item["name"] == "model_test_alignment")
        self.assertEqual(row["details"]["coverage_claim"], "release_convergence_deferred_structure_only")

    def test_alignment_green_with_non_deferred_gap_blocks(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["model_test_alignment"]["full_coverage_ok"] = False
        payloads["model_test_alignment"]["release_convergence_ok"] = False
        payloads["model_test_alignment"]["full_model_test_code_diagnostic"] = {
            "deferred_structure_split_count": 0,
            "gap_counts": {"missing_test": 1},
            "gap_surface_count": 1,
            "unresolved_non_deferred_gap_count": 1,
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "model_test_alignment")
        self.assertIn("full_coverage_ok_false", blocker["codes"])
        self.assertIn("release_convergence_ok_false", blocker["codes"])
        self.assertEqual(blocker["details"]["gap_counts"], {"missing_test": 1})

    def test_routine_only_alignment_cannot_close_repository_final_confidence(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["model_test_alignment"]["claim_scope"] = "routine"

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(
            item for item in report["blockers"] if item["evidence"] == "model_test_alignment"
        )
        self.assertIn("model_test_alignment_scope_not_done", blocker["codes"])

    def test_known_friction_scoped_risk_ledger_blocks(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["known_friction"]["defect_family_gate_report"]["risk_ledger_report"] = {
            "confidence": "scoped",
            "decision": "risk_evidence_scoped_confidence",
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "known_friction")
        self.assertIn("risk_ledger_confidence_not_full", blocker["codes"])
        self.assertEqual(blocker["details"]["risk_ledger_confidence"], "scoped")

    def test_missing_required_payload_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-missing-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {
                name: root / f"{name}.json"
                for name in PASSING_PAYLOADS
            }
            for name, payload in PASSING_PAYLOADS.items():
                if name == "event_idempotency":
                    continue
                result_paths[name].write_text(json.dumps(payload), encoding="utf-8")

            report = gate.evaluate_final_confidence(result_paths)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "event_idempotency")
        self.assertIn("missing_evidence", blocker["codes"])

    def test_missing_terminal_return_payload_blocks_formal_exit_confidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-missing-terminal-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {
                name: root / f"{name}.json"
                for name in PASSING_PAYLOADS
            }
            for name, payload in PASSING_PAYLOADS.items():
                if name == "terminal_return":
                    continue
                result_paths[name].write_text(json.dumps(payload), encoding="utf-8")

            report = gate.evaluate_final_confidence(result_paths)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "terminal_return")
        self.assertIn("missing_evidence", blocker["codes"])

    def test_failed_subcheck_blocks_even_when_result_json_is_stale_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-stale-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {}
            for name, payload in PASSING_PAYLOADS.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                result_paths[name] = path

            report = gate.evaluate_final_confidence(
                result_paths,
                subcheck_runs=[
                    {
                        "name": "known_friction",
                        "exit_code": 1,
                        "stdout_path": str(root / "known_friction.out.txt"),
                        "stderr_path": str(root / "known_friction.err.txt"),
                    }
                ],
            )

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "known_friction")
        self.assertIn("subcheck_failed", blocker["codes"])
        self.assertEqual(blocker["details"]["subcheck_exit_code"], 1)

    def test_run_required_subchecks_refreshes_json_and_passes_control_plane_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-runs-") as tmp_name:
            root = Path(tmp_name)
            commands: list[list[str]] = []

            def fake_run(command, cwd, stdout, stderr, check):  # type: ignore[no-untyped-def]
                commands.append(list(command))
                script = Path(command[1]).name
                if script == "flowpilot_new.py":
                    stdout.write(json.dumps(PASSING_PAYLOADS["terminal_return"]))
                    return SimpleNamespace(returncode=0)
                json_path = Path(command[command.index("--json-out") + 1])
                self.assertFalse(json_path.exists(), f"stale JSON was not cleared: {json_path}")
                payload_name = {
                    "run_flowpilot_control_plane_friction_checks.py": "control_plane",
                    "run_flowpilot_event_idempotency_checks.py": "event_idempotency",
                    "run_flowpilot_model_test_alignment_checks.py": "model_test_alignment",
                    "flowpilot_known_friction_regression_matrix.py": "known_friction",
                }[script]
                json_path.write_text(json.dumps(PASSING_PAYLOADS[payload_name]), encoding="utf-8")
                return SimpleNamespace(returncode=0)

            stale_path = root / "flowpilot_known_friction_regression_matrix_results.json"
            stale_path.write_text('{"stale": true}', encoding="utf-8")
            evidence_manifest = root / "acceptance-testmesh-manifest.json"
            evidence_manifest.write_text('{"source_fingerprint":"current"}\n', encoding="utf-8")
            with mock.patch.object(gate.subprocess, "run", side_effect=fake_run):
                runs = gate.run_required_subchecks(
                    root,
                    live_root=Path("project-root"),
                    source_root=Path("source-root"),
                    evidence_manifest=evidence_manifest,
                )

        self.assertTrue(all(run["exit_code"] == 0 for run in runs))
        self.assertEqual({run["name"] for run in runs}, set(PASSING_PAYLOADS))
        self.assertTrue(all(run["command"][0] == "<python>" for run in runs))
        control_command = next(
            command for command in commands if command[1].endswith("run_flowpilot_control_plane_friction_checks.py")
        )
        control_run = next(run for run in runs if run["name"] == "control_plane")
        mta_run = next(run for run in runs if run["name"] == "model_test_alignment")
        mta_command = next(
            command for command in commands if command[1].endswith("run_flowpilot_model_test_alignment_checks.py")
        )
        self.assertIn("--live-root", control_command)
        self.assertIn("project-root", control_command)
        self.assertIn("--source-root", control_command)
        self.assertIn("source-root", control_command)
        self.assertIn("<external-live-root>", control_run["command"])
        self.assertIn("<flowpilot-source-root>", control_run["command"])
        self.assertNotIn("project-root", control_run["command"])
        self.assertNotIn("source-root", control_run["command"])
        self.assertIn("--evidence-manifest", mta_command)
        self.assertIn(str(evidence_manifest), mta_command)
        self.assertIn("--evidence-scope", mta_command)
        self.assertIn("done", mta_command)
        self.assertIn("<external>/acceptance-testmesh-manifest.json", mta_run["command"])
        self.assertNotIn(str(evidence_manifest), mta_run["command"])
        for command in commands:
            if command is not control_command:
                if command[1].endswith("flowpilot_new.py"):
                    self.assertIn("--root", command)
                    self.assertIn("project-root", command)
                else:
                    self.assertNotIn("--live-root", command)
                self.assertNotIn("--source-root", command)

    def test_terminal_return_preflight_nonzero_exit_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-terminal-run-") as tmp_name:
            root = Path(tmp_name)

            def fake_run(command, cwd, stdout, stderr, check):  # type: ignore[no-untyped-def]
                del cwd, stderr, check
                self.assertTrue(command[1].endswith("flowpilot_new.py"))
                stdout.write(
                    json.dumps(
                        {
                            "ok": False,
                            "final_return_preflight": {
                                "allowed": False,
                                "blockers": ["next_action:open_startup_intake"],
                                "controller_stop_allowed": False,
                                "next_action_type": "open_startup_intake",
                            },
                            "foreground_duty": {
                                "action": "process_next_action",
                                "controller_stop_allowed": False,
                                "run_id": "run-startup",
                            },
                        }
                    )
                )
                return SimpleNamespace(returncode=1)

            with mock.patch.object(gate.subprocess, "run", side_effect=fake_run):
                run = gate.run_terminal_return_preflight(root, live_root=Path("project-root"))

            result_paths = {}
            for name in ("control_plane", "event_idempotency", "model_test_alignment", "known_friction"):
                path = root / f"{name}.json"
                path.write_text(json.dumps(PASSING_PAYLOADS[name]), encoding="utf-8")
                result_paths[name] = path
            result_paths["terminal_return"] = root / gate.TERMINAL_RETURN_RESULT_FILENAME
            self.assertEqual(run["exit_code"], 1)
            payload = json.loads((root / gate.TERMINAL_RETURN_RESULT_FILENAME).read_text(encoding="utf-8"))
            report = gate.evaluate_final_confidence(
                result_paths,
                subcheck_runs=[run],
            )

            self.assertEqual(payload["terminal_return_preflight_exit_code"], 1)
            self.assertFalse(report["ok"])
            blocker = next(item for item in report["blockers"] if item["evidence"] == "terminal_return")
            self.assertIn("terminal_return_preflight_command_nonzero", blocker["codes"])


if __name__ == "__main__":
    unittest.main()
