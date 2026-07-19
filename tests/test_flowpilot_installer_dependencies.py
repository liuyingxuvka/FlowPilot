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
            ["flowpilot", "flowguard", "flowguard-agent-skill"],
        )
        self.assertIn("flowguard", policy["required_python_packages"])
        self.assertIn("flowguard-agent-skill", policy["required_codex_skills"])
        self.assertEqual(policy["optional"], ["autonomous-concept-ui-redesign"])
        self.assertIn("autonomous-concept-ui-redesign", policy["optional_codex_skills"])
        self.assertNotIn("frontend-design", policy["optional"])
        self.assertNotIn("design-iterator", policy["optional_codex_skills"])
        self.assertIn("--install-flowguard", policy["policy"])
        self.assertIn("--include-optional", policy["policy"])

    def test_current_flowguard_agent_skill_replaces_retired_model_first_dependency(self) -> None:
        flowguard_skill = self.dependency("flowguard-agent-skill")

        self.assertTrue(flowguard_skill["required"])
        self.assertEqual(flowguard_skill["type"], "codex_skill")
        self.assertEqual(flowguard_skill["install_name"], "flowguard")
        self.assertEqual(flowguard_skill["source"]["path"], ".agents/skills/flowguard")
        self.assertNotIn(
            "model-first-function-flow",
            {item["name"] for item in self.manifest["dependencies"]},
        )

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

    def test_autonomous_ui_companion_uses_current_flowpilot_public_source(self) -> None:
        companion = self.dependency("autonomous-concept-ui-redesign")

        self.assertFalse(companion["required"])
        self.assertTrue(companion["companion"])
        self.assertEqual(companion["source"]["repo"], "liuyingxuvka/FlowPilot")
        self.assertEqual(companion["source"]["ref"], "main")
        self.assertEqual(
            companion["source"]["path"],
            "skills/autonomous-concept-ui-redesign",
        )
        self.assertEqual(
            check_public_release.github_skill_raw_url(companion["source"]),
            "https://raw.githubusercontent.com/liuyingxuvka/FlowPilot/main/skills/"
            "autonomous-concept-ui-redesign/SKILL.md",
        )

    def test_public_release_secret_patterns_reject_escaped_local_paths(self) -> None:
        text = '{"root": "' + "C:" + "\\\\" + "Users" + "\\\\" + "liu_y" + "\\\\" + "Documents" + '"}'

        self.assertTrue(any(pattern.search(text) for pattern in check_public_release.SECRET_PATTERNS))

    def test_public_release_allows_only_the_canonical_public_flowguard_ledger(self) -> None:
        for path in check_public_release.PUBLIC_FLOWGUARD_PATHS:
            with self.subTest(path=path):
                self.assertFalse(check_public_release.path_has_private_component(path))

        for path in (
            ".flowguard/private.json",
            ".flowguard/behavior_commitment_ledger/local-receipt.json",
            ".flowguard/project.toml",
        ):
            with self.subTest(path=path):
                self.assertTrue(check_public_release.path_has_private_component(path))

    def test_flowpilot_skill_package_includes_startup_intake_icon(self) -> None:
        flowpilot = self.dependency("flowpilot")

        self.assertEqual(flowpilot["repo_path"], "skills/flowpilot")
        self.assertTrue(
            (ROOT / "skills" / "flowpilot" / "assets" / "brand" / "flowpilot-icon-default.png").is_file()
        )


if __name__ == "__main__":
    unittest.main()
