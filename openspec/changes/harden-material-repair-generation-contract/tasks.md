## 1. OpenSpec and FlowGuard Grounding

- [x] 1.1 Validate this change's OpenSpec artifacts and keep the scope tied to existing repair/control transaction flows.
- [x] 1.2 Confirm real FlowGuard is available and rerun the upgraded control-plane friction model before code confidence claims.

## 2. Runtime Implementation

- [x] 2.1 Extend material packet reissue commit so material index, active parallel batch, packet ids, and generation metadata stay current-generation scoped.
- [x] 2.2 Tighten operation replay so replayed Controller actions synthesize fresh identity and use current material generation state for material packet/result operations.
- [x] 2.3 Ensure `controller_repair_work_packet` receipts fold into the owning repair transaction through the existing receipt reconciliation path and facade export.
- [x] 2.4 Gate PM material-scan result disposition on active batch, packet id, result envelope, and current generation identity.
- [x] 2.5 Extend existing scoped event idempotency to PM package disposition events using role-output body refs/hashes plus batch/generation scope.
- [x] 2.6 Extend the existing break-glass patch lifecycle with validation/final-disposition closure.

## 3. Tests and FlowGuard Validation

- [x] 3.1 Add or update focused tests for material reissue generation, operation replay identity, Controller repair receipt fold, PM stale disposition rejection, role-output dedupe, and break-glass closure.
- [x] 3.2 Run focused syntax, unit/runtime, and FlowGuard checks; triage failures before continuing.
- [x] 3.3 Run heavier model/router regressions in background artifacts where practical and inspect exit/meta artifacts before claiming pass.

## 4. Sync and Local Git

- [x] 4.1 Sync the validated repository-owned FlowPilot skill into the local installed version.
- [x] 4.2 Run install audit/check sequentially after sync.
- [x] 4.3 Inspect final git status and stage/commit only this change's files if peer-agent changes are isolated and validation is current.
