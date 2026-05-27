## 1. Model And Contract

- [x] 1.1 Extend the focused Controller patrol FlowGuard model with nonterminal status-return and stale-projection hazards.
- [x] 1.2 Update OpenSpec validation and focused model checks so the known-bad case fails if final-answer is allowed without `controller_stop_allowed=true`.
- [x] 1.3 Extend model-hierarchy checks so full FlowGuard confidence cannot omit visible/user-triggerable controls, buttons, status returns, recovery paths, or terminal/stop branches.

## 2. Runtime Payloads

- [x] 2.1 Add clear status-update versus stop-permission fields to foreground standby snapshots.
- [x] 2.2 Add final-answer preflight and projection-authority fields to patrol timer results.
- [x] 2.3 Add display-only projection authority and `next_step` source/freshness metadata to current status summaries.

## 3. Prompt Surfaces

- [x] 3.1 Update Controller role, resume/reentry, generated table prompt, and top-level skill wording to say user/status return is not Controller stop permission.
- [x] 3.2 Add propagation checks or focused tests for the new Controller stop-preflight wording.

## 4. Runtime Tests And Verification

- [x] 4.1 Add targeted router runtime tests for nonterminal user/status return, waiting standby, and stale/completed display projection.
- [x] 4.2 Run focused FlowGuard and targeted runtime checks.
- [x] 4.3 Start heavy meta/capability regressions through the background log contract and inspect final artifacts before reporting completion.

## 5. Sync And Evidence

- [x] 5.1 Update FlowGuard adoption evidence with trigger, commands, findings, skipped checks, and residual risk.
- [x] 5.2 Sync the validated repository-owned FlowPilot skill into the local installed skill and run install audit/check.
- [x] 5.3 Review git state, preserve unrelated peer changes, and create a local git commit if the worktree scope is clean enough to commit safely.
