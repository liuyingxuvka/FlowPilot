from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import packet_runtime  # noqa: E402


STARTUP_ANSWERS = {
    "background_agents": "allow",
    "scheduled_continuation": "manual",
    "display_surface": "chat",
    "provenance": "explicit_user_reply",
}


class FlowPilotRouterStartupRuntimeTests(unittest.TestCase):
    def make_project(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="flowpilot-startup-runtime-"))

    def rel(self, root: Path, path: Path) -> str:
        return str(path.relative_to(root)).replace("\\", "/")

    def test_startup_intake_powershell_sources_with_non_ascii_use_utf8_bom(self) -> None:
        scripts = (
            ROOT / "skills" / "flowpilot" / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1",
            ROOT / "docs" / "ui" / "startup_intake_desktop_preview" / "flowpilot_startup_intake.ps1",
        )
        for script in scripts:
            with self.subTest(script=script.relative_to(ROOT).as_posix()):
                data = script.read_bytes()
                self.assertTrue(any(byte >= 0x80 for byte in data), "test requires non-ASCII script source")
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"), "non-ASCII .ps1 source must be UTF-8 BOM for Windows PowerShell 5.1")

    def test_startup_intake_ui_writes_utf8_without_bom(self) -> None:
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("startup intake WPF smoke requires Windows PowerShell")
        root = self.make_project()
        output_dir = root / "startup-intake-output"
        script = ROOT / "skills" / "flowpilot" / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"
        result = subprocess.run(
            [
                "powershell",
                "-STA",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-OutputDir",
                str(output_dir),
                "-HeadlessConfirmText",
                "Check startup intake encoding",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        for name in (
            "startup_intake_result.json",
            "startup_intake_receipt.json",
            "startup_intake_envelope.json",
            "startup_intake_body.md",
        ):
            data = (output_dir / name).read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), name)
        for name in (
            "startup_intake_result.json",
            "startup_intake_receipt.json",
            "startup_intake_envelope.json",
        ):
            self.assertEqual((output_dir / name).read_bytes()[:1], b"{", name)
        result_payload = json.loads((output_dir / "startup_intake_result.json").read_text(encoding="utf-8"))
        self.assertEqual(result_payload["launch_mode"], "headless")
        self.assertTrue(result_payload["headless"])
        self.assertFalse(result_payload["formal_startup_allowed"])

    def test_startup_intake_ui_runs_from_installed_skill_without_repo_assets(self) -> None:
        if sys.platform != "win32" or shutil.which("powershell") is None:
            self.skipTest("startup intake WPF smoke requires Windows PowerShell")
        root = self.make_project()
        install_root = root / "skills-install" / "flowpilot"
        shutil.copytree(ROOT / "skills" / "flowpilot", install_root)
        output_dir = root / "startup-intake-output"
        script = install_root / "assets" / "ui" / "startup_intake" / "flowpilot_startup_intake.ps1"

        result = subprocess.run(
            [
                "powershell",
                "-STA",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-OutputDir",
                str(output_dir),
                "-HeadlessConfirmText",
                "Check startup intake installed skill asset lookup",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue((output_dir / "startup_intake_result.json").is_file())

    def test_router_accepts_utf8_bom_json_control_artifact(self) -> None:
        root = self.make_project()
        path = root / "bom.json"
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"ok": True}).encode("utf-8"))
        self.assertEqual(router.read_json(path), {"ok": True})

    def test_startup_intake_body_bom_is_not_injected_into_pm_packet_body(self) -> None:
        root = self.make_project()
        body_path = root / "startup_intake_body.md"
        body_path.write_bytes(b"\xef\xbb\xbfBuild with the existing requirements.")
        body_hash = packet_runtime.sha256_file(body_path)
        body = router._build_user_intake_body_from_ref(
            root,
            {
                "body_path": self.rel(root, body_path),
                "body_hash": body_hash,
                "startup_intake_record_path": "startup_intake/startup_intake_record.json",
                "startup_intake_receipt_path": "startup_intake/startup_intake_receipt.json",
                "startup_intake_envelope_path": "startup_intake/startup_intake_envelope.json",
            },
            STARTUP_ANSWERS,
        )
        self.assertIn("Build with the existing requirements.", body)
        self.assertNotIn("\ufeff", body)


if __name__ == "__main__":
    unittest.main()
