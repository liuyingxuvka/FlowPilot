## 1. TestMesh Model And Evidence Shape

- [x] 1.1 Add an acceptance-registry TestMesh model/runner with parent gate, child partitions, required payload cells, and scoped release gaps.
- [x] 1.2 Add current result JSON output for the acceptance-registry TestMesh and include timeout/not-run/progress-only evidence states.
- [x] 1.3 Add unit coverage for the model runner, known-bad cells, and parent confidence boundaries.

## 2. Fake AI And Work-Package Payload Chaos

- [x] 2.1 Extend fake AI rehearsal scenarios with malformed and corrected acceptance-item payload cells.
- [x] 2.2 Add terminal replay segment payload chaos for missing, duplicate, unexpected, and corrected segment targets.
- [x] 2.3 Add route mutation recovery coverage where replacement nodes must disposition all active acceptance items.

## 3. Router Tier Mapping And Slow Evidence

- [x] 3.1 Add or update TestMesh evidence mapping for router-quality-gates, router-packets, router-route, router-terminal, integration, release, and final-confidence tiers.
  - Done: mappings are explicit; router-packets/route/terminal/integration/release/final-confidence evidence gaps remain visible when not completed.
- [x] 3.2 Preserve timeout and background-progress-only states as non-pass evidence in the acceptance-registry TestMesh.
  - Done: release not-run, missing router background artifacts, progress-only background artifacts, stale pass, timeout, and failed packet-tier artifacts are non-pass evidence.
- [x] 3.3 Verify slow quality-gate child slices can support scoped parent confidence without hiding skipped release tiers.
  - Done: synthetic passed child artifacts support scoped confidence; real partial quality-gate artifacts are reported as progress-only until all expected children have final exit artifacts.

## 4. Validation And Closure

- [x] 4.1 Run OpenSpec strict validation for this change.
- [x] 4.2 Run focused unit tests, fake AI rehearsal, acceptance TestMesh runner, planning-quality, field-contract, field-mesh, model-test-alignment, meta/capability checks, and topology build/check.
  - Done: final current-code guard-family checks passed. Fresh routine background evidence under `tmp/test_background_acceptance_finaljson_20260614` passed for router quality, packets, route, and terminal child suites; the acceptance TestMesh runner is green for routine scope while release-only evidence remains explicitly deferred and not claimed.
- [x] 4.3 Run install sync, local install audit, install check, final check_install, FlowGuard adoption logging, and KB postflight.
  - Done: install sync, local install audit, install check, topology build/check, check_install, release tier, final-confidence gate, FlowGuard adoption logging, and KB postflight passed. A formal FlowPilot run was started for controller exit authority, but final-preflight currently blocks on `open_startup_intake` until the native startup window returns an interactive result.
