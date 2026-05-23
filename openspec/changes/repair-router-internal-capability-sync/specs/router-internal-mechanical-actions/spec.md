## ADDED Requirements

### Requirement: Router materializes ready internal postconditions before role waits
FlowPilot SHALL classify deterministic Router-owned postconditions separately
from role-provided external events and SHALL materialize them before exposing a
passive Controller or role wait.

#### Scenario: Capability evidence inputs are ready
- **WHEN** child-skill manifest review has passed
- **AND** PM has approved the child-skill manifest for route use
- **AND** the capability source artifacts are present and valid
- **AND** `capability_evidence_synced` is not yet recorded
- **THEN** Router MUST write Router-owned capability sync evidence
- **AND** Router MUST sync the matching event/flag
- **AND** Router MUST recompute the next action from the updated state
- **AND** Router MUST NOT create an `await_role_decision` row for
  `capability_evidence_synced`

#### Scenario: Capability evidence inputs are not ready
- **WHEN** the prerequisite flags imply a Router-owned internal postcondition
  is due
- **AND** the source artifacts required to materialize that postcondition are
  absent or invalid
- **THEN** Router MUST expose a local control-plane blocker or repair action
  that names the missing evidence
- **AND** Router MUST NOT represent the missing Router artifact as a Controller
  decision wait

### Requirement: Internal postcondition materialization is idempotent
FlowPilot SHALL make Router-owned internal postcondition materialization safe
across repeated daemon ticks, foreground re-entry, and manual event replay.

#### Scenario: Capability sync evidence already exists
- **WHEN** Router repeats reconciliation after capability sync evidence already
  exists
- **THEN** Router MUST preserve one authoritative sync artifact
- **AND** Router MUST keep the event/flag synced
- **AND** Router MUST NOT create duplicate wait rows or duplicate sync records
