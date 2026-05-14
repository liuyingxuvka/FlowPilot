from __future__ import annotations

import contextlib
import importlib.util
import io
import os
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


run_meta_checks = load_module(
    "flowpilot_progress_test_run_meta_checks",
    ROOT / "simulations" / "run_meta_checks.py",
)
run_capability_checks = load_module(
    "flowpilot_progress_test_run_capability_checks",
    ROOT / "simulations" / "run_capability_checks.py",
)


class LegacyRunnerProgressTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("FLOWGUARD_PROGRESS", None)

    def test_progress_helper_writes_stderr_only(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            progress = run_meta_checks._GraphBuildProgress("meta", 5)
            for state_count in range(1, 6):
                progress.observe(state_count, state_count * 2)
            progress.complete(5, 10)

        self.assertEqual("", stdout.getvalue())
        text = stderr.getvalue()
        self.assertIn("[flowpilot-flowguard] start check=meta", text)
        self.assertIn("[flowpilot-flowguard] progress check=meta 100%", text)
        self.assertIn("[flowpilot-flowguard] complete check=meta states=5 edges=10", text)

    def test_progress_helper_honors_environment_opt_out(self) -> None:
        os.environ["FLOWGUARD_PROGRESS"] = "0"
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            progress = run_capability_checks._GraphBuildProgress("capability", 5)
            progress.observe(5, 10)
            progress.complete(5, 10)

        self.assertEqual("", stderr.getvalue())

    def test_fast_proof_reuse_is_visible_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-proof-reuse-") as tmp_name:
            tmp = Path(tmp_name)
            old_results = run_meta_checks.RESULTS_PATH
            old_proof = run_meta_checks.PROOF_PATH
            try:
                run_meta_checks.RESULTS_PATH = tmp / "results.json"
                run_meta_checks.PROOF_PATH = tmp / "results.proof.json"
                run_meta_checks.RESULTS_PATH.write_text('{"ok": true}\n', encoding="utf-8")
                fingerprint = run_meta_checks._current_input_fingerprint()
                run_meta_checks._write_proof(ok=True, input_fingerprint=fingerprint)

                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    self.assertEqual(run_meta_checks.main(["--fast"]), 0)

                self.assertIn("FlowGuard meta proof reused", stdout.getvalue())
                self.assertIn("[flowpilot-flowguard] proof_reused check=meta", stderr.getvalue())
            finally:
                run_meta_checks.RESULTS_PATH = old_results
                run_meta_checks.PROOF_PATH = old_proof


if __name__ == "__main__":
    unittest.main()
