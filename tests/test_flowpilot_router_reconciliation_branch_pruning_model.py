from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_router_reconciliation_branch_pruning_model as model  # noqa: E402


EXPECTED_HAZARDS = {
    model.OVERCLAIM_BRANCH_EQUIVALENCE: "branch contraction overclaimed equivalence without replay evidence",
    model.MISSING_EVENT_AUTHORITY: "role-output event was recorded without durable Router authority",
    model.DUPLICATE_RUNTIME_STATE_OWNER: "runtime-state branch pruning introduced duplicate state ownership",
    model.PROGRESS_ONLY_VALIDATION: "background progress was claimed as pass without exit artifact",
}


def _selected_state(scenario: str) -> model.State:
    for label, state in model.next_states(model.initial_state()):
        if label == f"select_{scenario}":
            return state
    raise AssertionError(f"missing scenario {scenario}")


class FlowPilotRouterReconciliationBranchPruningModelTests(unittest.TestCase):
    def test_result_case_classifier_covers_shared_cases(self) -> None:
        observed_cases = set()
        accepted = set()
        for scenario in model.VALID_SCENARIOS:
            state = _selected_state(scenario)
            observed_cases.add(state.result_case)
            transitions = model.next_states(state)
            self.assertEqual(transitions[0][0], f"accept_{scenario}")
            accepted.add(transitions[0][1].scenario)

        self.assertEqual(accepted, set(model.VALID_SCENARIOS))
        self.assertEqual(observed_cases, set(model.RESULT_CASES))

    def test_known_bad_contracts_are_rejected(self) -> None:
        for scenario, expected in EXPECTED_HAZARDS.items():
            state = _selected_state(scenario)
            failures = model.branch_pruning_failures(state)
            self.assertIn(expected, failures)
            transitions = model.next_states(state)
            self.assertEqual(transitions[0][0], f"reject_{scenario}")

    def test_scheduled_receipt_effect_cases_keep_replay_gate(self) -> None:
        replay = _selected_state(model.SCHEDULED_ALREADY_RECONCILED_WAIT_TARGET_REPLAY)
        self.assertEqual(replay.result_case, "replay_required")
        self.assertTrue(replay.requires_replay_evidence)
        self.assertTrue(replay.replay_or_alignment_evidence)
        self.assertIn("pending_action_projection", replay.observable_state_writes)
        self.assertEqual(model.branch_pruning_failures(replay), [])

        blocked = _selected_state(model.SCHEDULED_RECEIPT_APPLY_BLOCKED)
        self.assertEqual(blocked.result_case, "blocked")
        self.assertFalse(blocked.contraction_allowed)
        self.assertIn("control_blocker_index", blocked.observable_state_writes)

    def test_role_output_authority_cases_preserve_not_ready_and_unauthorized(self) -> None:
        not_ready = _selected_state(model.ROLE_OUTPUT_NOT_READY_REQUIRED_FLAG)
        self.assertEqual(not_ready.result_case, "noop")
        self.assertEqual(not_ready.result_subcase, "not_ready")
        self.assertFalse(not_ready.event_recorded)
        self.assertEqual(model.branch_pruning_failures(not_ready), [])

        unauthorized = _selected_state(model.ROLE_OUTPUT_UNAUTHORIZED)
        self.assertEqual(unauthorized.result_subcase, "unauthorized")
        self.assertFalse(unauthorized.event_recorded)
        self.assertEqual(model.branch_pruning_failures(unauthorized), [])

        bad = _selected_state(model.MISSING_EVENT_AUTHORITY)
        self.assertTrue(bad.event_recorded)
        self.assertIn(EXPECTED_HAZARDS[model.MISSING_EVENT_AUTHORITY], model.branch_pruning_failures(bad))

    def test_runtime_state_resume_cases_keep_single_owner_model_only(self) -> None:
        snapshot = model.ownership_snapshot()
        self.assertEqual(snapshot["reuse_decision"], "add_child_model")
        self.assertIn(model.RUNTIME_STATE_SURFACE, snapshot["branch_owner_functions"])

        superseded = _selected_state(model.RUNTIME_PACKET_SUPERSEDED)
        self.assertEqual(superseded.result_case, "superseded")
        self.assertEqual(superseded.runtime_state_owner_count, 1)
        self.assertFalse(superseded.contraction_allowed)

        duplicate = _selected_state(model.DUPLICATE_RUNTIME_STATE_OWNER)
        self.assertIn(
            EXPECTED_HAZARDS[model.DUPLICATE_RUNTIME_STATE_OWNER],
            model.branch_pruning_failures(duplicate),
        )


if __name__ == "__main__":
    unittest.main()
