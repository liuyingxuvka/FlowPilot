from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_ROOT = ROOT / "simulations"


def runner_paths() -> list[Path]:
    return sorted(RUNNER_ROOT.glob("run_*checks.py"))


def top_level_function_names(tree: ast.Module) -> set[str]:
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def has_main_guard(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        for child in ast.walk(node.test):
            if isinstance(child, ast.Constant) and child.value == "__main__":
                return True
    return False


def has_structured_result_anchor(tree: ast.Module, text: str) -> bool:
    functions = top_level_function_names(tree)
    if {"run_checks", "build_report"} & functions:
        return True
    return any(anchor in text for anchor in ("RESULTS_PATH", "json.dumps", "FlowGuard"))


class FlowPilotModelCheckRunnerContractTests(unittest.TestCase):
    def test_all_model_check_runners_have_public_entrypoint_contracts(self) -> None:
        # Diagnostic marker: MODEL_CHECK_RUNNER_CONTRACT_STEMS
        paths = runner_paths()
        self.assertGreater(len(paths), 20)

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
                functions = top_level_function_names(tree)

                self.assertIn("main", functions)
                self.assertTrue(has_main_guard(tree))
                self.assertTrue(
                    has_structured_result_anchor(tree, text),
                    f"{path.name} lacks run_checks/build_report/results/json contract anchor",
                )

    def test_json_out_runners_keep_explicit_json_output_option(self) -> None:
        for path in runner_paths():
            text = path.read_text(encoding="utf-8")
            if "--json-out" not in text:
                continue
            with self.subTest(path=path.name):
                tree = ast.parse(text)
                self.assertIn("main", top_level_function_names(tree))
                self.assertIn("argparse", text)
                self.assertTrue("write_text" in text or "json.dumps" in text)


if __name__ == "__main__":
    unittest.main()
