## 1. OpenSpec and FlowGuard Grounding

- [x] 1.1 Record the synthetic trace replay proposal, design, and spec.
- [x] 1.2 Verify FlowGuard is importable and identify the existing model/test ownership boundaries.
- [x] 1.3 Keep this change isolated from the active material-progress peer work.

## 2. Trace Replay Test Scaffolding

- [x] 2.1 Add a test-only synthetic trace helper that describes role, actions, fake output, evidence kind, and expected outcome.
- [x] 2.2 Ensure trace helpers use real packet/runtime/router APIs rather than direct completion mutation.
- [x] 2.3 Add trace result assertions for controller visibility, body-open receipts, hashes, PM disposition, blockers, and evidence kind.

## 3. First Critical Trace Packs

- [x] 3.1 Add happy-path worker packet/result trace coverage.
- [x] 3.2 Add ACK-only-not-completion trace coverage.
- [x] 3.3 Add sealed-body isolation, wrong role/agent, and stale hash trace coverage.
- [x] 3.4 Add PM disposition and raw-result-to-reviewer rejection trace coverage.
- [x] 3.5 Add fixture/synthetic evidence boundary and background progress-only trace coverage.

## 4. FlowGuard Alignment and Regression Evidence

- [x] 4.1 Add the trace replay tests to the relevant routine/router test surface.
- [x] 4.2 Run focused trace replay tests and existing packet/runtime tests.
- [x] 4.3 Run FlowGuard model-test-alignment checks and inspect full coverage/release convergence findings.
- [x] 4.4 Launch long model regressions in background when required and inspect final artifacts before claiming completion.

## 5. Sync and Finalization

- [x] 5.1 Recheck git status for peer-agent changes before sync.
- [x] 5.2 Sync the installed local FlowPilot skill only after owned source validation and only when it will not absorb unrelated peer work.
- [x] 5.3 Run install check/audit serially after any sync.
- [x] 5.4 Record final evidence and remaining coverage expansion work.
