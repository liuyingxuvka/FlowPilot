## ADDED Requirements

### Requirement: Terminal Supplemental Repair Uses Current Route Repair Rules
FlowPilot SHALL represent terminal supplemental repair execution as current
route repair nodes or subnodes, not as a separate workflow or direct Worker
shortcut.

#### Scenario: PM chooses repair node
- **WHEN** PM accepts a terminal supplemental repair contract that requires
  executable work
- **THEN** PM MUST create repair nodes or subnodes with current route ids,
  repair item ids, and return/replay scope
- **AND** the normal route repair and node acceptance gates MUST run before
  Worker dispatch.

#### Scenario: Direct Worker shortcut attempted
- **WHEN** a supplemental repair contract tries to dispatch Worker execution
  without a current repair node or accepted same-gate reissue path
- **THEN** runtime MUST reject the dispatch as unsupported.

### Requirement: Supplemental Repair Invalidates Affected Terminal Evidence
FlowPilot SHALL invalidate affected final ledger, final matrix, terminal
replay, and node evidence when supplemental repair nodes change the delivered
artifact or acceptance surface.

#### Scenario: Repair node changes delivered work
- **WHEN** a supplemental repair node changes implementation, validation,
  product behavior, or evidence used by terminal closure
- **THEN** runtime MUST require final ledger rebuild and terminal backward
  replay before completion.
