## 1. Specification And Model Coverage

- [x] 1.1 Add focused FlowGuard coverage for role recovery memory injection, obligation classification, PM escalation boundaries, and replacement ordering.
- [x] 1.2 Model valid existing ACK/output settlement so recovered roles do not redo already-satisfied obligations.
- [x] 1.3 Model replacement row durability before original wait rows are marked `superseded`.
- [x] 1.4 Add or update model checks that preserve original obligation order when multiple replay rows are created.

## 2. Router Recovery Replay

- [x] 2.1 Add Router helpers that collect outstanding obligations for a recovered role from current-run controller-visible metadata.
- [x] 2.2 Add evidence validation for current-run ACK and output envelopes without reading sealed packet or result bodies.
- [x] 2.3 Add replacement ACK/work row creation that links replacements to original waits with `replaces`, `replacement_reason`, and `original_order`.
- [x] 2.4 Mark original wait rows `superseded` with `superseded_by` only after the replacement row is durably visible.
- [x] 2.5 Update successful role recovery flow to run mechanical replay before any PM recovery escalation.
- [x] 2.6 Keep PM escalation only for ambiguity, conflicts, repeated recovery failure, or route/acceptance/task-semantics changes.

## 3. Tests And Regression

- [x] 3.1 Add runtime tests for existing ACK settlement after role recovery.
- [x] 3.2 Add runtime tests for existing output settlement after role recovery.
- [x] 3.3 Add runtime tests for ordered replacement creation and superseding links.
- [x] 3.4 Add runtime tests that successful mechanical replay does not notify PM.
- [x] 3.5 Run focused runtime tests for the changed recovery path.

## 4. Installation And Integration

- [x] 4.1 Sync the local installed FlowPilot skill/runtime version after implementation.
- [x] 4.2 Run local install verification after syncing.
- [x] 4.3 Record the user-approved skip for heavyweight FlowGuard meta and capability regressions because they are too heavy for this pass.
- [x] 4.4 Report that heavyweight regression artifacts are not completion evidence for this pass because the checks were skipped/stopped by user direction.
- [x] 4.5 Review worktree status so parallel AI changes are preserved and included in final integration guidance.
