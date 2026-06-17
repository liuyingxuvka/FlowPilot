## ADDED Requirements

### Requirement: Packet Review Carries Acceptance Item Trace Keys
FlowPilot packet and package review SHALL carry `acceptance_item_ids` when the
current run declares an acceptance item registry, while still using existing
packet, result, output-contract, node-plan, and formal-package artifacts as
the evidence sources.

#### Scenario: PM formal package omits applicable acceptance items
- **WHEN** PM releases a formal Reviewer package for a node, packet, or
  disposition that owns active acceptance items
- **AND** the package omits those item ids from the current gate context
- **THEN** Reviewer MUST block the package through the existing review report
  fields
- **AND** PM MUST repair, reissue, or reroute through the current packet path.
