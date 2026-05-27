## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Validate the new OpenSpec change and keep scope limited to material progress generation projection.
- [x] 1.2 Confirm real FlowGuard is available and keep the upgraded control-plane model as the acceptance monitor.

## 2. Runtime Implementation

- [x] 2.1 Add active material batch/generation projection and use it in material packet next-action selection.
- [x] 2.2 Add a material-generation exception to stale run-state merge so old material progress flags cannot be restored after reissue.
- [x] 2.3 Tighten role-output bridge reconciliation so current-generation material disposition closure cannot be short-circuited by a run-wide flag.
- [x] 2.4 Ensure material dispatch block metadata references the active repair transaction when a current repair generation exists.

## 3. Tests And FlowGuard Validation

- [x] 3.1 Add focused regression tests for stale material flags versus active repair batch projection.
- [x] 3.2 Add focused regression tests for stale-save material flag resurrection and role-output current-generation disposition closure.
- [x] 3.3 Run focused tests and FlowGuard control-plane checks; triage failures before continuing.
- [x] 3.4 Run heavier model regressions in background artifacts and inspect exit/meta files before claiming pass.

## 4. Sync And Local Git

- [x] 4.1 Sync repository-owned FlowPilot skill into the local installed version after source validation.
- [x] 4.2 Run install audit/check sequentially after sync.
- [x] 4.3 Inspect final git status, then stage/commit this change's files if validation is current and peer changes remain isolated.
