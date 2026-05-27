## 1. Contract And Runtime

- [x] 1.1 Add a shared Router-owned state replay registry for legal state loader actions.
- [x] 1.2 Reconcile registered state loader receipts by replaying the registered Router action handler.
- [x] 1.3 Preserve unsupported/missing-postcondition blocker routing for unregistered stateful receipts.

## 2. FlowGuard Model And Source Audit

- [x] 2.1 Add safe and known-bad Router-owned state replay scenarios to the focused receipt-fold model.
- [x] 2.2 Extend the source audit so `load_*_state` flag writers must be present in the replay registry.
- [x] 2.3 Regenerate focused receipt-fold and control-plane friction model result artifacts.

## 3. Runtime Tests And Validation

- [x] 3.1 Add a resume runtime regression for `load_resume_state` receipt replay.
- [x] 3.2 Preserve durable Controller wait creation order during role-recovery replay.
- [x] 3.3 Harden fresh runtime write-lock classification exposed by background router tests.
- [x] 3.4 Run focused foreground checks for the replay path and related control-plane contracts.
- [x] 3.5 Run model and router runtime regressions in background logs and inspect final artifacts.

## 4. Local Sync

- [x] 4.1 Sync the installed local FlowPilot skill after code and model evidence settle.
- [x] 4.2 Run install audit/check commands after sync.
- [x] 4.3 Review local git status and keep this change scoped away from unrelated peer-agent edits.
