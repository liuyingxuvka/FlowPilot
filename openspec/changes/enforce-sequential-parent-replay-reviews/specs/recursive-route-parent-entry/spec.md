## ADDED Requirements

### Requirement: Parent entry consumes reviewed child replay evidence
FlowPilot route traversal SHALL NOT issue or consume parent/top-level backward
replay while any effective child/module node requiring parent replay lacks an
accepted independent review of its parent replay result.

#### Scenario: Parent waits for child replay review
- **WHEN** all direct child work results are accepted
- **AND** a child/module parent replay result exists without an accepted
  independent review
- **THEN** FlowPilot SHALL keep traversal on the child/module replay review
  obligation
- **AND** FlowPilot SHALL NOT advance to parent/top-level replay

#### Scenario: Parent replay begins after child review closure
- **WHEN** every effective child/module replay result that the parent depends on
  has an accepted independent review
- **AND** the parent node itself requires backward replay
- **THEN** FlowPilot MAY issue the parent backward replay packet for the parent
  scope
