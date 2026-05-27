## 1. Baseline And Coordination

- [x] 1.1 Record KB, OpenSpec, FlowGuard, repository coordination, and git
  baseline evidence for this pass.
- [x] 1.2 Verify real FlowGuard import and toolchain preflight.
- [x] 1.3 Record the Risk Intent Brief and FlowGuard adoption start note.

## 2. FlowGuard Model Contracts

- [x] 2.1 Add or update focused FlowGuard coverage for officer packet lifecycle
  hazards.
- [x] 2.2 Add or update focused FlowGuard coverage for continuation quarantine
  hazards.
- [x] 2.3 Add or update focused FlowGuard coverage for closure user-report and
  route display refresh hazards.
- [x] 2.4 Add or update focused FlowGuard coverage for Router scheduler
  settlement drift and active runtime-writer wait hazards.
- [x] 2.5 Run focused model checks and inspect counterexamples before runtime
  edits.

## 3. Officer Packet Lifecycle

- [x] 3.1 Add runtime templates/contracts for PM officer requests and officer
  reports.
- [x] 3.2 Add Router/runtime validation so officer reports require a matching
  current-run request and router-authorized event.
- [x] 3.3 Add focused runtime tests for authorized and invented officer report
  events.

## 4. Continuation State Quarantine

- [x] 4.1 Add current-run quarantine template/schema for imported prior run
  evidence, old role IDs, stale control state, and old assets.
- [x] 4.2 Add Router/runtime validation or helper logic that records and enforces
  quarantine before imported evidence becomes authority.
- [x] 4.3 Add focused tests for old control state, old role IDs, and old asset
  quarantine.

## 5. Closure User Report And Route Display Refresh

- [x] 5.1 Add final user-report template and runtime writer gated by clean
  terminal closure.
- [x] 5.2 Add route display refresh metadata/writer for chat route signs and
  UI-readable snapshots.
- [x] 5.3 Add focused tests proving user reports do not create closure authority
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

- [x] 6.1 Update `scripts/check_install.py` and related validators for new
  templates, cards, specs, and model result files.
- [x] 6.2 Update HANDOFF, equivalence docs, legacy matrix, and FlowGuard adoption
  log with completed/remaining status.
- [x] 6.3 Validate OpenSpec change in strict mode.

## 7. Verification, Sync, And Git

- [x] 7.1 Run focused unit tests and focused FlowGuard checks for touched
  boundaries.
- [x] 7.2 Launch and inspect background Meta and Capability regressions through
  the repository artifact contract.
- [x] 7.3 Run install self-check, smoke/fast validation, installed skill sync,
  installed skill freshness check, and local install sync audit.
- [x] 7.4 Review final diff for accidental behavior changes, generated noise,
  private paths, or release/publish side effects.
- [x] 7.5 Run KB postflight, stage, and commit the completed local maintenance
  work without pushing, tagging, or publishing.
