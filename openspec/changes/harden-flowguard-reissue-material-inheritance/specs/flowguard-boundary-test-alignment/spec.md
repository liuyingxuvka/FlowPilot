## ADDED Requirements

### Requirement: Derived material inheritance aligns model, code, and tests
FlowPilot SHALL bind derived-packet material inheritance requirements to FlowGuard model obligations, owner code contracts, and current tests before claiming the reissue class is covered.

#### Scenario: Field lifecycle projects derived material reads
- **WHEN** FieldLifecycleMesh represents `authorized_result_reads`, `authorized_result_read_ids`, `required_authorized_reads_before_submit`, and `required_authorized_read_count`
- **THEN** it MUST include the derived-packet lifecycle from source FlowGuard packet to runtime-generated reissue packet
- **AND** the projection MUST name the runtime owner that writes the inherited reads into the fresh packet envelope and handoff contract.

#### Scenario: Contract exhaustion generates inherited-read loss cases
- **WHEN** ContractExhaustionMesh receives the derived FlowGuard reissue material boundary
- **THEN** it MUST generate canonical bad cases for lost inherited authorized reads, lost required read ids, lost required read count, lost target result, lost blocker identity, lost semantic recheck contract, lost repair obligations, and lost evidence policy
- **AND** each case MUST have a current oracle reaction and downstream Model-Test Alignment/TestMesh handoff.

#### Scenario: Model-Test Alignment binds owner code contract
- **WHEN** Model-Test Alignment reviews the packet-result family obligations
- **THEN** it MUST include an obligation for `flowguard_reissue_preserves_required_authorized_result_reads`
- **AND** it MUST bind that obligation to the runtime code path that creates the derived packet and to tests that exercise the public runtime packet/result flow.

### Requirement: Observed reissue miss has replay-style regression evidence
FlowPilot SHALL include observed-regression evidence for the live miss class where a FlowGuard check result is mechanically rejected and the generated reissue packet must inherit the subject-result body read obligation.

#### Scenario: WorldGuard-style reissue path is covered
- **WHEN** a regression simulates a FlowGuard check packet for a repair-blocker target result
- **AND** the first FlowGuard result is mechanically rejected for missing `semantic_recheck`
- **THEN** the fresh reissue packet MUST inherit the target result as a required authorized read
- **AND** submitting the reissue result before opening that target result body MUST fail.

#### Scenario: Broad coverage consumes the new cases
- **WHEN** Cartesian, synthetic-agent, model-test alignment, or coverage-inventory checks claim the packet/result family is covered
- **THEN** the new derived-material-inheritance cases and evidence ids MUST be consumed by those checks
- **AND** skipped, stale, progress-only, or release-only evidence MUST NOT satisfy the routine local claim.
