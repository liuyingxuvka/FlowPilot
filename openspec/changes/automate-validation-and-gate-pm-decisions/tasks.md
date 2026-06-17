## 1. Contracts And Modeling

- [x] 1.1 Add OpenSpec requirements for system validation evidence and unified PM continue-repair decision gates.
- [x] 1.2 Add a focused FlowGuard model and runner for validator removal, system validation, and PM decision-gate hazards.

## 2. Runtime Implementation

- [x] 2.1 Add ledger support for system validation evidence and PM decision gate records.
- [x] 2.2 Change ordinary reviewer pass to record system validation evidence and issue closure without a validator packet.
- [x] 2.3 Preserve legacy validation packet pass/fail behavior for existing packets and repair paths.
- [x] 2.4 Stage PM continue-repair decisions until FlowGuard, reviewer, system validation, and closure pass.
- [x] 2.5 Stage route-mutating PM disposition decisions until FlowGuard, reviewer, system validation, and closure pass.
- [x] 2.6 Keep terminal PM stop/authority dispositions separate from continue-repair paths.

## 3. Tests And Rehearsals

- [x] 3.1 Update focused high-standard tests for no ordinary validator packet and system validation evidence.
- [x] 3.2 Add tests proving legacy validation failure remains blocking.
- [x] 3.3 Add tests proving PM continue-repair decisions are staged and direct repair bypasses are rejected.
- [x] 3.4 Update focused runtime check runners that assume validator packets on the ordinary success path.
- [x] 3.5 Add model-test alignment checks for the new FlowGuard model obligations.

## 4. Validation And Sync

- [x] 4.1 Run OpenSpec validation and FlowGuard project audit.
- [x] 4.2 Run focused FlowGuard model checks and targeted pytest.
- [x] 4.3 Run affected runtime check runners.
- [x] 4.4 Run background meta/capability checks and inspect artifacts.
- [x] 4.5 Sync repo-owned installed FlowPilot skill and run install audit/check.
- [x] 4.6 Stage/commit only scoped files and leave unrelated existing work untouched.
