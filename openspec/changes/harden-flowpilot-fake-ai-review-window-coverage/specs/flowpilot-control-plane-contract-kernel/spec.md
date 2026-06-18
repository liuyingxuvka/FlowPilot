## ADDED Requirements

### Requirement: AI-facing contracts surface runtime-enforced obligations
FlowPilot SHALL ensure every runtime-enforced result obligation that a role can
satisfy is projected into the current AI-facing packet contract before the
role's first response.

#### Scenario: Planning owner coverage is first-packet visible
- **WHEN** high-standard planning requires active acceptance items to be owned by route nodes
- **THEN** the planning packet contract MUST expose the required active acceptance item ids
- **AND** it MUST expose the required `nodes[].acceptance_item_ids` coverage path and a legal minimal shape.

#### Scenario: Node acceptance projection is first-packet visible
- **WHEN** node acceptance planning requires `acceptance_item_projection` rows
- **THEN** the node-acceptance packet contract MUST expose the node-owned acceptance item ids
- **AND** it MUST expose row object paths and required row fields before PM submits a pass result.

#### Scenario: Finite options include all legal choices
- **WHEN** a result field is constrained to finite values
- **THEN** the packet contract MUST expose all legal values in `allowed_value_options`
- **AND** runtime rejection for a wrong value MUST repeat the same legal options.

### Requirement: Contract reissues include executable repair guidance
Runtime contract rejection SHALL return enough structured repair guidance for
the contract-driven fake AI responder to generate a corrected result.

#### Scenario: Reissue names bad field and repair shape
- **WHEN** runtime rejects a result for malformed format, missing field, wrong type, wrong option, forbidden alias, missing projection, or owner coverage gap
- **THEN** the reissue payload MUST name the failed field or material family
- **AND** it MUST include the current minimal valid shape, branch shape, finite options, or active ids needed to repair the result.
