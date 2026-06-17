## MODIFIED Requirements

### Requirement: Formal gate packages reuse existing acceptance sources
FlowPilot SHALL make PM-built formal gate packages point Reviewer to existing
packet and result artifacts that define the current gate standard instead of
creating a separate acceptance-criteria schema. When the current run declares
an acceptance item registry, the package SHALL also carry applicable
`acceptance_item_ids` as trace keys into those existing acceptance sources.

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
  `output_contract`, result `Contract Self-Check`, and node acceptance plan
  when applicable as the current pass/fail standard
- **AND** when `acceptance_item_ids` are present, Reviewer SHALL check each
  applicable item against those same acceptance sources and direct evidence.

#### Scenario: Missing acceptance source blocks through existing review fields
- **WHEN** Reviewer cannot recover the current acceptance slice, source output
  contract, required result contract self-check, required node acceptance plan,
  or required active acceptance item projection from the formal package and
  cited artifacts
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
  unverifiable acceptance surface, role-boundary failure, protocol violation,
  or low-quality closure of an active acceptance item.
