## ADDED Requirements

### Requirement: Current handoff contracts include branch-specific output shapes
FlowPilot SHALL make every current packet family executable from the opened
packet by exposing required top-level fields, forbidden fields, conditional
child fields, and branch-specific minimal valid shapes in the current handoff
contract.

#### Scenario: Conditional branch shape is visible before submission
- **WHEN** a packet family allows a branch such as `decision=redesign_route`
- **THEN** the opened packet handoff contract MUST include the branch's required
  child fields and the strict minimal shape required by runtime validation

#### Scenario: Hidden branch requirement is rejected by model evidence
- **WHEN** runtime validation requires a nested field that is not represented in
  the handoff contract branch shape
- **THEN** FlowGuard information-flow alignment MUST report a gap before live
  or fake-AI evidence can be claimed complete

### Requirement: Mechanical reissue packets provide executable branch correction
FlowPilot SHALL make mechanical reissue packets identify the failing branch,
failed field path, concrete validation reason, and the same branch-specific
minimal valid shape needed for the responsible role to resubmit.

#### Scenario: Route redesign result is missing strict route-plan fields
- **WHEN** a `pm_repair_decision` result chooses `redesign_route` but omits the
  strict route-plan schema version, node list, node id, or title
- **THEN** runtime MUST reject the result and issue a fresh current packet whose
  correction metadata includes the failed route-plan path and a legal
  `redesign_route` shape

#### Scenario: Generic shape alone is insufficient for conditional failure
- **WHEN** a mechanical failure occurs inside a conditional child branch
- **THEN** the reissue packet MUST NOT rely only on the packet family's generic
  minimal valid shape

### Requirement: Normal role dispatch has one visible current-runtime path
FlowPilot SHALL expose one normal current-runtime action for assigning the
requested packet responsibility and opening the role handoff while preserving
runtime-owned checks for responsibility, current packet binding, role reuse,
replacement, liveness failure, and self-review prevention.

#### Scenario: Reusable current role is dispatched without two visible steps
- **WHEN** the next open packet has a reusable role slot for the requested
  responsibility
- **THEN** the foreground duty MUST expose one role-dispatch action and runtime
  MUST record assignment and lease evidence for the current packet

#### Scenario: Dead or forbidden role does not create a fallback path
- **WHEN** the current role is non-reusable, dead, wrong-responsibility, or
  forbidden from reviewing its own result
- **THEN** runtime MUST block or request a replacement through the same current
  dispatch action instead of using chat memory, old role ids, or a second public
  workflow

### Requirement: Staged PM gate projection names the active gate instead of historical errors
FlowPilot SHALL project staged PM decision gates as current gate work while
their FlowGuard, review, system-validation, or closure stage is pending.

#### Scenario: Accepted source packet remains valid staged-effect source
- **WHEN** a PM repair decision packet is accepted and a staged PM gate is
  awaiting FlowGuard or later validation
- **THEN** final return preflight MUST NOT report that accepted source packet as
  a current-target violation solely because it is accepted

#### Scenario: Real stale target still fails
- **WHEN** no pending staged gate justifies an accepted or noncurrent packet as
  a current target
- **THEN** final return preflight MUST continue to report the stale current
  target violation

### Requirement: Fake-AI rehearsal covers branch contracts and role dispatch
FlowPilot fake-AI rehearsal SHALL include contract-blind branch success,
branch-shape failure, corrected reissue, single visible role dispatch, and
staged-gate projection scenarios before broad current-runtime confidence is
claimed.

#### Scenario: Fake AI cannot pass by hidden branch knowledge
- **WHEN** a fake-AI success result includes branch fields not declared by the
  packet contract
- **THEN** the fake-AI parity check MUST fail or classify the row as a negative
  overproduction scenario

#### Scenario: Historical live branch-shape failure is replayed
- **WHEN** the observed PM `redesign_route` failure sequence is replayed
- **THEN** the rehearsal MUST show the first invalid branch shape is rejected,
  the corrected branch shape is accepted, and the route proceeds through the
  single current runtime path

### Requirement: Contract-sensitive changes refresh install, topology, and FlowGuard evidence
FlowPilot SHALL treat changes to packet contracts, role dispatch, status
projection, prompts, and fake-AI rehearsal as invalidating affected model,
test, topology, and install evidence.

#### Scenario: Current information-flow change is completed
- **WHEN** this change updates contract, runtime, prompt, or test surfaces
- **THEN** affected FlowGuard checks, fake-AI rehearsals, targeted unit tests,
  topology build/check, install audit, local install sync, and Git version
  evidence MUST be refreshed before completion is claimed
