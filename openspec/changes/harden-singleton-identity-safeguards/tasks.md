## 1. Grounding And Audit Design

- [x] 1.1 Verify real FlowGuard import/version and record the downstream routes for singleton duplicate safety.
- [x] 1.2 Inventory existing singleton/plural authority surfaces and write an install-visible singleton authority matrix.
- [x] 1.3 Add a read-only live `.flowpilot` singleton audit plan that never mutates peer-agent state.

## 2. FlowGuard Model And Diagnostics

- [x] 2.1 Add a focused FlowGuard singleton identity model with legal replay and illegal duplicate hazard cases.
- [x] 2.2 Add a checker that writes singleton authority result artifacts with decision, confidence, gaps, and known-bad outcomes.
- [x] 2.3 Feed singleton authority gaps into model maturation and model-test-code diagnostic output.

## 3. Runtime Surfaces And Tests

- [x] 3.1 Add the read-only live singleton audit implementation for active run ledgers, daemon locks, packet ledgers, route/frontier state, and material/progress evidence.
- [x] 3.2 Add targeted tests for daemon writer, package disposition, route replacement, material generation, ACK/output, and live-audit classification.
- [x] 3.3 Update install readiness to require the singleton authority model/check/result without racing install sync.

## 4. OpenSpec, Validation, And Sync

- [x] 4.1 Run strict OpenSpec validation for this change and keep `adopt-flowguard-model-maturation` verification tasks visible.
- [x] 4.2 Run focused singleton, maturation, idempotency, route-mutation, daemon, model-test-code, install, and smoke checks.
- [x] 4.3 Run heavyweight Meta and Capability regressions through the background artifact contract and inspect exit/meta artifacts.
- [x] 4.4 Sync the repository-owned FlowPilot skill to the local installed copy, then run local install audit/check serially.
- [x] 4.5 Update documentation, adoption logs, task checkboxes, and final evidence without reverting peer-agent changes.
