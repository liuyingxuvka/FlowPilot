## ADDED Requirements

### Requirement: Explicit Active-Set Authority

FlowPilot SHALL allow multiple Flow blocks or runs to be active in parallel
only when the user-visible status projection exposes an explicit active-set
authority that identifies each live block/run and its operation target.

#### Scenario: Independent Flow blocks are active in parallel

- **GIVEN** Flow block A and Flow block B are both running
- **AND** A is the current UI focus/default target
- **WHEN** FlowPilot writes the active UI task catalog or route-state snapshot
- **THEN** both A and B appear in the active set with stable target ids
- **AND** B is marked as background-active rather than stale
- **AND** the projection states that no global main line is required.

#### Scenario: Multiple live agents belong to one Flow block

- **GIVEN** Flow block A has Worker, Reviewer, and FlowGuard officer work in
  progress
- **WHEN** FlowPilot writes active-set status
- **THEN** those agents are represented as block-scoped activity under A
- **AND** their results target A's merge or review boundary, not an unrelated
  Flow block.

### Requirement: Current Pointer Remains UI Focus Only

FlowPilot SHALL treat `.flowpilot/current.json` as a UI focus/default-target
pointer and SHALL NOT treat it as daemon authority, a global main route, or a
reason to hide other legal active blocks.

#### Scenario: Focus changes while another run remains active

- **GIVEN** run A and run B are both running
- **AND** `.flowpilot/current.json` points to run A
- **WHEN** the active-set projection is rebuilt
- **THEN** A is marked as the focus/default target
- **AND** B remains visible as a targetable background active run
- **AND** no operation is implied for B unless explicitly targeted.

### Requirement: Targeted Operations

FlowPilot SHALL require continue, stop, inspect, resume, merge, and apply-to-all
operations to declare a target scope before they can mutate or advance active
Flow state.

#### Scenario: Stop one block without stopping the others

- **GIVEN** Flow blocks A and B are active
- **WHEN** the operator stops A by target id
- **THEN** A is stopped or quarantined according to its lifecycle state
- **AND** B remains active
- **AND** the operation record states that the target scope was `single`.

#### Scenario: Apply to all active blocks is explicit

- **GIVEN** Flow blocks A and B are active
- **WHEN** the operator requests an all-active operation
- **THEN** the operation record states `target_scope: all_active`
- **AND** the active-set catalog used to select A and B is recorded.

### Requirement: Stale Active Residue Is Not Live Work

FlowPilot SHALL classify old, terminal, abandoned, missing, or superseded
active-looking entries as stale residue/history instead of live active work.

#### Scenario: Historical run remains in the index

- **GIVEN** run A is terminal or stale
- **AND** run B is active
- **WHEN** active-set status is rebuilt
- **THEN** run A is excluded from live active tasks or listed under stale
  residue with a reason
- **AND** run B remains targetable live work.

#### Scenario: Missing active-set authority is rejected

- **GIVEN** multiple active entries are displayed
- **AND** the projection lacks explicit active-set authority or target ids
- **WHEN** FlowGuard audits the state
- **THEN** the audit reports a failure instead of treating the projection as a
  valid parallel Flow state.

### Requirement: Plain-Language Parallel Status

FlowPilot SHALL summarize parallel Flow status in user-facing language that
distinguishes focus, background active work, targeted operations, and stale
history without requiring users to understand internal ledgers.

#### Scenario: User sees parallel status

- **GIVEN** Flow blocks A and B are active
- **WHEN** Controller or UI status is shown to the user
- **THEN** the user can tell which block is focused by default
- **AND** which blocks are running in the background
- **AND** whether an action applies to one block or all active blocks.
