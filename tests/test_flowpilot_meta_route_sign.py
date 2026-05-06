from __future__ import annotations

import unittest

from simulations import meta_model


class FlowPilotMetaRouteSignTests(unittest.TestCase):
    def test_next_node_entry_rejects_stale_route_sign_evidence(self) -> None:
        state = meta_model.State(
            checkpoint_written=True,
            completed_chunks=1,
            required_chunks=3,
            node_acceptance_plan_written=True,
            current_node_high_standard_recheck_written=True,
            current_node_minimum_sufficient_complexity_review_written=True,
            user_flow_diagram_refreshed=True,
            visible_user_flow_diagram_emitted=True,
            user_flow_diagram_chat_display_required=True,
            user_flow_diagram_chat_displayed=True,
            user_flow_diagram_reviewer_display_checked=True,
            user_flow_diagram_reviewer_route_match_checked=True,
            user_flow_diagram_fresh_for_current_node=False,
        )

        result = meta_model.next_route_node_requires_fresh_route_sign(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("stale FlowPilot Route Sign", result.message)

    def test_next_node_entry_passes_after_route_sign_gate_reset(self) -> None:
        state = meta_model.State(
            checkpoint_written=True,
            completed_chunks=1,
            required_chunks=3,
            node_acceptance_plan_written=False,
            **meta_model._reset_user_flow_diagram_gate(),
        )

        result = meta_model.next_route_node_requires_fresh_route_sign(state, trace=())

        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
