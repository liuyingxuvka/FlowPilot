## Why

FlowPilot's high-assurance route is intentionally thorough, but the current
runtime and validation implementation repeatedly persists unchanged state,
duplicates the same stream and proof bodies, and retains completed evidence
without a safe archive lifecycle.  Long formal runs can therefore spend
avoidable I/O, time, and disk capacity on control material without producing
additional user-visible work or stronger proof.

## What Changes

- Preserve FlowPilot's explicit opt-in boundary and the complete PM, Worker,
  FlowGuard, Reviewer, repair, replay, and terminal-closure route.
- Make Router/daemon reconciliation semantically idempotent: observing the
  same state, action, receipt, wait, reminder, or projection produces no new
  authoritative write or duplicate history.
- Keep the existing responsive observation loop and atomic durable writes, but
  write full state and derived projections only when their semantic content
  changes; replace unbounded daemon tick output with a bounded summary.
- Coalesce repeated role progress reports that do not change status and are
  not due for a liveness reminder, using the existing progress fields and one
  finite status vocabulary.
- Keep one logical workstream plan per result, update its rows in place, and
  reference evidence instead of copying command-level plans or log bodies.
- **BREAKING**: replace normal-runtime v4 background evidence manifests with
  one direct v5 owner-reference contract.  v4 remains historical audit input
  only and is rejected by normal runtime; there is no compatibility reader,
  newest-manifest fallback, or dual emission.
- Keep stdout and stderr as the sole raw stream bodies; redefine
  `combined.txt` as a bounded terminal index and store proof references,
  hashes, exit state, cleanup evidence, and bounded failure excerpts instead
  of copied raw streams or prior owner rows.
- Extend the existing report-first retention tool into a frozen plan and
  explicitly invoked archive/apply transaction that protects current, live,
  nonterminal, locked, referenced, pinned, or otherwise ambiguous runs.
- Add resource-bounded FlowGuard scenarios and TestMesh evidence proving the
  optimized implementation preserves the current formal-route behavior.
- Synchronize the source version, clean installed FlowPilot projection, local
  Git state, SkillGuard maintenance evidence, GitHub tag, and GitHub Release
  only after one frozen final validation.

## Capabilities

### New Capabilities

None.  This change strengthens existing FlowPilot runtime, evidence, and
maintenance capabilities instead of creating a parallel workflow.

### Modified Capabilities

- `persistent-router-daemon`: no-change ticks do not mutate semantic state or
  accumulate unbounded tick output.
- `runtime-ledger-persistence`: atomic full-state and projection writes become
  content-aware while retaining corruption, lock, and read-back safeguards.
- `control-plane-ledger-consolidation`: repeated receipt, action, wait,
  reminder, and deferred-fold observations remain one current fact.
- `work-packet-ack-and-no-output-retry`: role progress persists only on a
  semantic status change or a due liveness update.
- `complete-ai-workstream-orchestration`: each substantive role maintains one
  obligation-level workstream plan and evidence-reference surface.
- `tiered-flowpilot-test-validation`: background logs and owner evidence use
  the v5 reference contract with one copy of each raw stream.
- `flowguard-test-obligation-ownership`: exact owner proof remains complete
  through immutable references instead of copied proof bodies.
- `repository-maintenance-guardrails`: read-only reporting gains a safe frozen
  plan and explicit archive/apply lifecycle without automatic deletion.
- `flowpilot-maintenance-ideal-state`: release readiness includes resource
  boundedness, current model authority, install parity, SkillGuard closure,
  and source/tag/release identity parity.

## Impact

The change affects Router daemon and receipt reconciliation, core runtime
projection persistence, role progress handling, role prompt/cards, background
test child/supervisor evidence, impact-manifest loading, retention tooling,
FlowGuard models and topology, tests, installation projection, versioning, and
release evidence.  Existing v4 manifests cease to be normal-runtime authority;
the first v5 baseline is produced by one explicit frozen owner.  Existing
formal quality gates and raw stdout/stderr proof remain mandatory.
