from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

from flowpilot_prompt_store import (  # noqa: E402
    PromptStore,
    PromptStoreError,
    load_prompt_manifest,
    prompt_entry,
    render_prompt_text,
)


class FlowPilotPromptStoreTests(unittest.TestCase):
    def test_manifest_loads_and_renders_controller_prompt(self) -> None:
        manifest = load_prompt_manifest()
        self.assertEqual(manifest["schema_version"], "flowpilot.prompt_store_manifest.v1")
        entry = prompt_entry("controller.action_ledger_table")
        self.assertEqual(entry["path"], "prompts/controller/action_ledger_table.md")

        text = render_prompt_text(
            "controller.action_ledger_table",
            {
                "break_glass_text": "Break glass only for router control-plane faults.",
                "patrol_command": "python skills/flowpilot/assets/flowpilot_router.py --root . --json controller-patrol-timer --seconds 60",
            },
        )

        self.assertIn("You are Controller only", text)
        self.assertIn("continuous_controller_standby", text)
        self.assertIn("user-visible message is needed", text)
        self.assertIn("Quiet patrol", text)
        self.assertIn("Break glass only", text)
        self.assertNotIn("${", text)

    def test_run_root_store_prefers_copied_runtime_kit(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="flowpilot-prompt-store-"))
        try:
            run_root = temp_root / ".flowpilot" / "runs" / "run-test"
            shutil.copytree(ASSETS / "runtime_kit", run_root / "runtime_kit", ignore=shutil.ignore_patterns("__pycache__"))
            store = PromptStore.from_run_root(run_root)
            self.assertEqual(store.manifest_path(), run_root / "runtime_kit" / "prompts" / "manifest.json")
            self.assertIn("ACK is receipt only", store.render("cards.post_ack_policy"))
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_run_root_store_rejects_missing_copied_runtime_kit(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="flowpilot-prompt-store-missing-kit-"))
        try:
            run_root = temp_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            with self.assertRaisesRegex(PromptStoreError, "run runtime kit missing"):
                PromptStore.from_run_root(run_root)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_unknown_prompt_missing_variable_and_missing_asset_are_rejected(self) -> None:
        with self.assertRaisesRegex(PromptStoreError, "unknown prompt id"):
            render_prompt_text("missing.prompt")

        with self.assertRaisesRegex(PromptStoreError, "missing template variables"):
            render_prompt_text("startup.heartbeat_resume", {"run_id": "run-test"})

        temp_root = Path(tempfile.mkdtemp(prefix="flowpilot-prompt-store-missing-"))
        try:
            shutil.copytree(ASSETS / "runtime_kit" / "prompts", temp_root / "prompts")
            (temp_root / "prompts" / "cards" / "post_ack_policy.md").unlink()
            with self.assertRaisesRegex(PromptStoreError, "prompt asset missing"):
                PromptStore(temp_root).render("cards.post_ack_policy")
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_hash_mismatch_is_rejected_without_inline_fallback(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="flowpilot-prompt-store-hash-"))
        try:
            shutil.copytree(ASSETS / "runtime_kit" / "prompts", temp_root / "prompts")
            asset = temp_root / "prompts" / "cards" / "post_ack_policy.md"
            asset.write_text(asset.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(PromptStoreError, "hash mismatch"):
                PromptStore(temp_root).render("cards.post_ack_policy")
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_prompt_manifest_has_existing_hashed_assets(self) -> None:
        manifest = load_prompt_manifest()
        prompt_root = ASSETS / "runtime_kit"
        for entry in manifest["prompts"]:
            with self.subTest(prompt_id=entry["id"]):
                path = prompt_root / entry["path"]
                self.assertTrue(path.exists(), entry)
                self.assertEqual(PromptStore(prompt_root).content_hash(entry["id"]), entry["sha256"])
                self.assertIsInstance(entry.get("template_variables"), list)

        encoded = json.dumps(manifest, sort_keys=True)
        self.assertIn("controller.action_ledger_table", encoded)
        self.assertIn("startup.heartbeat_resume", encoded)
        self.assertIn("packets.packet_identity_boundary", encoded)

    def test_packet_prompt_assets_render_without_inline_fallback(self) -> None:
        packet_boundary = render_prompt_text(
            "packets.packet_identity_boundary",
            {
                "packet_identity_marker": "flowpilot_packet_identity",
                "role": "worker",
            },
        )
        self.assertIn("flowpilot_packet_identity: true", packet_boundary)
        self.assertIn("recipient_role: worker", packet_boundary)
        self.assertIn("Packet ACK is receipt only", packet_boundary)

        result_boundary = render_prompt_text(
            "packets.result_identity_boundary",
            {
                "result_identity_marker": "flowpilot_result_identity",
                "role": "worker",
            },
        )
        self.assertIn("flowpilot_result_identity: true", result_boundary)
        self.assertIn("completed_by_role: worker", result_boundary)

        output_contract = render_prompt_text(
            "packets.output_contract_section",
            {
                "allowed_decisions_block": "",
                "body_template_block": "",
                "json_contract": '{\n  "contract_id": "demo"\n}',
                "required_envelope_block": "",
                "required_sections_block": "",
                "required_values_block": "",
                "segment_values_block": "",
            },
        )
        self.assertIn("## Output Contract", output_contract)
        self.assertIn('"contract_id": "demo"', output_contract)
        self.assertIn("Contract Self-Check", output_contract)


if __name__ == "__main__":
    unittest.main()
