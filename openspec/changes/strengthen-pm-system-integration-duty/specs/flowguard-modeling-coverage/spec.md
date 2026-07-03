## ADDED Requirements

### Requirement: FlowGuard models scattered local-pass/global-incoherence
FlowGuard SHALL include modelable planning and process hazards for scattered local-pass/global-incoherence.

#### Scenario: Product architecture misses integration intent
- **WHEN** product architecture lacks a root system integration intent
- **THEN** planning-quality FlowGuard checks SHALL detect the missing obligation.

#### Scenario: Route lacks composition review
- **WHEN** a route has locally plausible nodes but lacks parent/child/sibling composition review
- **THEN** FlowGuard route process checks SHALL detect the route risk.

#### Scenario: Node plan lacks integration touchpoint
- **WHEN** a node plan has acceptance criteria but no upstream, downstream, sibling, or parent relation
- **THEN** FlowGuard planning-quality checks SHALL detect the missing integration touchpoint.

#### Scenario: Final ledger relies only on node-level evidence
- **WHEN** final closure cites only local node reports and lacks whole-output composition review
- **THEN** FlowGuard terminal coverage checks SHALL detect the missing final integration evidence.

### Requirement: Escaped integration defects feed model maturation
FlowGuard SHALL route escaped hard integration defects into model-miss or maturation evidence.

#### Scenario: Final scattered output escaped earlier checks
- **WHEN** final replay finds a hard scattered-output defect after earlier local passes
- **THEN** FlowGuard model-miss triage SHALL identify whether the product, route, node, parent replay, final replay, or test model missed the same-class defect family.
