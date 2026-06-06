## ADDED Requirements

### Requirement: PM Repair Packets Include Concrete Blocker Context

FlowPilot PM repair-decision packets SHALL include the blocker recommendation,
repair target, stale evidence ids, and current recheck role needed for PM to
choose an executable recovery path.

#### Scenario: Reviewer blocks a result with a recommendation

- **WHEN** a reviewer, FlowGuard operator, system validation gate, or task
  result creates a semantic blocker with `recommended_resolution`
- **THEN** the PM repair-decision packet includes that recommendation
- **AND** it includes the blocked packet id, repair target packet id, stale
  evidence ids, blocker class, gate kind, and required recheck role.

#### Scenario: PM sees previous repair attempt

- **WHEN** the blocker family has prior active or recent repair decisions in
  the current run
- **THEN** the PM repair-decision packet includes repeat-loop context and prior
  decision ids for PM review.

### Requirement: Repair Reissue Packets Name The Required Deliverable

FlowPilot repair reissue packets SHALL tell the responsible role what concrete
fresh output is required to clear the blocker.

#### Scenario: Sender reissue follows PM decision

- **WHEN** PM chooses sender reissue, same-node repair, or collect
  more evidence for a blocker
- **THEN** the repair packet includes the original packet output contract,
  target result id, required recheck role, and a repair completion contract.

#### Scenario: Repair summary alone is insufficient

- **WHEN** the responsible role receives a repair reissue packet
- **THEN** the packet states that a repair explanation or summary alone is not
  completion evidence
- **AND** the role must submit a fresh current-packet result that satisfies the
  original output contract or explicitly returns a new blocker.

### Requirement: Repeat Blockers Escalate As Context, Not Silent Loops

FlowPilot SHALL surface repeated same-family blockers as explicit PM context
rather than silently reissuing the same vague repair packet.

#### Scenario: Same blocker family repeats

- **WHEN** the same repair target and blocker class appear more than once in
  the current run
- **THEN** PM and repair reissue packets include the repeat count and previous
  blocker ids
- **AND** FlowPilot does not treat the repeat count alone as a passed gate or a
  terminal stop.
