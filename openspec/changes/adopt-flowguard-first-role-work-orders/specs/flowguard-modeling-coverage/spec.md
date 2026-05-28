## ADDED Requirements

### Requirement: FlowGuard modeling coverage uses work-order/report traceability
FlowPilot SHALL connect startup snapshots, modeling plans, officer reports,
PM model decisions, route activation, and final ledgers through FlowGuard
work-order/report ids.

#### Scenario: Product modeling plan creates a work order
- **WHEN** PM asks Product FlowGuard Officer to model product behavior,
  product architecture, UI flow, source-system behavior, or product-fit risk
- **THEN** the Product Modeling Plan SHALL cite a `flowguard_work_order_id`
- **AND** the Product Officer report SHALL cite the same id before PM can
  accept product model coverage.

#### Scenario: Process modeling plan creates a work order
- **WHEN** PM asks Process FlowGuard Officer to model route viability,
  development process, repair return paths, validation freshness, mesh
  boundaries, or closure readiness
- **THEN** the Process Modeling Plan SHALL cite a `flowguard_work_order_id`
- **AND** the Process Officer report SHALL cite the same id before PM can
  accept process model coverage.

#### Scenario: Final ledger closes work-order coverage
- **WHEN** PM builds the final route-wide gate ledger
- **THEN** the ledger SHALL list every active FlowGuard work order, accepted
  report, stale report, skipped report, blocked report, and PM disposition
- **AND** completion SHALL remain blocked while any active work order is
  missing, stale, progress-only, unsupported, or not dispositioned by PM.

### Requirement: FlowGuard route selection is report evidence
FlowPilot SHALL require FlowGuard reports to identify the specific FlowGuard
route or satellite skill used and why it was the smallest sufficient route.

#### Scenario: Officer selects the smallest applicable FlowGuard route
- **WHEN** an Officer handles a work order
- **THEN** the report SHALL name whether it used Existing Model Preflight,
  DevelopmentProcessFlow, Model-Test Alignment, TestMesh, StructureMesh,
  ModelMesh, Model Miss Review, UI Flow Structure, Code Structure
  Recommendation, Architecture Reduction, or the model-first kernel
- **AND** the report SHALL explain why a broader route was not required or why
  escalation to a broader route is needed.

#### Scenario: PM cannot replace route evidence with prose
- **WHEN** PM accepts a FlowGuard-backed model, route, repair, or closure claim
- **THEN** PM SHALL cite the report id and freshness status
- **AND** PM prose alone SHALL NOT close missing report evidence.
