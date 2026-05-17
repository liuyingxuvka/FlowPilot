## ADDED Requirements

### Requirement: Route mutation runtime oracle is split into focused child suites

The router route-mutation runtime oracle SHALL expose focused child suites for
draft activation, model-miss triage, acceptance repair, preconditions,
transactions, topology mutation, sibling replacement, and parent backward
replay.

#### Scenario: Router route tier composes route-mutation child suites

- **GIVEN** the router route tier is planned
- **WHEN** the tier runner builds its command list
- **THEN** it SHALL include each focused route-mutation child suite
- **AND** it SHALL NOT use the old monolithic `router_route_mutation_core`
  command as routine evidence.

### Requirement: Compatibility aggregate remains available

The legacy `tests.router_runtime.route_mutation` module SHALL remain runnable
as a compatibility aggregate for explicit full-oracle checks.

#### Scenario: Full route-mutation oracle is requested explicitly

- **GIVEN** a maintainer runs `python -m unittest -v tests.router_runtime.route_mutation`
- **WHEN** the aggregate module loads tests
- **THEN** it SHALL run the same focused child test cases exactly once.

### Requirement: FlowGuard TestMesh owns every route-mutation child suite

FlowGuard maintenance evidence SHALL assign every focused route-mutation child
suite one owner, one command, and one final background artifact path.

#### Scenario: Route-mutation child evidence is missing

- **GIVEN** a router route validation claim
- **AND** one focused route-mutation child suite has no owner or final artifact
- **WHEN** FlowGuard reviews the TestMesh evidence
- **THEN** the validation claim SHALL be rejected.
