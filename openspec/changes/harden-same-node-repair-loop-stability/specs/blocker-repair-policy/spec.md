## ADDED Requirements

### Requirement: Same-node consecutive repair loops enter break-glass after five repeats
FlowPilot SHALL stop issuing ordinary PM repair packets when the same current route node has more than five consecutive repair attempts for the same blocker problem identity.

#### Scenario: Same node repeats beyond threshold
- **WHEN** a current route node has more than five consecutive blockers with the same route node identity, `blocker_class`, `gate_kind`, and `required_recheck_role`
- **THEN** FlowPilot MUST NOT issue another ordinary PM repair packet for that blocker
- **AND** FlowPilot MUST expose a control-plane break-glass duty with the node/problem family, attempt count, threshold, and involved blocker ids.

#### Scenario: Same node stays under threshold
- **WHEN** a current route node has five or fewer consecutive blockers with the same route node identity, `blocker_class`, `gate_kind`, and `required_recheck_role`
- **THEN** FlowPilot MAY continue through ordinary PM repair.

#### Scenario: Cross-node similar failures do not trigger the threshold
- **WHEN** similar blocker classes occur across different route nodes
- **THEN** FlowPilot MUST NOT combine those different-node blockers to trigger same-node repair-loop break-glass.

#### Scenario: Consecutive chain reset
- **WHEN** the node passes, the current route moves to a different node, or the next blocker has a different blocker problem identity
- **THEN** FlowPilot MUST NOT count blockers before that break as part of the current same-node consecutive loop.

### Requirement: Reviewer problem identity preserves repeat evidence
FlowPilot SHALL require Reviewer and FlowGuard Operator blocking reports to reuse the same blocker class when the same current route node repeats the same defect.

#### Scenario: Same node same defect keeps blocker class
- **WHEN** Reviewer or FlowGuard Operator blocks a repair result for the same current route node and the same defect as the prior blocker
- **THEN** the blocking report MUST keep the prior defect's `blocker_class` instead of inventing a new name for the same problem.

#### Scenario: Different defect can use different blocker class
- **WHEN** Reviewer or FlowGuard Operator identifies a genuinely different defect in the same node
- **THEN** the blocking report MAY use a different `blocker_class`
- **AND** FlowPilot MUST treat it as a different problem identity for same-node loop counting.

### Requirement: Noncurrent repair history is not current blocker state
FlowPilot SHALL preserve repair history in the ledger while excluding noncurrent repair rows from current blocker status and final-preflight blocking decisions.

#### Scenario: Old repair row remains history only
- **WHEN** a repair row belongs to a noncurrent route node, superseded packet, cleared blocker, or obsolete repair packet
- **THEN** FlowPilot MUST NOT present that row as a current active blocker
- **AND** FlowPilot MUST NOT block final-preflight solely because of that old row.

#### Scenario: Current same-node chain remains countable
- **WHEN** prior repair rows remain part of the current same-node consecutive problem chain
- **THEN** FlowPilot MAY use those rows as repair-loop evidence without presenting obsolete rows as active current work.
