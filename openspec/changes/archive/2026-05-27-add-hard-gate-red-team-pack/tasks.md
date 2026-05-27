## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean git state, and peer-agent coordination boundaries.
- [x] 1.2 Inventory existing AI-facing entrypoints and current synthetic/hard-gate evidence.
- [x] 1.3 Select finite red-team cells for this pass and define protected state invariants.

## 2. Matrix

- [x] 2.1 Add a hard-gate red-team coverage matrix script and result JSON.
- [x] 2.2 Add matrix rows for unauthorized event, role-output authority mismatch, packet identity mismatch, progress-only proof, stale run authority, and terminal overclaim.
- [x] 2.3 Add known-bad matrix cases for missing evidence, missing invariant, missing recovery route, and progress-only proof accepted as pass.
- [x] 2.4 Add tests for matrix completeness and known-bad rejection.

## 3. Runtime Red-Team Packages

- [x] 3.1 Add runtime red-team tests for unauthorized current wait events preserving pending state.
- [x] 3.2 Add runtime red-team tests for role-output router-supplied event authority mismatch.
- [x] 3.3 Add runtime red-team tests for packet/result identity or hash mismatch preserving ledger state.
- [x] 3.4 Add runtime red-team tests for progress-only background proof overclaim rejection.
- [x] 3.5 Add runtime red-team tests for stale run authority and terminal closure overclaim non-mutation.
- [x] 3.6 Fix any discovered runtime acceptance or state-mutation bug without weakening hard invariants. No runtime acceptance bug was exposed by this pass.

## 4. Validation

- [x] 4.1 Run focused hard-gate matrix tests.
- [x] 4.2 Run focused runtime red-team tests.
- [x] 4.3 Run model-test alignment and refresh generated evidence.
- [x] 4.4 Run fast tier and affected router child tiers, using background artifacts only when final exit artifacts exist.
- [x] 4.5 Run Meta and Capability model regressions in background and inspect final artifacts.

## 5. Sync and Finalization

- [x] 5.1 Validate OpenSpec change.
- [x] 5.2 Synchronize repository-owned local FlowPilot skill.
- [x] 5.3 Run install sync audit, install check, and check_install serially.
- [x] 5.4 Record FlowGuard adoption evidence and predictive-KB postflight.
- [x] 5.5 Commit local git state without pushing or publishing.
