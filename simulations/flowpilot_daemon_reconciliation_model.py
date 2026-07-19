"""FlowGuard model for FlowPilot daemon durable reconciliation.

Risk intent brief:
- Review the second-layer Router/daemon failure class where durable evidence
  exists on disk but the daemon keeps returning stale work.
- Model-critical durable state: Controller action receipts, stateful
  Controller-action postconditions, Controller-boundary confirmation artifacts,
  Controller action rows, Router scheduler rows, packet ledgers, mail delivery
  flags, startup system-card bundle ACK returns, startup secondary-state role
  flags, role-output ledgers, canonical report artifacts, Router event flags,
  transient Controller action temp files, stale in-memory daemon snapshots, and
  the one-tick reconciliation barrier before next-action computation.
- Adversarial branches include a completed Controller action repeated forever,
  a done receipt that updates only the action ledger but not Router state,
  an incomplete stateful receipt treated as success, a submitted role output
  left only in the role-output ledger, a canonical report file not synced back
  into Router flags, a daemon save that overwrites newer role-output evidence,
  and next-action computation that reads old pending_action before durable
  reconciliation.
- Hard invariants: every active daemon tick must reconcile durable receipts and
  role outputs before returning work; completed or blocked Controller actions
  must be cleared, applied, or surfaced as a blocker; a completed mail-delivery
  receipt must either fold the packet ledger and Router flag together or remain
  an explicit control blocker; a submitted PM repair decision for that blocker
  must be consumed into a repair transaction or reissue before the daemon keeps
  waiting on the same role; a resolved PM system-card bundle ACK must close the
  matching wait row and immediately expose the real user-intake packet dispatch
  if that packet is still held by Controller; expected valid role outputs must
  become Router events exactly once; canonical artifacts and flags must not
  diverge; a valid Controller-boundary artifact plus reconciled
  receipt/action/scheduler rows must rebuild Router flags before any next
  action is exposed; startup-daemon bootloader rows must have one
  reconciliation owner, startup postcondition misses must stay on the
  mechanical reissue lane until that budget is exhausted, and any blocker for
  the same startup row must be resolved before PM repair work can be queued
  once the postcondition is satisfied; daemon startup role flags written into
  the secondary startup record must be folded into Router state atomically
  before next-action computation; Controller action directory scans must skip
  transient `.tmp-*.json` files and transient file disappearance must never
  stop the daemon; daemon
  queue budget exhaustion must immediately start the next tick instead of
  sleeping; foreground start commands that collide with a fresh runtime-state
  writer must allocate one current run before advancement, wait for settlement,
  preserve already completed action evidence, and return live daemon status
  instead of failing or allocating another run; startup Controller receipts
  must fold action, scheduler, pending,
  bootstrap, and run-state projections under one owner instead of depending on
  a later apply path; real waits must not busy-loop; and stale daemon snapshots
  must never erase newer durable evidence.
"""

from __future__ import annotations

from flowguard import Workflow

from flowpilot_daemon_reconciliation_model_hazards import hazard_states
from flowpilot_daemon_reconciliation_model_invariants import INVARIANTS, invariant_failures
from flowpilot_daemon_reconciliation_model_state import Action, State, Tick, Transition, initial_state
from flowpilot_daemon_reconciliation_model_transitions import DaemonReconciliationStep, next_safe_states


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 12


def build_workflow() -> Workflow:
    return Workflow((DaemonReconciliationStep(),), name="flowpilot_daemon_reconciliation")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.lifecycle == "terminal"


def is_success(state: State) -> bool:
    return state.lifecycle == "terminal"


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
