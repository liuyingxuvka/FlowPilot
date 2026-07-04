## ADDED Requirements

### Requirement: Hard-gate escape returns to the owning normal gate

FlowPilot SHALL handle every current-contract hard-gate leak detected before final quality review by freezing final dispatch, identifying the first owning gate that should have blocked the state, and returning execution to that normal gate.

#### Scenario: Missing node entry returns to node acceptance

- **WHEN** final-dispatch preflight detects `missing_node_entry_gate` for a route node
- **THEN** runtime MUST NOT issue the final Reviewer packet
- **AND** runtime MUST return the frontier to that route node's normal `node_acceptance_plan` and `node_context_package` flow.

#### Scenario: Missing parent replay returns to parent replay

- **WHEN** final-dispatch preflight detects `missing_parent_backward_replay` for a parent/module
- **THEN** runtime MUST NOT issue the final Reviewer packet
- **AND** runtime MUST return execution to the normal `parent_backward_replay` gate for that parent/module.

#### Scenario: Missing PM disposition returns to PM disposition

- **WHEN** final-dispatch preflight detects `missing_pm_disposition` for a route node
- **THEN** runtime MUST NOT issue the final Reviewer packet
- **AND** runtime MUST return execution to the normal `node_pm_disposition` gate for that node.

#### Scenario: Active packet leak returns to packet repair

- **WHEN** final-dispatch preflight detects an unresolved current packet before final quality review
- **THEN** runtime MUST NOT issue the final Reviewer packet
- **AND** runtime MUST return to the existing current-packet repair flow.

### Requirement: Final quality review starts only after runtime hard-gate preflight passes

FlowPilot SHALL issue final backward quality review only after runtime has mechanically confirmed that current hard gates are complete for the effective route.

#### Scenario: Clean hard-gate preflight allows quality review

- **WHEN** runtime hard-gate preflight finds no node-entry, parent-replay, PM-disposition, packet-lifecycle, stale-evidence, or terminal-replay leak in the current hard-gate boundary
- **THEN** runtime may issue the final Reviewer packet for delivered-output and route-composition quality review.

#### Scenario: Reviewer is not asked to repair hard-gate leaks

- **WHEN** runtime hard-gate preflight finds a hard-gate leak
- **THEN** runtime MUST classify and route the leak before Reviewer dispatch
- **AND** the final Reviewer packet MUST NOT be used to collect or judge the missing hard-gate artifact.
