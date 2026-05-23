"""FlowGuard model for FlowPilot control-plane friction fixes.

Risk intent brief:
- Prevent prompt-isolation shortcuts from becoming handoff dead ends.
- Preserve Controller's envelope-only boundary while reducing purely
  mechanical handoff steps.
- Model-critical durable state: research package fields, worker packet
  materialization, material-scan dispatch integrity, packet/result open
  receipts, control-blocker routing, stop lifecycle reconciliation,
  active-task authority, display snapshot freshness, required phase-source
  context, and live-run artifact registration.
- Adversarial branches include dropped research scope fields, reviewer reports
  accepted without a result-body receipt, missing-receipt blockers escalated to
  PM instead of same-role reissue, material-scan packet dispatch with phase,
  contract, write-target, or canonical-body drift, PM repair reissue specs that
  never enter the packet runtime, success-only repair gates that cannot accept
  reviewer recheck blockers, stopped runs with live heartbeat/crew/packet
  state, stale snapshots treated as active UI state, ambiguous multi-active
  runs under current-json-only authority, product architecture delivery without
  PM material-understanding source paths, protocol blockers written outside
  router-visible state, stage-advance views left stale, stale role-decision
  waits that expose external events before their requires_flag is true, and
  optimized transactions that skip hash, role, or Controller-boundary checks.
  Status summaries, ack auto-consumption, stale wait reconciliation, role-work
  recipient normalization, model-miss report completeness, and role-memory
  deltas are included because these are the planned speed improvements.
  Long-running role-work waits are included: Controller can see only a
  metadata-only controller_status_packet progress surface, never sealed packet
  or result bodies. Reviewer-block repair routing is included: PM can repair
  node-local defects by revising or reissuing fresh same-node artifacts, while
  route mutation is reserved for defects the current node cannot semantically
  contain.
- Hard invariants: package-to-packet fields are preserved; material-scan
  dispatch requires phase, contract, write-target, and canonical-body
  consistency; repair reissues must materialize into packet files, ledger, and
  dispatch index; reviewer recheck failures must remain routable; reviewer
  decisions require legal open receipts; missing receipt repair is same-role
  reissue; stopped runs reconcile all visible lifecycle authorities; active
  snapshots are fresh; phase cards carry required source context; protocol
  blockers are router-visible; stage-advance views refresh; multi-active
  visibility has explicit authority; await_role_decision exposes only currently
  receivable external events; optimized transactions keep hash, role, and
  envelope-only guarantees; long-running waits expose exactly one status
  packet, progress is runtime-written numeric metadata, and status messages do
  not carry findings, evidence, recommendations, or body summaries; node-local
  reviewer blocks remain routable without a route mutation, use fresh repair
  evidence, and require the same review class to recheck before continuation;
  route mutations record why the current node cannot contain the repair and
  reopen route checks; optimized ack consumption validates exact ack, role, and
  hash; a valid direct ACK file that already exists is consumed before a later
  role event is blocked as an unresolved card return; pending waits reconcile
  only from durable packet/status evidence;
  user-facing status summaries remain metadata-only and blocker-consistent;
  PM role-work and current-node worker results return to PM before formal
  reviewer gates; role memory is an index, never an approval authority; and a
  complete model-miss officer report can reach a PM decision without a second
  officer loop; child-skill gate reviewer passes clear only the matching
  current gate blocker; direct Router ACK consumption preserves the semantic
  reviewer pass/block wait; PM repair authority cannot impersonate reviewer
  event authority; no-legal-next blockers wait for currently receivable role
  output; duplicate PM repair decisions are idempotent for the same blocker;
  Controller user reports do not expose internal action, packet, ledger, hash,
  contract, or diagnostic-path metadata by default; Router actions carry a
  Controller-facing plain-language reminder that is not itself user-visible;
  compact progress summaries include bounded route-level progress facts;
  display/status Controller work remains nonblocking; external keepalive work
  still requires lightweight confirmation; Controller delivery receipts only
  close Controller-owned delivery work and must become target-role waits rather
  than role completion; stateful Controller receipts cannot clear or advance a
  hard pending action until the Router can verify or reclaim the declared
  postcondition evidence; daemon ticks cannot escalate a half-complete
  Controller receipt when valid Router-owned artifacts already exist; and
  role-output events cannot be accepted from a prepared/progress status surface
  without a file-backed body path plus replayable body hash; PM role-work
  obligations are keyed by batch/request/packet/role, host delivery success and
  active-holder liveness are separate gates, packet-ledger IO is atomic and
  corruption-recoverable, result self-checks are machine-parseable, runtime
  authority backs every advertised reader; Router-owned internal postconditions
  with ready inputs materialize evidence or emit a router-visible blocker
  instead of becoming passive Controller/role waits; resolved obligations clear
  passive wait and reminder projections; and stale
  daemon/run-state saves cannot resurrect a live wait after the authoritative
  Router obligation state has cleared it.
- Blindspot: this is still a focused control-plane model. The live-run audit
  checks file-level consistency, but it does not prove product content quality.
"""

from __future__ import annotations

from flowguard import Workflow

from flowpilot_control_plane_friction_model_audit import audit_live_run
from flowpilot_control_plane_friction_model_hazards import hazard_states
from flowpilot_control_plane_friction_model_invariants import INVARIANTS, invariant_failures
from flowpilot_control_plane_friction_model_state import (
    PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES,
    Action,
    State,
    Tick,
    Transition,
    initial_state,
)
from flowpilot_control_plane_friction_model_transitions import (
    ControlPlaneStep,
    next_safe_states,
)


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneStep(),), name="flowpilot_control_plane_friction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 56


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "audit_live_run",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
