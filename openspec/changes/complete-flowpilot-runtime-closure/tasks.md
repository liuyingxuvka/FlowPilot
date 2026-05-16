## 1. Baseline And Coordination

- [x] 1.1 Record KB, OpenSpec, FlowGuard, repository coordination, and git
  baseline evidence for this pass.
- [x] 1.2 Verify real FlowGuard import and toolchain preflight.
- [x] 1.3 Record the Risk Intent Brief and FlowGuard adoption start note.

## 2. FlowGuard Model Contracts

- [ ] 2.1 Add or update focused FlowGuard coverage for officer packet lifecycle
  hazards.
- [ ] 2.2 Add or update focused FlowGuard coverage for continuation quarantine
  hazards.
- [ ] 2.3 Add or update focused FlowGuard coverage for closure user-report and
  route display refresh hazards.
- [x] 2.4 Add or update focused FlowGuard coverage for Router scheduler
  settlement drift and active runtime-writer wait hazards.
- [ ] 2.5 Run focused model checks and inspect counterexamples before runtime
  edits.

## 3. Officer Packet Lifecycle

- [ ] 3.1 Add runtime templates/contracts for PM officer requests and officer
  reports.
- [ ] 3.2 Add Router/runtime validation so officer reports require a matching
  current-run request and router-authorized event.
- [ ] 3.3 Add focused runtime tests for authorized and invented officer report
  events.

## 4. Continuation State Quarantine

- [ ] 4.1 Add current-run quarantine template/schema for imported prior run
  evidence, old role IDs, stale control state, and old assets.
- [ ] 4.2 Add Router/runtime validation or helper logic that records and enforces
  quarantine before imported evidence becomes authority.
- [ ] 4.3 Add focused tests for old control state, old role IDs, and old asset
  quarantine.

## 5. Closure User Report And Route Display Refresh

- [ ] 5.1 Add final user-report template and runtime writer gated by clean
  terminal closure.
- [ ] 5.2 Add route display refresh metadata/writer for chat route signs and
  UI-readable snapshots.
- [ ] 5.3 Add focused tests proving user reports do not create closure authority
  and stale displays do not override route state.

## 5A. Router Runtime Settlement

- [x] 5A.1 Upgrade the existing Router reconciliation path so an already
  reconciled Controller action backfills its matching Router scheduler row.
- [x] 5A.2 Upgrade the existing runtime JSON writer settlement path so fresh or
  progressing writers wait/retry instead of surfacing false PM/control
  blockers.
- [x] 5A.3 Add focused runtime tests for reconciled-action scheduler backfill
  and writer-progress wait behavior.

## 6. Validators, Docs, And Install Checks

- [ ] 6.1 Update `scripts/check_install.py` and related validators for new
  templates, cards, specs, and model result files.
- [ ] 6.2 Update HANDOFF, equivalence docs, legacy matrix, and FlowGuard adoption
  log with completed/remaining status.
- [ ] 6.3 Validate OpenSpec change in strict mode.

## 7. Verification, Sync, And Git

- [ ] 7.1 Run focused unit tests and focused FlowGuard checks for touched
  boundaries.
- [ ] 7.2 Launch and inspect background Meta and Capability regressions through
  the repository artifact contract.
- [ ] 7.3 Run install self-check, smoke/fast validation, installed skill sync,
  installed skill freshness check, and local install sync audit.
- [ ] 7.4 Review final diff for accidental behavior changes, generated noise,
  private paths, or release/publish side effects.
- [ ] 7.5 Run KB postflight, stage, and commit the completed local maintenance
  work without pushing, tagging, or publishing.
