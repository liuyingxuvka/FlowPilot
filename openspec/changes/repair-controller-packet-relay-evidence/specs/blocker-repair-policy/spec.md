## ADDED Requirements

### Requirement: PM escalation is reserved after relay mechanical repair boundary
FlowPilot SHALL escalate missing relay evidence to PM/control-blocker handling only when the missing evidence is not mechanically repairable by Controller or the Controller mechanical repair budget is exhausted.

#### Scenario: Invalid packet state escalates
- **WHEN** a relay receipt cannot be reconciled because the envelope is missing, corrupted, addressed to an invalid role, contaminated, or fails relay readiness checks
- **THEN** Router MAY materialize the appropriate control blocker or PM repair decision path instead of scheduling Controller mechanical relay repair

#### Scenario: Repeated Controller relay repair failure escalates
- **WHEN** Controller relay repair has been attempted up to the configured direct repair budget and the relay evidence is still missing or invalid
- **THEN** Router MUST escalate with a blocker payload that names the original action, packet ids, missing relay evidence, repair attempts used, and the exhausted budget
