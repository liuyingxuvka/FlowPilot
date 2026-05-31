"""FlowGuard model for the FlowPilot current-node router packet loop.

Risk intent brief:
- Prevent Controller from turning packet relay into route authority.
- Protect sealed packet/result bodies and project evidence from Controller
  reads or authorship.
- Model-critical durable state: PM route activation, current-node packet
  registration, PM high-standard gate, router direct dispatch, worker
  dispatch, active-holder packet lease, fast-lane mechanical retry/result
  submission, Controller next-action notice, PM result disposition, formal
  reviewer gate release, reviewer pass/block, route mutation, stale
  evidence/frontier marking, node completion, final route-wide ledger
  source-of-truth generation, same-scope replay, generated-resource and visual
  evidence closure, and segmented final backward replay.
- Adversarial branches include packet registration before route activation,
  worker dispatch before router direct dispatch, reviewer pass before PM
  disposition and formal gate release, result relay before packet-ledger checks,
  reviewer result-review card before PM gate release, FlowGuard operator packet relay without a FlowGuard operator card, repair/recheck
  bypasses around the reviewer,
  router wait events that are impossible under the active node kind, parent
  repair lanes that target leaf/current-node worker dispatch, collapsed repair
  outcome tables that map success/blocker/protocol-blocker to one
  business-validated event,
  route mutation without reviewer block or stale markers, PM completion before
  reviewer pass, final ledger without a current route scan/zero unresolved
  items/source-of-truth file, stale/unresolved evidence, pending generated
  resources, missing screenshots for UI/visual work, old assets reused as
  current evidence, final replay without a clean ledger or segment decisions,
  Controller body reads, and Controller-origin project evidence.
- Hard invariants: current-node packets require active route and fresh frontier;
  controller-only mode fail-closes to PM when no legal next action exists;
  expected PM/reviewer role-event waits must not be materialized as
  no-next-action blockers;
  current-node packets gate write grants; router direct dispatch gates worker work;
  worker and FlowGuard operator results are
  packet-ledger checked before PM relay; PM dispositions worker results before
  formal reviewer gate packages; active-holder fast-lane
  closure writes a Controller-visible next-action notice before cross-role relay; repair/recheck returns to the
  reviewer before PM completion; reviewer result decisions require the
  formal PM gate package and result-review system card; mutation requires reviewer block and stale
  evidence/frontier markers; same-scope replay reruns after mutation;
  PM node completion updates the durable completion ledger before parent replay
  or task completion projection;
  evidence/quality package and reviewer evidence quality pass precede final
  ledger source-of-truth generation; final ledger and segmented replay are
  ordered terminal gates; Controller remains envelope-only.
- Blindspot: this is an abstract control-plane model, not a replay adapter for
  the concrete router implementation.
"""


from __future__ import annotations

from flowguard import Workflow

from flowpilot_router_loop_model_hazards import hazard_states
from flowpilot_router_loop_model_invariants import INVARIANTS, invariant_failures, router_loop_invariant
from flowpilot_router_loop_model_state import (
    EXPECTED_ROLE_EVENT_CONTRACTS,
    Action,
    EventContract,
    State,
    Tick,
    Transition,
    initial_state,
)
from flowpilot_router_loop_model_transitions import (
    expected_role_event_waits,
    expected_wait_hazard_states,
    next_safe_states,
    RouterLoopStep,
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 110


def build_workflow() -> Workflow:
    return Workflow((RouterLoopStep(),), name="flowpilot_router_current_node_loop")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


__all__ = [
    "EXPECTED_ROLE_EVENT_CONTRACTS",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "EventContract",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "expected_role_event_waits",
    "expected_wait_hazard_states",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "router_loop_invariant",
]
