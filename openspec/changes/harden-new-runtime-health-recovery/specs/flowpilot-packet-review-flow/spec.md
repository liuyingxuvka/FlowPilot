## MODIFIED Requirements

### Requirement: Node Context Package Contract

Node acceptance plan intake SHALL validate only a top-level
`node_context_package`. It SHALL NOT normalize or accept
`node_acceptance_plan.node_context_package` or any other nested/legacy package
shape before reviewer repair loops.

#### Scenario: Nested node acceptance package is rejected

- **GIVEN** a node acceptance plan result contains
  `node_acceptance_plan.node_context_package`
- **WHEN** the runtime records the node acceptance plan closure
- **THEN** the runtime MUST reject the result as missing the top-level
  `node_context_package`
- **AND** MUST NOT record an accepted node context package for the current
  repair generation
