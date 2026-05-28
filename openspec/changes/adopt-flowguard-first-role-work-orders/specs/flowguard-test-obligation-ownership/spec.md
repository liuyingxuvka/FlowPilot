## ADDED Requirements

### Requirement: Test obligation rows retain FlowGuard work-order provenance
FlowPilot SHALL record the FlowGuard work-order/report provenance for test,
validation, replay, model-test alignment, and TestMesh obligations.

#### Scenario: Officer report creates test obligations
- **WHEN** a Product or Process FlowGuard report identifies
  `model_obligations`, `ordinary_test_evidence`, `missing_test_kinds`, or
  validation freshness gaps
- **THEN** PM SHALL copy those rows into the relevant test obligation matrix
  with the originating `flowguard_work_order_id` and `flowguard_report_id`
- **AND** PM SHALL choose a disposition before the dependent gate can pass.

#### Scenario: Stale report stales test obligation coverage
- **WHEN** a FlowGuard report becomes stale because the route, model boundary,
  code boundary, packet scope, evidence path, or final artifact set changed
- **THEN** dependent test obligation rows SHALL become unresolved until PM
  reruns the report, repairs the matrix, defers to a named node, or records an
  authorized waiver.

### Requirement: Progress-only FlowGuard evidence cannot close validation gaps
FlowPilot SHALL reject validation, TestMesh, Model-Test Alignment, or
background FlowGuard evidence that has only progress output and no final
artifact completion proof.

#### Scenario: Background check is still running
- **WHEN** a test obligation cites a background FlowGuard check
- **THEN** the row SHALL require final exit/meta artifacts and completion
  status before it can be dispositioned as covered
- **AND** Reviewer and final ledger checks SHALL treat progress-only evidence
  as missing.

#### Scenario: Worker cannot cover broad FlowGuard gap locally
- **WHEN** a worker packet discovers that an assigned obligation needs broad,
  slow, layered, stale, release-only, or cross-node validation
- **THEN** the Worker SHALL return a bounded blocker, `needs_pm`, or PM
  Suggestion Item
- **AND** PM SHALL route the gap to TestMesh, Model-Test Alignment, another
  FlowGuard work order, repair, deferral, or waiver with authority.
