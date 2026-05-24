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
    router.EXTERNAL_EVENTS = {"pm_approves_startup_activation": {"flag": "startup_activation_approved"}}  # type: ignore[attr-defined]
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
            "label": "controller_waits_for_pm_startup_activation",
            "waiting_for_role": "project_manager",
            "expected_return_path": "mailbox/outbox/events/pm_startup_activation.envelope.json",
            "controller_action_id": "controller-action-stale",
        },
        "events": [],
        "history": [],
    }


class RuntimeStatePersistenceTests(unittest.TestCase):
    def test_child_merge_preserves_foreground_clear_without_metadata_leak(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-test")
        loaded_state = _base_state(run_root)
        persistence._attach_run_state_load_metadata(loaded_state)
        loaded_state["history"].append({"event": "daemon_tick_after_load"})

        foreground_state = _base_state(run_root)
        foreground_state["pending_action"] = None
        foreground_state["flags"]["foreground_ready"] = True
        foreground_state["events"].append({"event": "pm_approves_startup_activation"})

        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertIsNone(merged["pending_action"])
        self.assertTrue(merged["flags"]["foreground_ready"])
        self.assertIn({"event": "pm_approves_startup_activation"}, merged["events"])
        self.assertIn({"event": "daemon_tick_after_load"}, merged["history"])
        self.assertNotIn(persistence._RUN_STATE_LOAD_META_HASH, merged)
        self.assertNotIn(persistence._RUN_STATE_LOAD_META_FLAGS, merged)
        self.assertNotIn(persistence._RUN_STATE_LOAD_META_PENDING, merged)

    def test_stale_save_does_not_restore_material_progress_flags_after_new_generation(self) -> None:
        run_root = Path(".flowpilot/runs/run-persistence-material-generation-test")
        loaded_state = _base_state(run_root)
        loaded_state["flags"].update(
            {
                "material_scan_packets_relayed": True,
                "worker_packets_delivered": True,
                "worker_scan_results_returned": True,
                "material_scan_results_relayed_to_pm": True,
                "material_scan_result_disposition_recorded": True,
            }
        )
        persistence._attach_run_state_load_metadata(loaded_state)

        foreground_state = _base_state(run_root)
        foreground_state["active_material_generation"] = {
            "schema_version": "flowpilot.active_material_generation.v1",
            "packet_generation_id": "repair-tx-material-gen-001",
            "repair_transaction_id": "repair-tx-material",
            "batch_id": "repair-tx-material-gen-001-batch",
        }
        foreground_state["flags"].update(
            {
                "material_scan_packets_relayed": False,
                "worker_packets_delivered": False,
                "worker_scan_results_returned": False,
                "material_scan_results_relayed_to_pm": False,
                "material_scan_result_disposition_recorded": False,
            }
        )

        merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)

        self.assertEqual(
            merged["active_material_generation"]["packet_generation_id"],
            "repair-tx-material-gen-001",
        )
        self.assertFalse(merged["flags"]["material_scan_packets_relayed"])
        self.assertFalse(merged["flags"]["worker_packets_delivered"])
        self.assertFalse(merged["flags"]["worker_scan_results_returned"])
        self.assertFalse(merged["flags"]["material_scan_results_relayed_to_pm"])
        self.assertFalse(merged["flags"]["material_scan_result_disposition_recorded"])

    def test_parent_facade_delegates_load_and_stale_save_to_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-runtime-state-persistence-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-persistence-test"
            router = _dummy_router(run_root)
            state_path = router.run_state_path(run_root)  # type: ignore[attr-defined]
            _write_json(state_path, _base_state(run_root))

            loaded_state, loaded_root = persistence.load_run_state_from_run_root(router, project_root, run_root)
            self.assertEqual(loaded_root, run_root.resolve())
            self.assertIn(persistence._RUN_STATE_LOAD_META_HASH, loaded_state)

            foreground_state = _read_json(state_path)
            foreground_state["pending_action"] = None
            foreground_state["flags"]["startup_activation_approved"] = True
            foreground_state["events"].append({"event": "pm_approves_startup_activation"})
            _write_json(state_path, foreground_state)

            direct_merged = persistence._merge_stale_run_state_save(foreground_state, loaded_state)
            self.assertIsNone(direct_merged["pending_action"])
            loaded_state["history"].append({"event": "daemon_tick_after_foreground_clear"})
            persistence.save_run_state(router, run_root, loaded_state)

            saved = _read_json(state_path)
            self.assertIsNone(saved["pending_action"])
            self.assertTrue(saved["flags"]["startup_activation_approved"])
            self.assertIn({"event": "pm_approves_startup_activation"}, saved["events"])
            self.assertIn({"event": "daemon_tick_after_foreground_clear"}, saved["history"])
            self.assertNotIn(persistence._RUN_STATE_LOAD_META_HASH, saved)
            self.assertIn(persistence._RUN_STATE_LOAD_META_HASH, loaded_state)
            facade_loaded, _ = runtime_state.load_run_state_from_run_root(router, project_root, run_root)
            self.assertIn(persistence._RUN_STATE_LOAD_META_HASH, facade_loaded)


if __name__ == "__main__":
    unittest.main()
