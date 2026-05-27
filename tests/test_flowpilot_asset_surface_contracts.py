from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "skills" / "flowpilot" / "assets"
LOCAL_PREFIXES = (
    "barrier",
    "card",
    "flowpilot",
    "packet",
    "role",
    "run_packet",
)
STRUCTURE_SPLIT_CHILD_SURFACES = (
    "flowpilot_router_event_dispatcher_record",
    "flowpilot_router_expected_waits_reconciliation_pm_package",
    "flowpilot_router_role_output_bridge_events_replay",
    "flowpilot_router_runtime_state_persistence_save",
)


def assignment_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names: set[str] = set()
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def defined_or_imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            names.update(assignment_names(node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.partition(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name)
    return names


def all_literal_exports(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            return None
        exports: list[str] = []
        for item in node.value.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            exports.append(item.value)
        return exports
    return None


def declares_all_exports(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            return True
    return False


def has_local_import_surface(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module.startswith(LOCAL_PREFIXES):
            return True
    return False


class FlowPilotAssetSurfaceContractTests(unittest.TestCase):
    def test_asset_modules_have_parseable_public_surface(self) -> None:
        # Diagnostic marker: ASSET_SURFACE_CONTRACT_TEST_PATH
        paths = sorted(ASSET_ROOT.glob("*.py"))
        self.assertGreater(len(paths), 50)

        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                tree = ast.parse(text)
                names = defined_or_imported_names(tree)
                exports = all_literal_exports(tree)

                self.assertIn("from __future__ import annotations", text)
                self.assertTrue(
                    names or exports or has_local_import_surface(tree),
                    f"{path.name} exposes no public or imported surface",
                )
                if exports is not None:
                    self.assertEqual(len(exports), len(set(exports)))
                    missing = [name for name in exports if name not in names]
                    if missing:
                        self.assertTrue(
                            has_local_import_surface(tree),
                            f"{path.name} exports undefined local names without owner imports: {missing}",
                        )

    def test_facade_modules_delegate_to_owner_modules(self) -> None:
        for path in sorted(ASSET_ROOT.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "Compatibility facade" not in text:
                continue
            with self.subTest(path=path.name):
                tree = ast.parse(text)
                self.assertTrue(
                    has_local_import_surface(tree),
                    f"{path.name} facade should import owner-module symbols",
                )
                exports = all_literal_exports(tree)
                self.assertTrue(declares_all_exports(tree), f"{path.name} facade should declare __all__")
                if exports is not None:
                    self.assertTrue(exports)

    def test_structure_split_child_surfaces_are_parseable(self) -> None:
        for stem in STRUCTURE_SPLIT_CHILD_SURFACES:
            with self.subTest(stem=stem):
                path = ASSET_ROOT / f"{stem}.py"
                self.assertTrue(path.exists(), stem)
                ast.parse(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
