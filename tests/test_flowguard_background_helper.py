from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


helper = importlib.import_module("scripts.run_flowguard_background")
source_fingerprint = importlib.import_module("scripts.test_tier.source_fingerprint")


class FlowGuardBackgroundHelperTests(unittest.TestCase):
    def test_source_fingerprint_covers_canonical_behavior_authority(self) -> None:
        root = Path(__file__).resolve().parents[1]
        covered = {
            path.relative_to(root).as_posix()
            for path in source_fingerprint.covered_source_files()
        }
        self.assertIn(
            ".flowguard/behavior_commitment_ledger/ledger.json",
            covered,
        )

    def test_source_fingerprint_covers_skillguard_authority_not_result_output(self) -> None:
        root = Path(__file__).resolve().parents[1]
        covered = {
            path.relative_to(root).as_posix()
            for path in source_fingerprint.covered_source_files()
        }
        for relative in (
            "simulations/flowpilot_skillguard_contract_model.py",
            "simulations/run_flowpilot_skillguard_contract_checks.py",
            "skills/flowpilot/.skillguard/contract-source.json",
            "skills/flowpilot/.skillguard/compiled-contract.json",
            "skills/flowpilot/.skillguard/check-manifest.json",
        ):
            self.assertIn(relative, covered)
        self.assertNotIn(
            "simulations/flowpilot_skillguard_current_contract_results.json",
            covered,
        )

    def test_command_writes_complete_current_stable_artifact_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowguard-background-helper-") as tmp:
            root = Path(tmp)
            exit_code = helper.main(
                [
                    "--name",
                    "fixture",
                    "--log-root",
                    str(root),
                    "--",
                    sys.executable,
                    "-c",
                    "import sys; print('out'); print('err', file=sys.stderr)",
                ]
            )
            paths = helper.artifact_paths(root, "fixture")
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
            all_present = all(path.is_file() for path in paths.values())
            exit_text = paths["exit"].read_text(encoding="utf-8").strip()
            out_text = paths["out"].read_text(encoding="utf-8")
            err_text = paths["err"].read_text(encoding="utf-8")
            verify_exit_code = helper.main(
                [
                    "--name",
                    "fixture",
                    "--log-root",
                    str(root),
                    "--verify",
                    "--",
                    sys.executable,
                    "-c",
                    "import sys; print('out'); print('err', file=sys.stderr)",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(verify_exit_code, 0)
        self.assertTrue(all_present)
        self.assertEqual(exit_text, "0")
        self.assertIn("out", out_text)
        self.assertIn("err", err_text)
        self.assertEqual(meta["status"], "passed")
        self.assertTrue(meta["source_fingerprint_current"])
        self.assertFalse(meta["proof_reused"])
        self.assertEqual(
            meta["covered_source_fingerprint_start"],
            meta["covered_source_fingerprint_end"],
        )

    def test_verify_rejects_stale_source_without_relaunching(self) -> None:
        command = (sys.executable, "-c", "print('current')")
        with tempfile.TemporaryDirectory(prefix="flowguard-background-helper-stale-") as tmp:
            root = Path(tmp)
            self.assertEqual(
                helper.main(
                    ["--name", "fixture", "--log-root", str(root), "--", *command]
                ),
                0,
            )
            paths = helper.artifact_paths(root, "fixture")
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
            meta["covered_source_fingerprint"] = "stale-source"
            paths["meta"].write_text(json.dumps(meta), encoding="utf-8")

            exit_code = helper.main(
                [
                    "--name",
                    "fixture",
                    "--log-root",
                    str(root),
                    "--verify",
                    "--",
                    *command,
                ]
            )

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
