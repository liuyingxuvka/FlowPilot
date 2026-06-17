# flowpilot-packet-review-flow Spec Delta

## ADDED Requirements

### Requirement: FlowGuard hard evidence must gate Reviewer release

FlowPilot SHALL reject a FlowGuard pass before Reviewer packet release when the packet-owned formal `flowguard_evidence.json` is missing, unreadable, or reports a non-pass hard decision for the current FlowGuard packet.

#### Scenario: Artifact says missing code contract while body claims pass

- **GIVEN** a FlowGuard packet requires formal run-local evidence
- **AND** its result body says `passed=true`
- **AND** the packet-owned `flowguard_evidence.json` reports `missing_code_contract`
- **WHEN** the result is submitted
- **THEN** FlowPilot rejects it as a mechanical contract block
- **AND** no Reviewer packet is released from that FlowGuard result

### Requirement: Reviewer manifests must expose only passable hard evidence

Reviewer packets SHALL include FlowGuard evidence manifest entries only from complete, current, pass FlowGuard work orders whose hard-evidence decision is pass-equivalent.

#### Scenario: Failed hard evidence is not exposed as pass evidence

- **GIVEN** a FlowGuard work order records `hard_evidence_decision=missing_code_contract`
- **WHEN** FlowPilot builds the Reviewer evidence reads
- **THEN** that work order is not exposed as matching pass evidence
