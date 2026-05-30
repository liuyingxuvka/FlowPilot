# router-reconciliation-branch-pruning Specification

## Purpose
TBD - created by archiving change prune-router-reconciliation-branch-logic. Update Purpose after archive.
## Requirements
### Requirement: Router reconciliation branches are modeled before contraction

FlowPilot SHALL use a FlowGuard branch-pruning model before simplifying
behavior-bearing Router reconciliation branches.

#### Scenario: Branch model defines observable result cases

- **WHEN** a Router reconciliation branch-pruning change is prepared
- **THEN** the FlowGuard model defines the input state, observable output,
  observable state writes, and side effects for each target branch family
- **AND** each branch family maps to one of `noop`, `reconciled`,
  `superseded`, `replay_required`, `retry_pending`, `repair_pending`, or
  `blocked`.

#### Scenario: Unmodeled branch contraction is blocked

- **WHEN** a branch writes run state, controller action rows, controller
  receipts, history, external events, role-output ledgers, or control blockers
- **THEN** the branch MUST NOT be collapsed until its result case and
  observable effects are represented in the branch-pruning model.

### Requirement: Branch contraction is evidence backed

FlowPilot SHALL require equivalence, replay, or model-test alignment evidence
before replacing repeated branch-local logic with shared handlers.

#### Scenario: State-writing branch requires replay evidence

- **WHEN** a proposed contraction changes how a state-writing branch reaches
  `reconciled`, `superseded`, `retry_pending`, `repair_pending`, or `blocked`
- **THEN** conformance replay or focused runtime tests prove that old and new
  paths produce the same observable state and side effects.

#### Scenario: Property-only evidence is insufficient for deletion

- **WHEN** FlowGuard evidence only proves selected properties rather than full
  observable behavior
- **THEN** the affected branch may be documented or isolated
- **AND** the branch MUST NOT be deleted or merged into a shared effect handler
  without stronger evidence.

### Requirement: Role-output event pruning preserves Router authority

FlowPilot SHALL keep dynamic Router event authority explicit when simplifying
role-output reconciliation paths.

#### Scenario: Role output without authority is not consumed

- **WHEN** a role-output envelope names an external event but the active Router
  wait state or required authority does not allow that event
- **THEN** the simplified reconciliation path classifies the envelope as
  `unauthorized` or `not_ready`
- **AND** it does not record the event as reconciled.

#### Scenario: Shared role-output scaffolding keeps separate authority branch

- **WHEN** startup fact and direct role-output event reconciliation share
  ledger scanning, envelope validation, ACK preconsumption, or pending-blocker
  checks
- **THEN** the common path still branches on event authority before recording
  any external event or side effect.

### Requirement: Structure changes serve branch pruning

FlowPilot SHALL allow file splitting during this change only when it preserves
the reduced branch model and makes ownership clearer.

#### Scenario: File split follows reduced logic

- **WHEN** implementation splits a reconciliation owner module after branch
  pruning
- **THEN** the split separates classifier, effect application, unsupported historical
  facade, and genuinely domain-specific handlers
- **AND** it does not preserve the same large implicit logic tree across more
  files.

#### Scenario: Public unsupported historical remains stable

- **WHEN** branch-pruning implementation changes module structure
- **THEN** existing Router, receipt, role-output, and runtime-state import
  surfaces keep the current public contract until StructureMesh parity evidence
  proves a safe replacement boundary.
