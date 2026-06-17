## MODIFIED Requirements

### Requirement: Remaining StructureMesh Gaps Are Cleared By Evidence

The FlowPilot structure-maintenance workflow SHALL treat a remaining model-code-test StructureMesh gap as complete only when the corresponding parent entrypoint is below its diagnostic threshold and the split has current model, code, and external test evidence.

#### Scenario: Runtime contract split preserves public facade behavior

- **GIVEN** an oversized `skills/flowpilot/assets/*.py` runtime contract surface appears as a `runtime_contract` StructureMesh gap
- **WHEN** the module is split into child modules
- **THEN** the original module path SHALL continue to provide its public imports or exported data
- **AND** tests SHALL prove the child modules combine to the same externally visible contract where tables or manifests are split
- **AND** new child modules SHALL have model/test/code diagnostic evidence rather than becoming `missing_test` or `internal_only_test` gaps.

#### Scenario: Route frontier completion split preserves legal-action authority

- **GIVEN** `flowpilot_router_route_frontier_policy_completion` is reported as a `needs_structure_split` public route-frontier facade
- **WHEN** route-authority, legal-action, and node-completion helper blocks are moved into child owner modules
- **THEN** the original module SHALL still export the same route-authority and frontier-completion function names
- **AND** facade imports SHALL resolve to the same function objects as the owning child modules
- **AND** the regenerated full diagnostic SHALL report zero `needs_structure_split` findings for `asset:flowpilot_router_route_frontier_policy_completion`
- **AND** no new child owner module SHALL appear as `missing_test`, `internal_only_test`, or `missing_model`.
