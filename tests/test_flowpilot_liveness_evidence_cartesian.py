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


matrix = load_module(
    "flowpilot_liveness_evidence_cartesian",
    ROOT / "simulations" / "flowpilot_liveness_evidence_cartesian.py",
)


class FlowPilotLivenessEvidenceCartesianTests(unittest.TestCase):
    def test_liveness_evidence_cartesian_materializes_full_dimension_product(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["row_count"], matrix.required_case_count())
        self.assertEqual(report["row_count"], 35_280)
        self.assertEqual(set(report["dimensions"]["roles"]), set(matrix.ROLES))
        self.assertEqual(set(report["dimensions"]["ack_states"]), set(matrix.ACK_STATES))
        self.assertEqual(set(report["dimensions"]["result_states"]), set(matrix.RESULT_STATES))
        self.assertEqual(set(report["dimensions"]["progress_states"]), set(matrix.PROGRESS_STATES))
        self.assertEqual(set(report["dimensions"]["legacy_pollution_states"]), set(matrix.LEGACY_POLLUTION_STATES))
        self.assertEqual(set(report["dimensions"]["time_buckets"]), set(matrix.TIME_BUCKETS))
        self.assertEqual(set(report["dimensions"]["reminder_history_states"]), set(matrix.REMINDER_HISTORY_STATES))
        self.assertLessEqual(
            {
                "wait_missing_ack",
                "remind_missing_ack",
                "replace_missing_ack",
                "wait_fresh_evidence",
                "remind_stale_progress",
                "replace_stale_progress",
                "final_result_wins",
                "mechanical_result_block",
                "invalid_setup",
            },
            set(report["by_reaction"]),
        )
        self.assertGreater(report["legacy_pollution_case_count"], 0)
        self.assertGreater(report["runtime_executable_count"], 0)

    def test_liveness_evidence_cartesian_runtime_executable_cases_match_oracle(self) -> None:
        required = {
            "roles": set(matrix.ROLES),
            "ack_states": set(matrix.ACK_STATES),
            "progress_states": set(matrix.PROGRESS_STATES) - {"after_accepted_result"},
            "legacy_pollution_states": set(matrix.LEGACY_POLLUTION_STATES),
            "time_buckets": set(matrix.TIME_BUCKETS),
            "reactions": {
                row["expected_reaction"]
                for row in matrix.build_rows()
                if row["runtime_executable"]
            },
        }
        covered = {key: set() for key in required}
        selected = []

        for case in matrix.iter_cases():
            expected = matrix.expected_wait_reaction(case)
            if not expected["runtime_executable"]:
                continue
            values = {
                "roles": case.role,
                "ack_states": case.ack_state,
                "progress_states": case.progress_state,
                "legacy_pollution_states": case.legacy_pollution,
                "time_buckets": case.time_bucket,
                "reactions": expected["reaction"],
            }
            if not any(values[key] not in covered[key] for key in required):
                continue
            selected.append((case, expected))
            for key, value in values.items():
                covered[key].add(value)
            if all(required[key] <= covered[key] for key in required):
                break

        for key in required:
            self.assertLessEqual(required[key], covered[key], key)

        for case, expected in selected:
            with self.subTest(case_id=case.case_id):
                observed = matrix.materialize_runtime_case(case)
                self.assertEqual(observed["decision"], expected["decision"])
                self.assertEqual(observed["state"], expected["state"])
                self.assertNotIn("current_liveness_failure", str(observed["wait_recovery"]))
                self.assertNotIn("timeout_unknown", str(observed["wait_recovery"]))
                if case.legacy_pollution != "none":
                    self.assertTrue(expected["legacy_pollution_ignored"])
        self.assertLess(len(selected), 100)

    def test_liveness_legacy_pollution_never_changes_expected_reaction(self) -> None:
        baseline_by_shape: dict[tuple[str, str, str, str, str, str], str] = {}
        for case in matrix.iter_cases():
            shape = (
                case.role,
                case.ack_state,
                case.result_state,
                case.progress_state,
                case.time_bucket,
                case.reminder_history,
            )
            reaction = matrix.expected_wait_reaction(case)["reaction"]
            if case.legacy_pollution == "none":
                baseline_by_shape[shape] = reaction
                continue
            self.assertEqual(reaction, baseline_by_shape[shape])


if __name__ == "__main__":
    unittest.main()
