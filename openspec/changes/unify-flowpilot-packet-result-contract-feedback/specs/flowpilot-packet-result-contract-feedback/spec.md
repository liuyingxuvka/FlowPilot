## ADDED Requirements

### Requirement: High-standard contract freezes root user-intent closure
FlowPilot SHALL require the accepted high-standard contract to preserve hard
user intent, forbidden scope, completion meaning, evidence rules, and
report-only closure boundaries. A generic hard row that only says to complete
the user request SHALL NOT be sufficient when the PM has accepted a
high-standard flow.

#### Scenario: Forbidden scope is preserved through closure
- **WHEN** the user or PM high-standard contract forbids a class of output such
  as UI creation
- **THEN** route planning, node packets, final ledger, and final preflight MUST
  keep that forbidden scope visible and block closure if a matching forbidden
  artifact is present without explicit waiver

#### Scenario: Completion cannot close by report only
- **WHEN** a hard requirement is marked as needing artifact, validation, or
  freshness evidence
- **THEN** final closure MUST require direct evidence or an explicit waiver and
  MUST NOT treat a completion report alone as evidence

### Requirement: Route nodes project hard requirements into deliverable checks
FlowPilot SHALL require current route nodes that declare hard requirement
coverage or required outputs to carry current proof obligations through node
acceptance plans, node context packages, and route deliverable checks.

#### Scenario: Node accepted without proof is not requirement coverage
- **WHEN** a hard high-standard requirement is only cited by an accepted node
  but the node has no passing deliverable check, validation evidence, PM
  absorption, or explicit waiver for that requirement
- **THEN** the final requirement evidence matrix MUST mark that requirement
  unresolved

#### Scenario: Required output without deliverable check blocks terminal closure
- **WHEN** a route node declares required outputs but omits system
  deliverable checks
- **THEN** the final route-wide gate ledger MUST block closure with the current
  node id

### Requirement: Node context package carries the current work contract
FlowPilot SHALL treat `node_context_package` as the current work contract
projected from PM planning, not as optional narrative. The package MUST carry
inherited hard requirement ids, evidence targets, inspection targets,
FlowGuard targets, Reviewer starting points, low-quality-success risks,
semantic downgrade risks, work-packet projection, and test obligation matrix
visibility before Worker dispatch.

#### Scenario: Node package omits semantic risk projection
- **WHEN** a node acceptance plan result returns a package without
  low-quality-success risks, semantic downgrade risks, work-packet projection,
  or test obligation matrix rows
- **THEN** runtime MUST mechanically block the node acceptance plan result and
  reissue the current packet family

### Requirement: PM disposition absorbs role reports before node acceptance
FlowPilot SHALL require PM node disposition to absorb current Worker,
FlowGuard, and Reviewer evidence before accepting a node. The disposition MUST
name covered requirement ids, absorbed review findings, absorbed FlowGuard
boundaries, unresolved or waived risks, and semantic downgrade disposition.

#### Scenario: PM accepts without absorption
- **WHEN** a PM disposition body accepts a node but omits reviewer absorption,
  FlowGuard absorption, requirement coverage, residual risk disposition, or
  semantic downgrade disposition
- **THEN** runtime MUST block the PM disposition as an incomplete current
  contract result

### Requirement: Existing deliverable checks support semantic closure
FlowPilot SHALL extend the existing route `deliverable_checks` surface to cover
current semantic evidence without adding a second final-checker path. Supported
checks MUST include JSON field existence/equality, text containment/forbidden
text, forbidden path/glob absence, and freshness after a referenced event when
declared by a route node.

#### Scenario: Stale final report is blocked
- **WHEN** a final report deliverable is older than a required final-preflight
  or validation event
- **THEN** the route deliverable check MUST fail and terminal closure MUST
  remain blocked

#### Scenario: Forbidden output is blocked
- **WHEN** a route deliverable check declares a forbidden path or glob and a
  matching artifact exists
- **THEN** the check MUST fail and final closure MUST remain blocked

### Requirement: Role report packet families require current rich report fields
FlowPilot SHALL require Reviewer and FlowGuard operator packet results to carry
the current report body fields already defined by the role contracts and role
cards. A generic minimal `decision` and `pm_visible_summary` body SHALL NOT be
accepted as a successful current Reviewer or FlowGuard packet result.

#### Scenario: Reviewer minimal result is mechanically blocked
- **WHEN** a Reviewer packet result contains only generic navigation fields
- **THEN** runtime MUST block it with the current packet-result family id and
  the missing `independent_challenge` field paths

#### Scenario: FlowGuard operator minimal result is mechanically blocked
- **WHEN** a FlowGuard operator packet result omits model boundary, skipped
  checks, missing test kinds, confidence boundary, or contract self-check
- **THEN** runtime MUST block it with the current packet-result family id and
  missing field paths

### Requirement: Runtime remains a mechanical validator
FlowPilot runtime SHALL validate field presence, explicit arrays, forbidden old
fields, current packet identity, path/hash authority, and role-authored
`pm_visible_summary`. Runtime SHALL NOT judge Reviewer quality or FlowGuard
model sufficiency.

#### Scenario: Rich report body passes mechanical validation
- **WHEN** a Reviewer or FlowGuard operator submits all required current field
  paths with explicit arrays
- **THEN** runtime MAY accept the result mechanically and route it to the
  existing downstream consumer without adding any compatibility path

### Requirement: Fake AI rehearsals use declared current report contracts
FlowPilot fake AI success bodies SHALL emit the current declared fields for
Reviewer and FlowGuard packet families. Negative rehearsals SHALL prove that a
generic minimal result is not passing evidence.

#### Scenario: Fake AI cannot hide report-contract bypass
- **WHEN** fake AI rehearses Reviewer or FlowGuard success
- **THEN** the success body MUST include the declared rich report fields and
  fake AI parity checks MUST fail if those fields are absent

### Requirement: Field modeling covers role report body fields
FlowPilot FieldContract and source-alignment evidence SHALL account for
behavior-bearing role report body fields that are consumed by current packet
result families, including Reviewer independent challenge fields and
FlowGuard operator model/test boundary fields.

#### Scenario: Field model catches packet-result/report drift
- **WHEN** packet-result rows, role report contracts, fake AI bodies, or tests
  disagree about required Reviewer or FlowGuard fields
- **THEN** the FlowGuard field/model alignment check MUST fail before broad
  confidence is claimed

### Requirement: Terminal closure requires backward replay from delivered output
FlowPilot SHALL require final backward replay before high-standard completion
can be claimed. The replay MUST start from delivered output and current
evidence, challenge final-user intent, forbidden scope, semantic downgrade,
low-quality-success risks, stale reports, and missing proof.

#### Scenario: Ledger is clean but backward replay is missing
- **WHEN** final route-wide ledger and requirement evidence matrix are clean
  but high-standard completion lacks accepted terminal backward replay
- **THEN** final preflight MUST block completion rather than allowing a
  report-only or ledger-only stop
