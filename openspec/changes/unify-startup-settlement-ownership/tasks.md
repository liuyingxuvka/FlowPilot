## 1. Model And Contract

- [x] 1.1 Confirm real FlowGuard import for this change.
- [x] 1.2 Run the focused daemon reconciliation model with the new foreground-wait and single-owner startup receipt hazards.
- [x] 1.3 Validate the OpenSpec change.

## 2. Runtime Implementation

- [x] 2.1 Reuse the existing runtime JSON write-lock liveness rule for foreground startup/status retries.
- [x] 2.2 Route startup daemon bootloader completion through the existing startup receipt effect and scheduled receipt reconciliation path.
- [x] 2.3 Preserve stale-lock, unsupported-receipt, and real blocker behavior.

## 3. Tests And Verification

- [x] 3.1 Add focused runtime regression coverage for foreground active-writer settlement.
- [x] 3.2 Add focused runtime regression coverage for startup receipt single-owner reconciliation and replay no-op behavior.
- [x] 3.3 Run focused tests and local install sync/audit. Heavyweight Meta and Capability regressions were deferred by explicit user direction because they are too heavy for this focused pass.

## 4. Finalization

- [x] 4.1 Update FlowGuard adoption notes with commands, findings, and any deferred checks.
- [ ] 4.2 Preserve compatible peer-agent changes and prepare the local git commit once the combined worktree is verified.
