## ADDED Requirements

### Requirement: Hard-gate matrix covers terminal replay blocker miss
FlowPilot hard-gate coverage SHALL include executable evidence for the
terminal backward replay negative branch that previously passed through the
wrong control-plane lane.

#### Scenario: Valid terminal blocker is not a mechanical reissue loop
- **WHEN** a test submits a current terminal backward replay result with
  `passed=false`, failing segment context, blockers, direct evidence, PM repair
  decision, and repair restart policy
- **THEN** the test MUST prove the result is mechanically valid
- **AND** the test MUST prove runtime records a semantic terminal blocker
  instead of issuing a mechanical reissue packet.

#### Scenario: Model-test alignment names the negative branch
- **WHEN** FlowGuard model-test alignment audits terminal final-quality
  obligations
- **THEN** the terminal replay result contract MUST have ordinary test evidence
  for both the pass branch and the valid-block branch
- **AND** scoped confidence MUST NOT rely only on the happy terminal replay
  path.
