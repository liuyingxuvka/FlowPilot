## ADDED Requirements

### Requirement: Parent backward replay distinguishes inherited history from current repair child results
FlowPilot SHALL require replacement parent/module repair replay to combine
inherited accepted context with current repair child results, without allowing
inherited history alone to close the parent.

#### Scenario: Replacement parent replay has current repair child evidence
- **WHEN** all active repair children under a replacement parent repair node have returned accepted results
- **THEN** parent backward replay MAY consume those current repair child results together with inherited accepted context evidence
- **AND** the replay MUST identify which evidence is current repair output and which evidence is inherited history.

#### Scenario: Inherited history alone cannot close replacement parent
- **WHEN** a replacement parent repair node has inherited accepted result refs but no accepted result from an active repair child
- **THEN** parent backward replay MUST block
- **AND** FlowPilot MUST NOT mark the replacement parent complete from inherited history alone.

#### Scenario: Empty parent replay is a control-plane blocker
- **WHEN** parent backward replay is requested for a replacement parent/module repair node whose active `child_node_ids` are empty
- **THEN** Runtime MUST materialize or preserve a control-plane blocker for the malformed replacement node
- **AND** Runtime MUST NOT open another ordinary same-shape parent repair node before the malformed route shape is repaired or break-glass is evaluated.
