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
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


backfeed = load_module(
    "flowpilot_real_issue_backfeed",
    ROOT / "simulations" / "flowpilot_real_issue_backfeed.py",
)
contract_model = load_module(
    "flowpilot_contract_exhaustion_mesh_model",
    ROOT / "simulations" / "flowpilot_contract_exhaustion_mesh_model.py",
)


class FlowPilotRealIssueBackfeedTests(unittest.TestCase):
    def test_real_issue_backfeed_registry_bridges_every_issue_to_runtime_replay(self) -> None:
        report = backfeed.build_report()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["findings"], [])
        self.assertGreaterEqual(report["row_count"], 6)
        for row in report["rows"]:
            with self.subTest(issue_id=row["issue_id"]):
                for field in backfeed.REQUIRED_ROW_FIELDS:
                    self.assertIn(field, row)
                    self.assertNotIn(row[field], ("", None))
                self.assertFalse(row["sealed_body_copied"])
                self.assertTrue(str(row["runtime_replay_suite_id"]).endswith("_matrix"))
                self.assertEqual(row["required_evidence_owner"], backfeed.REQUIRED_EVIDENCE_OWNER)

    def test_real_issue_backfeed_cells_are_contract_exhaustion_required_cells(self) -> None:
        expected = {cell["cell_id"] for cell in backfeed.backfeed_cells()}
        actual = {
            str(cell["cell_id"])
            for cell in contract_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            if cell.get("required_evidence_owner") == backfeed.REQUIRED_EVIDENCE_OWNER
        }

        self.assertLessEqual(expected, actual)
        self.assertIn("real_issue_backfeed.real.fake_ai.pseudo_json_repeated_reissue", actual)
        self.assertIn("real_issue_backfeed.real.contract_surface.acceptance_owner_hidden_rule", actual)

    def test_real_issue_backfeed_rejects_missing_fields_and_sealed_body_copies(self) -> None:
        row = dict(backfeed.backfeed_rows()[0])
        row.pop("fake_ai_profile_id")
        row["sealed_body_copied"] = True

        findings = backfeed.backfeed_findings([row])
        finding_codes = {finding["code"] for finding in findings}

        self.assertIn("missing_backfeed_field", finding_codes)
        self.assertIn("sealed_body_copied_into_backfeed", finding_codes)


if __name__ == "__main__":
    unittest.main()
