## ADDED Requirements

### Requirement: Systemic replay stories prove recovery loops

System-level synthetic agent replay packages SHALL exercise fake AI activity
through real FlowPilot runtime surfaces and prove the resulting recovery loop.

#### Scenario: Valid envelope contains bad content

- **GIVEN** a fake AI role writes through a valid role or packet envelope
- **AND** the payload lacks required deliverable evidence or contradicts the
  claimed completion
- **WHEN** the replay package executes
- **THEN** FlowPilot SHALL reject completion and route the run to a blocker,
  repair, or reviewer-controlled continuation path.

#### Scenario: Multiple blockers overlap

- **GIVEN** a fake run has more than one unresolved blocker or dirty ledger
- **WHEN** the replay package asks for the next legal action
- **THEN** the highest-priority active control-plane blocker SHALL preempt
  normal work
- **AND** lower-priority evidence SHALL remain unresolved rather than being
  silently cleared.

#### Scenario: PM repair attempt fails

- **GIVEN** PM selects a legal repair target
- **AND** the resulting fake repair still lacks valid deliverable evidence
- **WHEN** retry budget is exhausted
- **THEN** the workflow SHALL escalate or remain blocked instead of completing
  or looping forever.

#### Scenario: Restart replays stale state

- **GIVEN** stale saved state, old packet body, or old PM disposition exists
- **WHEN** the current run is reentered or resumed
- **THEN** stale evidence SHALL NOT satisfy the current obligation
- **AND** the current run SHALL expose a recovery action or blocker.

#### Scenario: Parallel write interference appears

- **GIVEN** a peer or stale writer records evidence for the same logical run
- **WHEN** the replay package reconciles current authority
- **THEN** foreign or stale evidence SHALL NOT overwrite current authority
- **AND** it SHALL NOT count as completion evidence.

#### Scenario: Terminal total gate rejects incomplete run

- **GIVEN** one or more dirty ledgers, unresolved material obligations, PM
  suggestions, self-interrogation items, or incomplete background artifacts
  remain
- **WHEN** final completion is requested
- **THEN** completion SHALL be rejected with a visible blocker or repair reason.
