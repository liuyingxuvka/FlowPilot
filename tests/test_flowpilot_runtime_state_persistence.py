from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router_runtime_state as runtime_state  # noqa: E402
import flowpilot_router_runtime_state_persistence as persistence  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _dummy_router(run_root: Path) -> ModuleType:
    router = ModuleType("runtime_state_persistence_test_router")
    router.RUNTIME_FLAG_DEFAULTS = {"controller_core_loaded": False, "foreground_ready": False}  # type: ignore[attr-defined]
    router.SYSTEM_CARD_SEQUENCE = ({"flag": "pm_card_delivered"},)  # type: ignore[attr-defined]
    router.MAIL_SEQUENCE = ({"flag": "mail_delivered"},)  # type: ignore[attr-defined]
    router.EXTERNAL_EVENTS = {"worker_current_node_result_returned": {"flag": "current_node_result_returned"}}  # type: ignore[attr-defined]
    router.read_json = _read_json  # type: ignore[attr-defined]
    router.read_json_if_exists = lambda path: _read_json(path) if Path(path).exists() else {}  # type: ignore[attr-defined]
    router.write_json = _write_json  # type: ignore[attr-defined]
    router.project_relative = lambda project_root, path: str(Path(path).resolve().relative_to(Path(project_root).resolve())).replace("\\", "/")  # type: ignore[attr-defined]
    router.active_run_root = lambda project_root, bootstrap_state=None: run_root  # type: ignore[attr-defined]
    router.run_state_path = lambda root: Path(root) / "router_state.json"  # type: ignore[attr-defined]
    return router


def _base_state(run_root: Path) -> dict[str, Any]:
    return {
        "schema_version": "flowpilot.run_state.v1",
        "run_id": run_root.name,
        "run_root": f".flowpilot/runs/{run_root.name}",
        "flags": {"controller_core_loaded": False, "foreground_ready": False},
        "pending_action": {
            "action_type": "await_role_decision",
            "label": "controller_waits_for_current_node_worker_result",
            "waiting_for_role": "worker",
            "expected_return_path": "packets/pkt-current/result_envelope.json",
            "controller_action_id": "controller-action-stale",
        },
        "events": [],
        "history": [],
    }


class RuntimeStatePersistenceTests(unittest.TestCase):

    def test_child_merge_preserves_foreground_clear_without_metadata_leak(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-clear-blocker-test")
        loaded_state = _base_state(run_root)
        loaded_state["active_control_blocker"] = {
            "blocker_id": "control-blocker-loaded",
            "blocker_artifact_path": ".flowpilot/runs/run-persistence-clear-blocker-test/control_blocks/loaded.json",
            "delivery_status": "pending",
        }
        loaded_state["latest_control_blocker_path"] = loaded_state["active_control_blocker"]["blocker_artifact_path"]
        persistence._attach_run_state_load_metadata(loaded_state)

        foreground_state = _base_state(run_root)
        foreground_state["active_control_blocker"] = None
        foreground_state["latest_control_blocker_path"] = None

        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertIsNone(merged["active_control_blocker"])
        self.assertIsNone(merged["latest_control_blocker_path"])
        self.assertFalse(any(str(key).startswith("_flowpilot_loaded_") for key in merged))

    def test_parent_facade_delegates_load_and_stale_save_to_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-runtime-state-load-save-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            _write_json(run_root / "router_state.json", _base_state(run_root))
            fake_router = _dummy_router(run_root)

            loaded, loaded_root = persistence.load_run_state_from_run_root(fake_router, project_root, run_root)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            assert loaded_root is not None
            self.assertEqual(loaded_root, run_root.resolve())
            self.assertTrue(str(loaded.get("_flowpilot_loaded_run_state_hash") or ""))

            loaded["flags"]["foreground_ready"] = True
            persistence.save_run_state(fake_router, run_root, loaded)
            saved = _read_json(run_root / "router_state.json")

        self.assertTrue(saved["flags"]["foreground_ready"])
        self.assertFalse(any(str(key).startswith("_flowpilot_loaded_") for key in saved))

    def test_stale_save_has_no_retired_material_generation_override(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-current-contract-test")
        loaded_state = _base_state(run_root)
        persistence._attach_run_state_load_metadata(loaded_state)

        foreground_state = _base_state(run_root)
        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertNotIn("active_material_generation", merged)
        persistence_source = (ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_runtime_state_persistence.py").read_text(encoding="utf-8")
        save_source = (ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_runtime_state_persistence_save.py").read_text(encoding="utf-8")
        for retired_name in (
            "_material_generation_key",
            "_MATERIAL_GENERATION_PROGRESS_FLAGS",
            "pm_records_material_scan_result_disposition",
        ):
            self.assertNotIn(retired_name, persistence_source + save_source)

    def test_stale_save_preserves_foreground_active_control_blocker(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-active-blocker-test")
        loaded_state = _base_state(run_root)
        persistence._attach_run_state_load_metadata(loaded_state)

        foreground_state = _base_state(run_root)
        foreground_state["active_control_blocker"] = {
            "blocker_id": "control-blocker-foreground",
            "blocker_artifact_path": ".flowpilot/runs/run-persistence-active-blocker-test/control_blocks/foreground.json",
            "delivery_status": "pending",
        }
        foreground_state["latest_control_blocker_path"] = foreground_state["active_control_blocker"]["blocker_artifact_path"]

        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertEqual(merged["active_control_blocker"]["blocker_id"], "control-blocker-foreground")
        self.assertEqual(
            merged["latest_control_blocker_path"],
            ".flowpilot/runs/run-persistence-active-blocker-test/control_blocks/foreground.json",
        )

    def test_stale_save_cannot_replace_newer_active_control_blocker_with_loaded_one(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-active-blocker-replacement-test")
        loaded_state = _base_state(run_root)
        loaded_state["active_control_blocker"] = {
            "blocker_id": "control-blocker-loaded",
            "blocker_artifact_path": ".flowpilot/runs/run-persistence-active-blocker-replacement-test/control_blocks/loaded.json",
            "delivery_status": "pending",
        }
        loaded_state["latest_control_blocker_path"] = loaded_state["active_control_blocker"]["blocker_artifact_path"]
        persistence._attach_run_state_load_metadata(loaded_state)

        foreground_state = _base_state(run_root)
        foreground_state["active_control_blocker"] = {
            "blocker_id": "control-blocker-foreground",
            "blocker_artifact_path": ".flowpilot/runs/run-persistence-active-blocker-replacement-test/control_blocks/foreground.json",
            "delivery_status": "delivered",
        }
        foreground_state["latest_control_blocker_path"] = foreground_state["active_control_blocker"]["blocker_artifact_path"]

        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertEqual(merged["active_control_blocker"]["blocker_id"], "control-blocker-foreground")
        self.assertEqual(
            merged["latest_control_blocker_path"],
            ".flowpilot/runs/run-persistence-active-blocker-replacement-test/control_blocks/foreground.json",
        )


if __name__ == "__main__":
    unittest.main()
