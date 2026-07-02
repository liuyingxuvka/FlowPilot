## MODIFIED Requirements

### Requirement: Route-node repair replacement resolves active child lineage
FlowPilot SHALL resolve every copied child route-node reference to its current
active replacement before writing a repair replacement node or issuing parent
backward replay.

#### Scenario: Copied parent children resolve to active replacements
- **GIVEN** a parent node lists a child id that has been superseded by a repair replacement
- **WHEN** Runtime creates a `repair_current_scope` replacement for the parent
- **THEN** the replacement parent's `child_node_ids` MUST contain the active replacement child id
- **AND** the old child id MUST appear only as lineage context.

#### Scenario: Unresolved lineage blocks instead of falling back
- **GIVEN** a copied child id points to a missing, cyclic, or still-superseded replacement chain
- **WHEN** Runtime tries to create a parent repair replacement or parent replay packet
- **THEN** Runtime MUST reject the transition
- **AND** Runtime MUST NOT use the old child id or old accepted result as current authority.

#### Scenario: Active lineage is visible to downstream review
- **WHEN** Runtime issues a parent backward replay packet after child lineage resolution
- **THEN** the packet MUST include the active child ids
- **AND** the packet MUST include lineage rows mapping original child ids to active child ids when any child changed.
