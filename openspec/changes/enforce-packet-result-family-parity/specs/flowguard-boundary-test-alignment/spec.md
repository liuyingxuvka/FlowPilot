## ADDED Requirements

### Requirement: Model-test alignment consumes packet-result family parity
FlowPilot model-test alignment SHALL include a FlowGuard obligation-family
parity decision for packet-result reconciliation before reporting this control
plane class as fully covered.

#### Scenario: All family members have current external evidence
- **WHEN** `material_scan`, `research`, `current_node`, and `pm_role_work` each have current model obligations, runtime regression evidence, partial-batch evidence, stale-reminder evidence, wrong-recipient evidence, and sealed-body provenance evidence
- **THEN** model-test alignment MAY report packet-result family parity as covered.

#### Scenario: Sibling family evidence is missing or stale
- **WHEN** any packet-result family member lacks current passing evidence for a required mechanism
- **THEN** model-test alignment MUST mark the packet-result family claim blocked or scoped
- **AND** broad full-coverage claims MUST NOT consume that family as passed.

### Requirement: Analogous defect scans derive sibling obligations
FlowGuard model-test alignment SHALL use the observed research durable-join
miss as a bad-case seed that derives sibling checks for material scan,
current-node, and PM role-work reconciliation.

#### Scenario: Research miss seed is reviewed
- **WHEN** the research durable-envelope miss is present in the family scan
- **THEN** FlowGuard SHALL derive analogous candidate checks for every sibling packet-result family
- **AND** any unreviewed sibling candidate blocks the family-level closure claim.
