## ADDED Requirements

### Requirement: PM Compiles Atomic Acceptance Item Registry
FlowPilot SHALL require the PM high-standard contract to include an
`acceptance_item_registry` that compiles explicit user requirements, implicit
user commitments, PM-added high standards, hard low-quality-success risks,
target-realization obligations, child-skill standards, and FlowGuard
obligations into atomic acceptance items.

#### Scenario: Missing registry blocks high-standard contract
- **WHEN** PM submits a `task.high_standard_contract` result
- **AND** the result omits `acceptance_item_registry.items`
- **THEN** runtime MUST mechanically block the result
- **AND** runtime MUST reissue the current high-standard contract packet with
  `acceptance_item_registry` listed as a required result field.

#### Scenario: PM high standard becomes item
- **WHEN** PM adds a high-standard current-run requirement beyond the user's
  literal wording
- **THEN** PM MUST create at least one active acceptance item with
  `source_type` set to `pm_high_standard`
- **AND** that item MUST include a quality floor, required evidence, owner
  node projection, review gate projection, and final replay requirement.

### Requirement: Acceptance Items Are Projected Through Existing Route Gates
FlowPilot SHALL project every active acceptance item through existing route
nodes, node acceptance plans, work packets, Reviewer gates, FlowGuard route
checks, PM dispositions, final ledgers, and terminal replay maps using
`acceptance_item_ids`.

#### Scenario: Route has orphan acceptance item
- **WHEN** an active acceptance item has no owner node and no authorized waiver,
  supersession, or user stop
- **THEN** route review and FlowGuard route-process checks MUST block route
  activation or final closure.

#### Scenario: Node plan lacks item projection
- **WHEN** a route node owns an active acceptance item
- **AND** the node acceptance plan omits that item from
  `acceptance_item_projection`
- **THEN** Reviewer MUST block the node acceptance plan before Worker dispatch.

### Requirement: Acceptance Item Closure Is High Quality Or Blocked
FlowPilot SHALL treat active acceptance item closure as binary at hard gates:
an item is either closed with current high-quality evidence, explicitly
waived/superseded by authority, or unresolved. Low-quality or existence-only
evidence MUST NOT close an active item.

#### Scenario: Existence-only evidence tries to close item
- **WHEN** an active acceptance item requires proof of depth
- **AND** PM or Worker cites only a file, report, screenshot, ledger row, or
  generic completion statement that does not prove the hard part
- **THEN** Reviewer MUST block the item as low-quality closure
- **AND** final ledger MUST keep the item unresolved.

#### Scenario: PM disposition omits item closure
- **WHEN** PM accepts a node that owns active acceptance items
- **AND** the PM disposition omits `accepted_acceptance_item_ids`,
  `blocked_acceptance_item_ids`, and waiver/supersession disposition for those
  items
- **THEN** final requirement matrix MUST keep those items unresolved.

### Requirement: Final Replay Closes Every Active Acceptance Item
FlowPilot SHALL require final route-wide ledger, final requirement evidence
matrix, and terminal backward replay to include every active acceptance item
and its high-quality closure status before PM completion approval.

#### Scenario: Route mutation leaves old item open
- **WHEN** route mutation replaces a node or subtree
- **AND** an active acceptance item from the previous route is neither closed,
  superseded, waived, nor assigned to a replacement node
- **THEN** final ledger MUST report the item as unresolved
- **AND** closure MUST remain blocked.

#### Scenario: Terminal replay omits acceptance item
- **WHEN** runtime issues terminal backward replay segment targets
- **AND** the active acceptance item table has an item not covered by the
  submitted terminal replay
- **THEN** terminal closure MUST remain blocked
- **AND** the missing item MUST be visible in final unresolved rows.
