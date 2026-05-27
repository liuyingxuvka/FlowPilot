# multiround-fake-ai-control-rehearsal Specification

## Purpose
TBD - created by archiving change harden-multiround-fake-ai-control-rehearsal. Update Purpose after archive.
## Requirements
### Requirement: Multi-round fake AI control rehearsals prove repair recovery
FlowPilot SHALL maintain prepared fake AI rehearsal rows that include at least
one sequence where a bad fake AI package is followed by a bad PM repair decision
and then by a corrected producer-backed repair decision.

#### Scenario: Bad repair does not advance route
- **WHEN** a prepared fake AI rehearsal submits a PM repair decision that waits for a role-produced event without producer evidence
- **THEN** Router MUST reject or preserve the repair as blocked without advancing to a dead follow-up wait
- **AND** the rehearsal MUST keep the original control blocker active or otherwise record a corrected-PM-decision requirement.

#### Scenario: Corrected repair restores legal continuation
- **WHEN** the same rehearsal then submits a corrected PM repair decision with current producer evidence
- **THEN** Router MUST move to the next legal wait or recovery state that names the producer evidence
- **AND** the rehearsal MUST record the evidence id as current and primary for the multi-round control-plane obligation.

### Requirement: Multi-round rehearsal gates reject stale evidence
FlowPilot SHALL include known-bad rehearsal rows proving that stale flags,
superseded packet results, or old event registrations cannot satisfy a fresh
repair wait.

#### Scenario: Old evidence cannot prove fresh repair
- **WHEN** a prepared fake AI rehearsal contains old result flags, old packet output, or old event registrations but no current producer for the repair target
- **THEN** the rehearsal matrix MUST reject the row as insufficient evidence
- **AND** the row MUST NOT count as fast-gate, model-test alignment, or real-Router rehearsal proof.

### Requirement: Rehearsal confidence boundary is explicit
FlowPilot SHALL describe multi-round fake AI rehearsal evidence as
control-plane confidence for prepared packages, not live AI semantic quality.

#### Scenario: Semantic quality is not overclaimed
- **WHEN** a multi-round fake AI rehearsal row is generated
- **THEN** the row MUST record `live_ai_semantic_quality_proven` as false
- **AND** the report confidence boundary MUST state that prepared fake AI packages do not prove every possible live AI semantic error impossible.
