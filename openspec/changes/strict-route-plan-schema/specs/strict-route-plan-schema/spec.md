## ADDED Requirements

### Requirement: PM Route Plan Uses Strict Schema

FlowPilot SHALL materialize route nodes only from a PM planning result whose body is a JSON object with `schema_version` equal to `flowpilot.route_plan.v1` and a non-empty `nodes` array.

#### Scenario: Structured route plan materializes exact nodes

- **WHEN** an accepted PM planning result body contains `schema_version: "flowpilot.route_plan.v1"` and three entries in `nodes`
- **THEN** the runtime MUST materialize exactly those three node IDs in that order
- **AND** it MUST preserve each node's required outputs, deliverable checks, validation checks, and acceptance criteria.

#### Scenario: Numbered text route plan is rejected

- **WHEN** an accepted PM planning result body contains numbered prose instead of the strict schema
- **THEN** route materialization MUST fail with a schema error
- **AND** the runtime MUST NOT create fallback route nodes.

#### Scenario: Compatibility field is rejected

- **WHEN** an accepted PM planning result body uses `route_nodes` instead of `nodes`
- **THEN** route materialization MUST fail with a schema error
- **AND** the runtime MUST NOT infer or translate the compatibility field.

### Requirement: Route Materialization Has No Bootstrap Fallback

FlowPilot SHALL NOT use active route step titles, fixed bootstrap steps, numbered text, or responsibility inference as fallback route materialization sources.

#### Scenario: Empty strict node list blocks route materialization

- **WHEN** a PM planning result has the strict schema but an empty `nodes` array
- **THEN** route materialization MUST fail
- **AND** the active route's existing `steps` MUST NOT be used as replacement nodes.

#### Scenario: Missing node identity blocks route materialization

- **WHEN** a strict route-plan node omits `node_id` or `title`
- **THEN** route materialization MUST fail
- **AND** the runtime MUST NOT synthesize a node identity.
