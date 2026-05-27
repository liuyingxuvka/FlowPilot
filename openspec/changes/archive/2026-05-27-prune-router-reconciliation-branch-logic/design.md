## Context

FlowPilot's current maintenance map shows several Router runtime owners above
the StructureMesh line threshold, but the user goal is not line-count reduction
by itself. The goal is to reduce bug risk by making behavior-bearing decision
trees shorter, easier to inspect, and easier to validate.

The strongest branch-pruning candidates are not the pure data files. They are
reconciliation functions where many branches converge on the same observable
state updates:

- `flowpilot_router_controller_scheduler_receipts_scheduled.py`
  - `_reconcile_scheduled_controller_action_receipts`: 94 branch nodes across
    lines 148-480.
- `flowpilot_router_role_output_bridge.py`
  - `_try_reconcile_direct_role_output_event_ledger`: 20 branch nodes.
  - `_role_output_event_has_durable_authority`: 19 branch nodes.
  - `_try_reconcile_startup_fact_role_output_ledger`: 16 branch nodes.
- `flowpilot_router_runtime_state.py`
  - `_derive_resume_next_recipient_from_packet_ledger`: 28 branch nodes.
  - stale-save merge helpers are smaller but sensitive state owners.
- `flowpilot_router_controller_scheduler_receipts_packet_folds.py`
  - fold handlers contain repeated evidence/status/update patterns.

Existing FlowGuard StructureMesh and model-test alignment already cover the
Router split and must remain the parent evidence boundary. This change adds a
narrower child model for branch pruning before any implementation rewrite.

## Goals / Non-Goals

**Goals:**

- Model branch pruning as `Input x State -> Set(Output x State)` before
  changing runtime code.
- Collapse reconciliation logic into a small result-case vocabulary that
  preserves observable behavior.
- Identify which branches are equivalent, which require replay evidence, and
  which must remain separate.
- Make any later file split serve the simplified logic rather than replace it.
- Preserve public imports and runtime artifacts unless StructureMesh and
  model-test alignment prove the new boundary.

**Non-Goals:**

- This proposal step does not edit FlowPilot runtime code.
- Do not remove compatibility facades.
- Do not delete branches only because they look redundant.
- Do not merge role-output event paths unless Router event authority is still
  explicit and tested.
- Do not split `runtime_state` ownership until stale-save and resume behavior
  have dedicated replay evidence.

## Decisions

### Decision 1: Model result cases before code shape

The branch-pruning model will classify each reconciliation input into one of
these result cases:

| Result case | Meaning |
| --- | --- |
| `noop` | Input is out of scope, incomplete, already settled, or not ready. |
| `reconciled` | The observable action/receipt/event has been settled. |
| `superseded` | A current wait or packet path was replaced by newer state. |
| `replay_required` | Existing done/reconciled evidence requires state replay. |
| `retry_pending` | The correct outcome is not known yet and retry remains legal. |
| `repair_pending` | A repair was scheduled or is already pending. |
| `blocked` | Router must write a blocker or preserve an existing block. |

Alternative considered: split oversized files first. Rejected because file
splitting can make a complex decision tree harder to understand if the logical
result cases are still implicit.

### Decision 2: Prioritize Controller scheduled receipt reconciliation

The first implementation target after approval should be
`_reconcile_scheduled_controller_action_receipts`. It has the largest branch
count and repeats the same observable effects: write the action row, update the
scheduler row, resolve blockers, clear pending controller action, append
history, refresh derived views, and save run state.

Alternative considered: start with `runtime_state`. Rejected because
`runtime_state` owns core persistence and stale-write protection; it needs more
manual review before branch contraction.

### Decision 3: Role-output pruning requires authority evidence first

Role-output reconciliation has obvious shared scaffolding, but event authority
must remain a first-class model branch. A role output envelope is not enough to
prove that the Router is currently allowed to consume the event.

Alternative considered: merge startup fact and direct event scanning
immediately. Rejected because prior model-miss lessons show static output
checks can pass while dynamic Router event authority is absent.

### Decision 4: Structure splitting follows the reduced logic

After a branch model and replay evidence are green, code may be reorganized as:

- classifier: derives the result case and payload;
- effect applicator: performs common writes for the result case;
- compatibility facade: keeps existing imports stable;
- domain-specific handlers: only where behavior remains genuinely different.

Alternative considered: preserve all current branch-local writes. Rejected
because repeated write/update/clear/save logic is the maintenance risk this
change is meant to reduce.

### Decision 5: First implementation pass contracts effects, not files

The first Controller scheduled-receipt pass keeps
`flowpilot_router_controller_scheduler_receipts_scheduled.py` as the compatible
runtime owner and contracts only the repeated reconciliation effect sequence:
action-row write, scheduler-row update, pending-apply clearance, and blocker
resolution.

This is the smallest behavior-preserving structure change because the modeled
result cases do not all share the same state effects. Branches for replay,
retry, repair, blocked, and superseded outcomes remain explicit unless focused
runtime evidence proves they can share the same effect path. Role-output and
runtime-state pruning remain model/evidence candidates only in this change.

## Risks / Trade-offs

- Branch equivalence is overclaimed -> require conformance replay before
  collapsing state-writing branches.
- Role-output event authority is weakened -> model `unauthorized` and
  `not_ready` as explicit result cases and add direct source-level tests.
- Runtime-state ownership becomes duplicated -> treat runtime-state pruning as
  model-only until stale-save and resume replay evidence exists.
- File splitting becomes the primary goal again -> add acceptance criteria that
  no split counts unless the branch model has fewer decision cases or clearer
  result ownership.
- Background checks are mistaken for pass evidence -> require exit-bearing
  artifacts for any long regression claim.

## Migration Plan

1. Build the branch-pruning model and executable checks without changing
   runtime code.
2. Add model-test alignment contracts for the branch classifier and result-case
   application plan.
3. Add focused conformance fixtures that replay current representative branch
   paths.
4. Only after those checks pass, implement a small Controller scheduled receipt
   contraction.
5. Re-run FlowGuard StructureMesh, model-test alignment, focused runtime tests,
   background Router/Meta/Capability checks, and install sync before any done
   claim.

## Open Questions

- Should the first implementation pass stop after Controller scheduled receipt
  reconciliation, or also include receipt fold common-effect cleanup?
- Should role-output reconciliation receive a separate OpenSpec change because
  it touches dynamic event authority?
- Should runtime-state branch tables be model-only until after the Controller
  receipt contraction lands?
