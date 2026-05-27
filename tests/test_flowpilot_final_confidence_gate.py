from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "simulations" / "flowpilot_final_confidence_gate.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("flowpilot_final_confidence_gate", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(MODULE_PATH.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


gate = load_gate_module()


PASSING_PAYLOADS = {
    "control_plane": {
        "ok": True,
        "live_run_audit": {
            "ok": True,
            "skipped": False,
            "run_id": "run-current",
            "findings": [],
        },
    },
    "event_idempotency": {
        "ok": True,
        "flowguard_explorer": {"ok": True},
        "safe_graph": {"ok": True},
        "progress": {"ok": True},
        "hazard_detection": {"ok": True},
    },
    "model_test_alignment": {
        "ok": True,
        "alignment_ok": True,
        "full_diagnostic_ok": True,
        "full_coverage_ok": True,
        "full_model_test_code_diagnostic": {
            "gap_counts": {},
            "gap_surface_count": 0,
        },
    },
    "known_friction": {
        "ok": True,
        "defect_family_gate_ok": True,
        "defect_family_gate_report": {
            "gate_report": {
                "confidence": "full",
                "decision": "defect_family_gate_full_confidence",
            },
            "risk_ledger_report": {
                "confidence": "full",
                "decision": "risk_evidence_full_confidence",
            },
        },
    },
}


class FlowPilotFinalConfidenceGateTests(unittest.TestCase):
    def evaluate(self, payloads: dict[str, dict]) -> dict:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                result_paths[name] = path
            return gate.evaluate_final_confidence(result_paths)

    def test_all_required_evidence_allows_full_confidence(self) -> None:
        report = self.evaluate(copy.deepcopy(PASSING_PAYLOADS))

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["decision"], gate.DECISION_FULL)
        self.assertEqual(report["blockers"], [])

    def test_skipped_live_audit_blocks_final_confidence(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["control_plane"]["ok"] = True
        payloads["control_plane"]["live_run_audit"] = {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "findings": [],
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        self.assertEqual(report["decision"], gate.DECISION_BLOCKED)
        self.assertIn("live_run_audit_skipped", report["blockers"][0]["codes"])

    def test_failed_live_audit_preserves_finding_codes(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["control_plane"]["ok"] = False
        payloads["control_plane"]["live_run_audit"] = {
            "ok": False,
            "skipped": False,
            "run_id": "run-current",
            "findings": [
                {"code": "break_glass_patch_validation_pending", "severity": "error"},
            ],
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "control_plane")
        self.assertIn("live_run_audit_failed", blocker["codes"])
        self.assertIn("control_plane_check_failed", blocker["codes"])
        self.assertIn("break_glass_patch_validation_pending", blocker["details"]["live_finding_codes"])

    def test_alignment_green_with_full_coverage_false_blocks(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["model_test_alignment"]["full_coverage_ok"] = False
        payloads["model_test_alignment"]["full_model_test_code_diagnostic"] = {
            "gap_counts": {"needs_structure_split": 3},
            "gap_surface_count": 3,
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "model_test_alignment")
        self.assertIn("full_coverage_ok_false", blocker["codes"])
        self.assertEqual(blocker["details"]["gap_counts"], {"needs_structure_split": 3})

    def test_known_friction_scoped_risk_ledger_blocks(self) -> None:
        payloads = copy.deepcopy(PASSING_PAYLOADS)
        payloads["known_friction"]["defect_family_gate_report"]["risk_ledger_report"] = {
            "confidence": "scoped",
            "decision": "risk_evidence_scoped_confidence",
        }

        report = self.evaluate(payloads)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "known_friction")
        self.assertIn("risk_ledger_confidence_not_full", blocker["codes"])
        self.assertEqual(blocker["details"]["risk_ledger_confidence"], "scoped")

    def test_missing_required_payload_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-final-confidence-missing-") as tmp_name:
            root = Path(tmp_name)
            result_paths = {
                name: root / f"{name}.json"
                for name in PASSING_PAYLOADS
            }
            for name, payload in PASSING_PAYLOADS.items():
                if name == "event_idempotency":
                    continue
                result_paths[name].write_text(json.dumps(payload), encoding="utf-8")

            report = gate.evaluate_final_confidence(result_paths)

        self.assertFalse(report["ok"])
        blocker = next(item for item in report["blockers"] if item["evidence"] == "event_idempotency")
        self.assertIn("missing_evidence", blocker["codes"])


if __name__ == "__main__":
    unittest.main()
