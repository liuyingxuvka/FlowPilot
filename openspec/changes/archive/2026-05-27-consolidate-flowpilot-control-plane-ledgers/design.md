## Context

The current control plane has correct pieces but too many runtime records can
still behave like authorities for the same fact. A Controller receipt can update
an action record and scheduler row while the Router daemon is also folding
scheduler state. Legacy `pending_action` can still expose an executable shape
that disagrees with the Controller action ledger. Batch waits can be rendered
from a single inferred event role even when packet members show several holders.

The hard constraints remain unchanged: Controller must stay attached in the
foreground while FlowPilot is active, workers and reviewers must only receive
their authorized envelopes/bodies, and signed packet artifacts are immutable.

## Goals / Non-Goals

**Goals:**
- Make the daemon the single owner of scheduler ledger folding during daemon
  mode.
- Let foreground Controller paths append receipts without directly owning
  scheduler state transitions.
- Keep compatibility for existing controller action records and old
  `pending_action` consumers while preventing conflicting decisions.
- Make batch waits and current-work summaries name all missing roles from member
  state.
- Turn transient Windows ledger contention into retry/defer behavior, not daemon
  death.
- Add FlowGuard and unit coverage for the known recurrence class.

**Non-Goals:**
- Removing the Controller action ledger or packet runtime.
- Changing role visibility, sealed-body rules, or signed artifact rules.
- Changing the formal startup contract or public FlowPilot invocation protocol.
- Performing a broad router facade refactor unrelated to the control-plane
  ownership issue.

## Decisions

1. **Daemon-owned scheduler folding**

   Receipt writers may create or update receipt files and action-local receipt
   metadata, but scheduler rows are reconciled by a Router-owned fold function.
   In daemon mode, foreground reconciliation can request the fold or return a
   deferred result; it does not race the daemon by independently rewriting the
   scheduler ledger.

   Alternative considered: keep both writers and broaden retry wrappers. That
   would reduce crashes but preserve the root race and leave two paths deciding
   scheduler truth.

2. **Receipt append first, state fold second**

   Controller completion remains receipt-driven. The receipt is the durable
   external fact; scheduler status and display summaries are projections folded
   from it. This keeps Controller simple and preserves the existing envelope-only
   boundary.

   Alternative considered: make Controller update every affected table. That
   repeats the current drift pattern and makes recovery harder.

3. **Compatibility projection for legacy `pending_action`**

   `pending_action` remains readable for older helpers and status displays, but
   when a matching Controller action exists, the Controller action ledger row is
   the authority for whether action execution, receipt, or router-controlled
   waiting is required.

   Alternative considered: remove `pending_action` immediately. That would be
   cleaner but too broad for the current repair because many tests and helper
   modules still read it.

4. **Batch wait role derivation from packet/member state**

   Generic worker events no longer imply `worker_a` as the sole owner when batch
   metadata names several holders. Current-work and reminder projections derive
   missing roles from refreshed packet/batch member state first, then fall back
   to event-role inference only when no batch detail exists.

   Alternative considered: add more special cases to event-name inference. That
   still guesses from names instead of using the actual batch state.

5. **Transient ledger access is not a daemon-fatal failure**

   Atomic write verification and read-back errors caused by Windows file
   contention are normalized to the same deferrable write-in-progress class used
   for replace-time contention. The daemon reports a defer tick and remains the
   active writer unless evidence shows real corruption without a fresh lock.

   Alternative considered: catch raw `PermissionError` only in the daemon loop.
   That would protect one call site but leave other runtime readers/writers with
   inconsistent semantics.

## Risks / Trade-offs

- [Risk] Some foreground tests currently expect immediate scheduler row mutation
  after `record_controller_action_receipt`. -> Mitigation: preserve immediate
  action-local receipt metadata and expose a fold helper for tests; update tests
  to assert daemon/fold-owned scheduler reconciliation.
- [Risk] Legacy helpers still read `pending_action`. -> Mitigation: keep
  compatibility fields but compute execution authority from the Controller
  action ledger when possible.
- [Risk] Deferring on `PermissionError` could mask real corruption. ->
  Mitigation: only treat access failures as transient when the file is daemon
  critical and the write-lock/fresh-access context says another writer may still
  be active; stale or malformed ledgers without fresh lock remain repair-needed.
- [Risk] Parallel AI work may touch receipt modules. -> Mitigation: keep edits
  narrow, inspect existing diffs before patching, and avoid repo-wide formatters.

## Migration Plan

1. Add a focused FlowGuard control-plane consolidation model that captures the
   known bad cases: multi-writer scheduler mutation, read-back
   `PermissionError`, contradictory `pending_action`, stale passive waits, and
   batch wait role collapse.
2. Update runtime helpers so daemon-owned folding is the canonical path and
   transient ledger contention defers rather than kills the daemon.
3. Update batch/current-work projections to prefer member state over event-name
   guesses.
4. Add or adjust focused router runtime tests for the new ownership and
   projection rules.
5. Run focused FlowGuard checks and router tests, then run heavyweight project
   regressions in the background with the repository log contract.
6. Sync the local installed FlowPilot skill and audit install freshness.

Rollback is ordinary git rollback of this change set. Runtime data migration is
not required; stale rows are reconciled by the new fold behavior when read.

## Open Questions

- Whether to fully remove legacy `pending_action` in a later major cleanup. This
  change keeps it as a compatibility projection.
