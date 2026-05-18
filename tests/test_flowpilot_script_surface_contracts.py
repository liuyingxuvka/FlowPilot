from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / "scripts"
WRAPPER_SCRIPTS = {
    "check_install.py",
    "flowpilot_outputs.py",
    "flowpilot_packets.py",
    "flowpilot_paths.py",
    "flowpilot_user_flow_diagram.py",
}


def top_level_function_names(tree: ast.Module) -> set[str]:
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            names.add(alias.asname or alias.name)
    return names


def has_main_guard(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        for child in ast.walk(node.test):
            if isinstance(child, ast.Constant) and child.value == "__main__":
                return True
    return False


class FlowPilotScriptSurfaceContractTests(unittest.TestCase):
    def test_scripts_expose_cli_or_wrapper_contract(self) -> None:
        # Diagnostic marker: SCRIPT_SURFACE_CONTRACT_TEST_PATH
        paths = sorted(SCRIPT_ROOT.glob("*.py"))
        self.assertGreater(len(paths), 10)

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
                functions = top_level_function_names(tree)
                imports = imported_names(tree)

                self.assertIn("from __future__ import annotations", text)
                if path.name in WRAPPER_SCRIPTS:
                    self.assertTrue(
                        "main" in imports or "_load_asset_module" in functions,
                        f"{path.name} wrapper must import main or load an asset module",
                    )
                else:
                    self.assertTrue(
                        {"main", "build_report", "check"} & functions,
                        f"{path.name} should expose main/build_report/check",
                    )
                if path.name != "flowpilot_paths.py":
                    self.assertTrue(has_main_guard(tree), f"{path.name} should have a __main__ guard")

    def test_public_json_scripts_keep_json_contract_literals(self) -> None:
        json_scripts = {
            "audit_local_install_sync.py",
            "audit_validation_artifacts.py",
            "check_public_release.py",
            "flowpilot_lifecycle.py",
            "install_flowpilot.py",
            "run_test_tier.py",
        }
        for name in json_scripts:
            with self.subTest(path=name):
                text = (SCRIPT_ROOT / name).read_text(encoding="utf-8")
                self.assertIn("json", text)


if __name__ == "__main__":
    unittest.main()
