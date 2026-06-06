"""Thin current-contract entrypoint for the FlowPilot persistent Router daemon model.

FlowGuard model for FlowPilot persistent Router daemon control.

Risk intent brief:
- Prevent FlowPilot from stalling when a role writes the expected ACK/report
  file after Controller has stopped at an ordinary wait boundary.
- Preserve the existing authority split: Router decides route state,
  Controller executes host actions from a durable checklist, and roles only
  write mailbox evidence.
- Model-critical durable state: daemon lock/status, one-second daemon tick,
  mailbox evidence, ACK consumption, Controller action ledger entries,
  external-event wait row closure, Controller receipts, stateful Controller
  postcondition evidence, Router scheduler ledger parseability, atomic durable
  ledger writes, daemon status/lock/process consistency, manual resume/patrol
  resume recovery, role cohort liveness, missing-deliverable repair
  issue/failure counts, and terminal cleanup.
- Adversarial branches include formal startup skipping or failing daemon
  launch before Controller core load, no daemon at a wait, duplicate Router
  writers, duplicate ACK observation, Router marking Controller work done
  without a receipt, Controller acting as the normal Router metronome,
  daemon-scheduled startup rows whose done receipts do not update bootstrap
  flags, clear bootstrap pending_action, reconcile the Router row, and schedule
  the next startup row,
  Controller stopping at ordinary waits, foreground Controller ending while a
  live daemon-owned role wait is active, foreground Controller ending while
  the daemon is live but no Controller action is ready, patrol starting a
  second live daemon, Router scheduler ledger corruption from partial writes,
  monitor current-work projection dropping active packet holders or internal
  reconciliation owners after `pending_action` is cleared,
  treating a fresh runtime write lock as corruption instead of a one-tick
  defer, daemon status claiming active after an error lock or missing process,
  and terminal stop leaving daemon/Controller/roles active.
- Hard invariants: formal startup must start a live one-second Router daemon
  before Controller core loads; active ordinary waits have a live daemon; one
  daemon writer owns a run; mailbox evidence is consumed at most once;
  recorded external events close every matching durable wait row before Router
  opens the next wait;
  Controller-required work is done only with a Controller receipt; stateful
  Controller receipts such as startup boundary confirmation must either have
  Router-visible postcondition evidence before Router marks the action done, or
  remain incomplete with a bounded Controller deliverable repair row;
  Router may count a repair attempt as failed only after the matching
  Controller repair receipt is received and invalid, and must not write a
  budget-exhausted blocker while a repair action is still pending;
  receipt reconciliation must also advance the matching Router-owned internal
  fact, and daemon-scheduled startup receipts must advance the bootstrap flag,
  clear bootstrap pending_action, and reconcile the Router scheduler row, so the
  same Controller action is not reissued forever; Controller
  follows the daemon-owned ledger instead of manually ticking the Router during
  normal runtime; Controller stays attached to the ledger during all
  nonterminal daemon-live runtime, processes pending executable Controller
  actions, and keeps a foreground standby loop active during ordinary
  daemon-owned role waits; monitor current-work projection names active packet
  holders, passive reconciliation owners, and internal Router/Controller work
  even when the unsupported_historical wait target is null; Router/Controller durable ledgers stay valid JSON
  after every write, fresh in-progress write locks defer daemon progress
  instead of surfacing as corruption, nested status/state writes during that
  wait do not terminate the daemon, runtime write-lock failures remain
  mechanical before PM semantic repair, self-owned stale write locks are
  cleared only after safe artifact checks and diagnostic evidence, durable
  ledgers are written atomically, and daemon active status never contradicts an
  error lock or missing process;
  patrol restarts only dead/stale daemon state; and terminal stop disables
  daemon, Controller, patrol, roles, and route work.
"""

from __future__ import annotations

from flowguard import Workflow

from flowpilot_persistent_router_daemon_model_hazards import hazard_states
from flowpilot_persistent_router_daemon_model_invariants import INVARIANTS, invariant_failures
from flowpilot_persistent_router_daemon_model_state import Action, State, Tick, Transition, initial_state
from flowpilot_persistent_router_daemon_model_transitions import PersistentRouterDaemonStep, next_safe_states


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 16


def build_workflow() -> Workflow:
    return Workflow((PersistentRouterDaemonStep(),), name="flowpilot_persistent_router_daemon")


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

