## ADDED Requirements

### Requirement: Neutral relay names do not expand body access authority
FlowPilot SHALL allow recipient-neutral relay helper names while preserving the addressed-role body access rules. A renamed or aliased relay check MUST NOT let PM, Reviewer, Controller, Worker, or Officer open a body outside the role and stage authorized by the packet or result contract.

#### Scenario: PM opens only PM-bound result
- **WHEN** a result is relayed to `project_manager` for disposition
- **THEN** PM may open the result body only through the packet runtime authorization path for that result
- **AND** Reviewer SHALL NOT gain raw result body access from the PM-bound relay.

#### Scenario: Compatibility alias keeps old callers safe
- **WHEN** existing code calls a legacy reviewer-named relay check for a PM-bound result
- **THEN** the check SHALL apply the same recipient, ledger, hash, and body-boundary rules as the recipient-neutral check
- **AND** the legacy name SHALL NOT imply Reviewer approval or Reviewer body access.
