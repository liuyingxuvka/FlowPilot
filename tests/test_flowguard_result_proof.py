from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


run_capability_checks = load_module(
    "flowpilot_test_run_capability_checks",
    ROOT / "simulations" / "run_capability_checks.py",
)
run_meta_checks = load_module(
    "flowpilot_test_run_meta_checks",
    ROOT / "simulations" / "run_meta_checks.py",
)
smoke_flowpilot = load_module(
    "flowpilot_test_smoke_flowpilot",
    ROOT / "scripts" / "smoke_flowpilot.py",
)


class FlowGuardResultProofTests(unittest.TestCase):
    def assert_proof_accepts_same_inputs_and_rejects_changed_result(self, runner) -> None:
        with tempfile.TemporaryDirectory(prefix="flowguard-proof-") as tmp_name:
            tmp = Path(tmp_name)
            old_results = runner.RESULTS_PATH
            old_proof = runner.PROOF_PATH
            try:
                runner.RESULTS_PATH = tmp / "results.json"
                runner.PROOF_PATH = tmp / "results.proof.json"
                runner.RESULTS_PATH.write_text('{"ok": true}\n', encoding="utf-8")

                input_fingerprint = runner._current_input_fingerprint()
                runner._write_proof(ok=True, input_fingerprint=input_fingerprint)

                self.assertEqual(runner._valid_proof(input_fingerprint), (True, "valid proof"))
                self.assertEqual(runner._valid_proof("changed"), (False, "input fingerprint changed"))

                runner.RESULTS_PATH.write_text('{"ok": false}\n', encoding="utf-8")
                self.assertEqual(
                    runner._valid_proof(input_fingerprint),
                    (False, "result fingerprint changed"),
                )
            finally:
                runner.RESULTS_PATH = old_results
                runner.PROOF_PATH = old_proof

    def test_meta_result_proof_rejects_stale_reuse(self) -> None:
        self.assert_proof_accepts_same_inputs_and_rejects_changed_result(run_meta_checks)

    def test_capability_result_proof_rejects_stale_reuse(self) -> None:
        self.assert_proof_accepts_same_inputs_and_rejects_changed_result(run_capability_checks)

    def test_smoke_fast_only_marks_slow_model_checks_fast(self) -> None:
        commands: list[list[str]] = []
        fast_flags: list[bool] = []
        old_run = smoke_flowpilot.run
        try:
            def fake_run(command: list[str], *, fast: bool = False) -> bool:
                commands.append(command)
                fast_flags.append(fast)
                return True

            smoke_flowpilot.run = fake_run
            self.assertEqual(smoke_flowpilot.main(["--fast"]), 0)
        finally:
            smoke_flowpilot.run = old_run

        self.assertTrue(fast_flags)
        self.assertTrue(all(fast_flags))
        self.assertIn([sys.executable, "simulations/run_meta_checks.py", "--fast"], commands)
        self.assertIn([sys.executable, "simulations/run_capability_checks.py", "--fast"], commands)
        self.assertIn(
            [
                sys.executable,
                "simulations/run_flowpilot_control_plane_friction_checks.py",
                "--skip-live-audit",
                "--json-out",
                "simulations/flowpilot_control_plane_friction_results.json",
            ],
            commands,
        )
        for command in commands[:4]:
            self.assertNotIn("--fast", command)

    def test_smoke_group_runs_only_selected_chunk(self) -> None:
        commands: list[list[str]] = []
        old_run = smoke_flowpilot.run
        try:
            def fake_run(command: list[str], *, fast: bool = False) -> bool:
                commands.append(command)
                return True

            smoke_flowpilot.run = fake_run
            self.assertEqual(smoke_flowpilot.main(["--fast", "--group", "parents"]), 0)
        finally:
            smoke_flowpilot.run = old_run

        self.assertEqual(
            commands,
            [
                [
                    sys.executable,
                    "simulations/run_flowpilot_model_mesh_checks.py",
                    "--json-out",
                    "simulations/flowpilot_model_mesh_results.json",
                ],
                [sys.executable, "simulations/run_meta_checks.py", "--fast"],
                [sys.executable, "simulations/run_capability_checks.py", "--fast"],
                [
                    sys.executable,
                    "simulations/run_flowpilot_model_hierarchy_checks.py",
                    "--json-out",
                    "simulations/flowpilot_model_hierarchy_results.json",
                ],
            ],
        )

    def test_smoke_structure_alignment_is_declaration_only_and_cannot_overwrite_strict_evidence(self) -> None:
        commands = smoke_flowpilot.build_check_groups(fast=True)["structure"]
        alignment_command = next(
            command
            for command in commands
            if "simulations/run_flowpilot_model_test_alignment_checks.py" in command
        )

        self.assertIn("--declaration-only", alignment_command)
        self.assertNotIn(
            "simulations/flowpilot_model_test_alignment_results.json",
            alignment_command,
        )
        self.assertIn(
            "tmp/test_results/flowpilot_model_test_alignment_declaration_only.json",
            alignment_command,
        )


if __name__ == "__main__":
    unittest.main()
