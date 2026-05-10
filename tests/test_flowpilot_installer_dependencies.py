from __future__ import annotations

import importlib.util
import sys
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


install_flowpilot = load_module(
    "flowpilot_test_install_flowpilot",
    ROOT / "scripts" / "install_flowpilot.py",
)
check_public_release = load_module(
    "flowpilot_test_check_public_release",
    ROOT / "scripts" / "check_public_release.py",
)


class FlowPilotInstallerDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = install_flowpilot.load_manifest()

    def dependency(self, name: str) -> dict:
        for dependency in self.manifest["dependencies"]:
            if dependency["name"] == name:
                return dependency
        self.fail(f"missing dependency: {name}")

    def test_dependency_policy_declares_required_and_optional_tiers(self) -> None:
        policy = install_flowpilot.dependency_policy_summary(self.manifest)

        self.assertEqual(
            policy["required"],
            ["flowpilot", "flowguard", "model-first-function-flow", "grill-me"],
        )
        self.assertIn("flowguard", policy["required_python_packages"])
        self.assertIn("model-first-function-flow", policy["required_codex_skills"])
        self.assertIn("grill-me", policy["required_codex_skills"])
        self.assertIn("frontend-design", policy["optional"])
        self.assertIn("design-iterator", policy["optional_codex_skills"])
        self.assertIn("--install-flowguard", policy["policy"])
        self.assertIn("--include-optional", policy["policy"])

    def test_flowguard_source_is_public_github_python_package(self) -> None:
        flowguard = self.dependency("flowguard")

        self.assertTrue(flowguard["required"])
        self.assertEqual(flowguard["type"], "python_package")
        self.assertEqual(flowguard["source"]["kind"], "github_python_package")
        self.assertEqual(flowguard["source"]["repo"], "liuyingxuvka/FlowGuard")
        self.assertEqual(flowguard["install"]["requires_explicit_flag"], "--install-flowguard")
        self.assertTrue(install_flowpilot.source_is_complete(flowguard["source"]))
        self.assertEqual(
            install_flowpilot.parse_github_source(flowguard["source"]),
            ("liuyingxuvka/FlowGuard", "main", ""),
        )

    def test_flowguard_python_package_dry_run_describes_install_without_network(self) -> None:
        flowguard = self.dependency("flowguard")

        action = install_flowpilot.install_python_package(flowguard, dry_run=True)

        self.assertTrue(action["ok"])
        self.assertTrue(action["dry_run"])
        self.assertEqual(action["action"], "install_github_python_package")
        self.assertEqual(action["source"], "https://github.com/liuyingxuvka/FlowGuard")
        self.assertEqual(action["ref"], "main")
        self.assertEqual(action["path"], ".")
        self.assertIn("pip install", action["command"])

    def test_public_release_probe_targets_flowguard_pyproject(self) -> None:
        flowguard = self.dependency("flowguard")

        self.assertTrue(check_public_release.source_is_complete(flowguard["source"]))
        self.assertEqual(
            check_public_release.github_raw_url(flowguard["source"], "pyproject.toml"),
            "https://raw.githubusercontent.com/liuyingxuvka/FlowGuard/main/pyproject.toml",
        )


if __name__ == "__main__":
    unittest.main()
