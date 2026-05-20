## ADDED Requirements

### Requirement: Formal gate packages reuse existing acceptance sources
FlowPilot SHALL make PM-built formal gate packages point Reviewer to existing
packet and result artifacts that define the current gate standard instead of
creating a separate acceptance-criteria schema.

#### Scenario: Package includes source packet and contract references
- **WHEN** PM records an absorbed package-result disposition
- **AND** PM releases a formal gate package for Reviewer
- **THEN** each package result entry SHALL include the existing result envelope
  path and hash
- **AND** each package result entry SHALL include the existing source packet
  envelope path when known
- **AND** each package result entry SHALL expose the existing source output
  contract identifier when present in the result or packet envelope.

#### Scenario: Reviewer derives the gate standard from existing artifacts
- **WHEN** Reviewer reviews a PM formal gate package
- **THEN** Reviewer SHALL use the package `gate_kind` and
  `reviewer_review_scope` to identify the current gate
- **AND** Reviewer SHALL use the source packet acceptance slice, source
  `output_contract`, result `contract_self_check`, and node acceptance plan
  when applicable as the current pass/fail standard.

#### Scenario: Missing acceptance source blocks through existing review fields
- **WHEN** Reviewer cannot recover the current acceptance slice, source output
  contract, required result contract self-check, or required node acceptance
  plan from the formal package and cited artifacts
- **THEN** Reviewer SHALL return a normal blocked review report
- **AND** the report SHALL use existing `blockers` and
  `recommended_resolution` fields to tell PM what to repair, reissue, or
  collect.

#### Scenario: Higher-standard suggestions do not become blockers by default
- **WHEN** Reviewer finds a simpler equivalent path, higher-quality option, or
  future improvement that does not prove the current gate minimum standard is
  unmet
- **THEN** Reviewer SHALL record the item as PM decision support using existing
  `pm_suggestion_items`
- **AND** Reviewer SHALL NOT classify it as `current_gate_blocker` unless it
  exposes an unmet hard requirement, missing proof, semantic downgrade,
  unverifiable acceptance surface, role-boundary failure, or protocol
  violation.
