## ADDED Requirements

### Requirement: Role submissions use current packet skeleton before submit
FlowPilot SHALL require role-facing guidance and focused tests to use the
current packet skeleton as the mechanical shape for formal packet results.

#### Scenario: Positive PM repair test uses current skeleton
- **WHEN** a focused PM repair flow test submits a valid PM repair result for a
  packet that declares `repair_evidence_obligations`
- **THEN** the test MUST submit a result that covers every obligation id in
  `repair_obligation_disposition`
- **AND** the test MUST NOT use a `decision`/`reason`-only result as a passing
  obligation-bearing repair case.

#### Scenario: Reason-only PM repair remains negative evidence
- **WHEN** PM submits only `decision` and `reason` for an obligation-bearing PM
  repair packet
- **THEN** Runtime MUST mechanically reject the result
- **AND** FlowPilot MUST keep or reissue the current PM repair packet path for a
  corrected result instead of applying the repair decision.

