## ADDED Requirements

### Requirement: Model-test alignment binds packet contracts to code and fake AI
FlowGuard boundary-test alignment SHALL compare packet-result contract rows with
runtime validators, fake AI scenario outputs, and negative tests before broad
FlowPilot e2e evidence is accepted as current-contract proof.

#### Scenario: Contract row lacks code or test evidence
- **WHEN** a packet-result contract family has no runtime validator binding,
  fake AI parity evidence, or negative test row
- **THEN** Model-Test Alignment MUST report a gap instead of treating broad e2e
  success as full coverage

#### Scenario: Fake AI emits undeclared successful field
- **WHEN** source alignment detects a successful fake AI body field that is not
  declared by the matching packet contract
- **THEN** Model-Test Alignment MUST fail or scope out that fake AI evidence
  until the packet contract, packet body, and runtime validator are reconciled
