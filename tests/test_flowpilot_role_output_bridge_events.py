from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(ASSETS))

import flowpilot_router_role_output_bridge_events as role_output_bridge_events  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dummy_router(project_root: Path) -> ModuleType:
    router = ModuleType("dummy_role_output_bridge_router")
    router._run_state_has_event = lambda run_state, event: False
    router._controller_actions_dir = lambda run_root: run_root / "controller_actions"
    router._read_json_for_runtime_scan = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    router._controller_wait_allowed_external_events = lambda entry: entry.get("allowed_external_events") or []
    router._pending_expected_external_event_groups = lambda run_state: []
    router._gate_completion_wait_group = lambda group: group
    router.resolve_project_path = lambda root, value: (root / value) if not Path(value).is_absolute() else Path(value)
    router.read_json_if_exists = lambda path: json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
    router.project_relative = lambda root, path: Path(path).resolve().relative_to(root.resolve()).as_posix()
    return router


class RoleOutputBridgeEventChildTests(unittest.TestCase):
    def test_role_output_bridge_event_child_reads_body_and_checks_pending_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-role-output-bridge-events-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            body_path = run_root / "role_outputs" / "material.json"
            _write_json(body_path, {"sufficient": True})
            router = _dummy_router(project_root)

            payload = role_output_bridge_events._role_output_body_payload_from_record(
                router,
                project_root,
                {"body_path": ".flowpilot/runs/run-test/role_outputs/material.json"},
                {
                    "event_name": "reviewer_reports_material_sufficient",
                    "body_ref": {"path": ".flowpilot/runs/run-test/role_outputs/material.json"},
                },
            )

            self.assertTrue(payload["sufficient"])
            self.assertEqual(payload["_role_output_envelope"]["event_name"], "reviewer_reports_material_sufficient")
            self.assertTrue(
                role_output_bridge_events._role_output_event_has_durable_authority(
                    router,
                    run_root,
                    {
                        "flags": {},
                        "pending_action": {
                            "action_type": "await_role_decision",
                            "allowed_external_events": ["reviewer_reports_material_sufficient"],
                        },
                    },
                    "reviewer_reports_material_sufficient",
                )
            )
            self.assertFalse(
                role_output_bridge_events._role_output_event_has_durable_authority(
                    router,
                    run_root,
                    {"flags": {}, "pending_action": {}},
                    "reviewer_reports_material_sufficient",
                )
            )


if __name__ == "__main__":
    unittest.main()
