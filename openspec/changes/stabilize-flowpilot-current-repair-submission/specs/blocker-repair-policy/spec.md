## ADDED Requirements

### Requirement: PM repair packets expose the authoritative current submission skeleton
FlowPilot SHALL expose the current packet's complete PM repair submission
skeleton as the authoritative role-facing example whenever a PM repair packet
declares required result fields, conditional branch fields, or repair evidence
obligations.

#### Scenario: Obligation-bearing PM repair packet shows complete skeleton
- **WHEN** Runtime creates a PM repair decision packet with
  `repair_evidence_obligations`
- **THEN** the packet body MUST include a `minimal_valid_shape` that contains
  `repair_obligation_disposition`
- **AND** the instruction text MUST direct PM to use that current
  `minimal_valid_shape` rather than a fixed `decision`/`reason` example.

#### Scenario: Reason-only example cannot override obligation skeleton
- **WHEN** a PM repair decision packet declares `repair_evidence_obligations`
- **THEN** FlowPilot MUST NOT present a fixed valid-looking example that
  contains only `decision` and `reason`
- **AND** Runtime MUST still reject a submitted result that omits
  `repair_obligation_disposition`.

### Requirement: PM repair prompt guidance prioritizes current packet checklist
FlowPilot SHALL instruct PM to treat the opened packet's required fields,
conditional fields, authorized input materials, and skeleton as the current
pre-submit checklist for the repair decision.

#### Scenario: PM repair card names mandatory obligation disposition
- **WHEN** PM receives a repair packet with `repair_evidence_obligations`
- **THEN** PM guidance MUST state that every obligation id requires one
  `repair_obligation_disposition` row before `submit-result`
- **AND** PM guidance MUST state that `reason`, `summary`, registry prose, and
  old result references do not satisfy those obligations.

