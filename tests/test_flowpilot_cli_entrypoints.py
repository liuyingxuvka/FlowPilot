from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


def hidden_process_kwargs() -> dict[str, object]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        "startupinfo": startupinfo,
    }


def run_cli(args: Sequence[str], *, expected_codes: set[int] | None = None) -> subprocess.CompletedProcess[str]:
    expected = {0} if expected_codes is None else expected_codes
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        **hidden_process_kwargs(),
    )
    if completed.returncode not in expected:
        raise AssertionError(
            f"{args} returned {completed.returncode}\nSTDOUT:\n{completed.stdout[-2000:]}\nSTDERR:\n{completed.stderr[-2000:]}"
        )
    return completed


def run_json_cli(args: Sequence[str], *, expected_codes: set[int] | None = None) -> dict[str, object]:
    completed = run_cli(args, expected_codes=expected_codes)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{args} did not print JSON:\n{completed.stdout[-2000:]}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{args} printed non-object JSON")
    return payload


class FlowPilotCliEntrypointTests(unittest.TestCase):
    def test_install_sync_and_release_audit_entrypoints_emit_structured_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-cli-skills-") as tmp_name:
            skills_dir = str(Path(tmp_name) / "skills")

            install = run_json_cli(
                [
                    "scripts/install_flowpilot.py",
                    "--check",
                    "--dry-run",
                    "--json",
                    "--skills-dir",
                    skills_dir,
                ],
                expected_codes={0, 1},
            )
            self.assertIn("dependency_policy", install)
            self.assertIn("dependencies", install)
            self.assertIn("install_actions", install)

            audit = run_json_cli(
                [
                    "scripts/audit_local_install_sync.py",
                    "--json",
                    "--skills-dir",
                    skills_dir,
                ],
                expected_codes={0, 1},
            )
            self.assertIn("checks", audit)
            self.assertTrue(any("repo_owned_skill_fresh" in check["name"] for check in audit["checks"]))

        check_install = run_json_cli(["scripts/check_install.py"], expected_codes={0, 1})
        self.assertIn("checks", check_install)

        release = run_json_cli(
            [
                "scripts/check_public_release.py",
                "--json",
                "--skip-url-check",
                "--skip-validation",
            ],
            expected_codes={0, 1},
        )
        self.assertEqual(release["scope"], "flowpilot_repository_only")
        self.assertTrue(release["no_companion_publish_authority"])
        self.assertTrue(any(check["name"] == "git_worktree_clean" for check in release["checks"]))

    def test_packet_and_output_entrypoint_help_exposes_public_commands(self) -> None:
        packets = run_cli(["scripts/flowpilot_packets.py", "--help"])
        self.assertIn("issue", packets.stdout)
        self.assertIn("user-intake", packets.stdout)
        self.assertIn("audit-chain", packets.stdout)

        outputs = run_cli(["scripts/flowpilot_outputs.py", "--help"])
        self.assertIn("prepare-output", outputs.stdout)
        self.assertIn("submit-output", outputs.stdout)
        self.assertIn("verify-envelope", outputs.stdout)

    def test_lifecycle_scan_entrypoint_is_read_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-lifecycle-cli-") as tmp_name:
            root = Path(tmp_name)
            payload = run_json_cli(
                [
                    "scripts/flowpilot_lifecycle.py",
                    "--root",
                    str(root),
                    "--json",
                ]
            )

            self.assertEqual(payload["schema_version"], "flowpilot-lifecycle/v2")
            self.assertIn(payload["decision"], {"actions_required", "reconciled"})
            self.assertFalse((root / ".flowpilot" / "lifecycle" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
