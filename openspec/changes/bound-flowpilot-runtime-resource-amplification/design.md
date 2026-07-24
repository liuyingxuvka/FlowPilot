## Context

FlowPilot is an explicit opt-in, high-risk project-control runtime.  Its
quality route is not the source of the observed storage problem: PM, Worker,
FlowGuard, Reviewer, repair, terminal ledger, and backward replay are required
and remain required.  The amplification comes from physical representation and
control-loop behavior:

- the daemon observes related files every second and saves full state even
  when no semantic state changed;
- repeated receipt/wait/reminder observations refresh timestamps and append
  duplicate history;
- a small ledger change rematerializes many unchanged projections;
- role prompts turn minor activity into persistent progress events;
- background validation stores stdout/stderr and then copies both into
  `combined.txt`, while supervisor metadata copies impact plans, snapshots,
  owner identities, reuse tickets, and prior owner rows;
- completed run and validation directories have a report-only retention tool
  but no safe archive transaction.

The current checkout also moved from FlowGuard 0.58.5 to 0.61.0.  The upgrade
requires one content-addressed observed model-system authority.  The existing
165 topology entries and native runners are retained as that authority; this
change extends their current owners and later activates one whole revision set.

No active repository-root `.flowpilot/state.json` existed when the change was
started, so no live formal run needs an in-place runtime-state conversion.
Untracked peer work is outside this change and must remain untouched.

## Goals / Non-Goals

**Goals:**

- Preserve the complete existing formal route and its evidence strength.
- Make unchanged observation a true no-op for authoritative state, ledgers,
  projections, and semantic history.
- Keep atomic replace, fsync, read-back, lock, liveness, and corruption
  behavior for writes that are actually needed.
- Store each raw validation stream and each owner proof body once.
- Make daemon output, progress evidence, supervisor progress, combined output,
  failure excerpts, and retention metadata bounded.
- Replace v4 normal-runtime evidence authority directly with v5; reject old
  authority instead of carrying two readers or two emitters.
- Extend the existing retention report into an explicit, frozen, recoverable
  archive transaction without automatic cleanup.
- Prove behavioral parity and resource bounds through existing FlowGuard model
  families, a focused child model, TestMesh, and ordinary tests.
- Finish with source/install/version/Git/SkillGuard/GitHub Release parity.

**Non-Goals:**

- Do not change FlowPilot admission: only an explicit current-conversation user
  request may start FlowPilot.
- Do not introduce a light/medium/heavy FlowPilot route or skip PM, Worker,
  FlowGuard, Reviewer, repair, replay, or terminal gates.
- Do not replace the one-second related-file observation window in this
  release.  Dynamic backoff requires later measurement and a separate change.
- Do not create a second router state ledger, semantic-revision ledger,
  persistent dirty-section ledger, repeat-count history, or role-specific
  progress ledger.
- Do not content-address or migrate the per-run runtime-kit snapshot in this
  release; measured runtime-kit copies are small relative to validation logs
  and currently provide frozen prompt/card evidence.
- Do not automatically archive or delete real historical runs during install
  or validation.

## Decisions

### 1. Separate observation and liveness from semantic persistence

The existing one-second daemon tick remains.  Each tick computes changes in
memory and returns a compact classification:

- semantic state changed;
- projection changed;
- work frontier advanced;
- change reasons.

No semantic delta means no call path may rewrite router state, action rows,
scheduler ledgers, semantic history, or unchanged derived projections.
Liveness continues through the existing small daemon lock/status surface.
`save_run_state` performs a final canonical-equality defense and returns
whether it wrote.

The daemon result removes the unbounded `ticks[]` body and exposes bounded
scalars such as `tick_count`, `semantic_change_count`,
`no_change_tick_count`, `last_tick`, and `terminal`; diagnostic samples are
bounded.

Alternative considered: increase the tick interval.  Rejected for this
release because it changes detection latency and hides the real defect:
unchanged observations should be cheap regardless of frequency.

### 2. Reconcile one stable fact once

Controller receipt reconciliation compares the receipt SHA-256, current action
state, and scheduler effect before writing.  A matching current receipt is
classified as already current and changes no timestamps or history.

The following observation-only state is removed as current authority:

- action `seen_count`;
- action `last_seen_at`;
- copied `wait_reminder_history` arrays;
- repeated deferred-fold, reminder, and passive-wait history entries.

The existing action, receipt, scheduler, pending-wait, and return-event records
remain the owners.  Current wait state keeps only compact last-reminder
identity/count fields where needed.  Controller ledgers are rebuilt only when
their semantic inventory changes and preserve exact owner/action references
instead of copying completed bodies.

Alternative considered: add a `repeat_count` to history.  Rejected because
incrementing it would still turn every no-change observation into a write.

### 3. Make core projections content-aware without persistent dirty state

Every text/JSON projection writer first compares canonical content.  The core
runtime computes changed top-level ledger categories in memory and materializes
only the affected projection families.  It does not persist dirty categories
or create another recovery authority.

`events.jsonl` appends only events newer than the current terminal event
identity; it does not scan and rewrite the complete event file.  Existing
atomic durability remains the only write path.

### 4. Coalesce progress and keep one workstream table

The existing fields remain authoritative:

- `progress_count`;
- `last_progress_at`;
- `last_progress_status`.

Allowed persistent status is limited to:

- `started`;
- `working`;
- `waiting_external`;
- `verifying`;
- `repairing`;
- `blocked`;
- `ready_to_submit`.

A repeated identical status inside the ten-minute liveness window returns
`coalesced=true` without an event, count increment, or ledger save.  A status
change or due reminder persists.  Existing five-minute ACK reminder,
ten-minute ACK replacement, ten-minute result reminder, and thirty-minute
result replacement thresholds remain unchanged.

`contract_self_check.workstream_plan_and_completion` remains the sole role
plan.  One row represents an acceptance obligation or meaningful phase, not a
command/read/microstep.  Final submission updates the same rows; Reviewer and
FlowGuard cite the plan and report differences rather than copying it.

### 5. Store raw streams once and replace v4 with v5 references

The five stable background paths remain:

- `.out.txt`;
- `.err.txt`;
- `.combined.txt`;
- `.exit.txt`;
- `.meta.json`.

Stdout and stderr are the only raw stream bodies.  `combined.txt` becomes a
terminal stream index containing status, stream paths, hashes, byte/line
counts, exit code, timestamps, and cleanup state; it contains no raw stream
copy and is capped at 32 KiB.  Failure excerpts are capped at 200 lines or
64 KiB.

The supervisor writes:

1. one immutable `<base>.impact-plan.json`;
2. one small mutable `<base>.progress.json`;
3. one terminal `<base>.owner-index.json`;
4. the existing bounded terminal meta and exit markers.

Child processes resolve their identity by impact-plan path, plan SHA-256, and
owner id.  Temporary `.owner.json` bodies are removed.  Reused owners store
only immutable prior proof references plus current reuse-ticket identity; they
do not copy prior logs, snapshots, owner rows, or full ticket dictionaries.

The normal runtime accepts only
`acceptance_testmesh_evidence_manifest.v5`.  v4 files remain audit-only
historical material and are rejected by the normal loader.  This release
executes one explicit full v5 seed baseline after source/toolchain freeze.
There is no converter, automatic v4 import, newest-manifest search, fallback,
dual read, or dual emission.

Alternative considered: keep v4 and add optional v5 fields.  Rejected because
it would preserve duplicate authority and make proof freshness ambiguous.

### 6. Extend retention through one existing maintenance owner

`scripts/flowpilot_runtime_retention.py` remains the sole maintenance entry.
Its public CLI and import surface remain a thin facade. Read-only inventory and
protection classification live under one scan owner, canonical identity and
path helpers live under one pure common owner, and frozen-plan/archive/index/
cleanup side effects remain under the facade apply owner. StructureMesh
records every moved function, state, side effect, configuration value, public
entrypoint, dependency edge, and parity boundary. This prevents the retention
repair itself from becoming another oversized control-plane script.
Its default remains read-only.  Planning covers both `.flowpilot/runs` and
`tmp/test_background`, classifying:

- current/index status;
- terminal evidence validity;
- live daemon/process/lease;
- open packet/action;
- active write locks;
- external proof/checkpoint/release references;
- pins and protected reasons;
- bytes and proposed action.

`max_runs` ranks only already eligible entries; age or quota never creates
eligibility.

An explicit `plan` freezes exact candidates and a plan SHA-256.  A separately
invoked `apply --plan ... --plan-sha256 ...` revalidates every protection,
creates and reads back a ZIP under `.flowpilot/archives`, records archive
path/hash/time in the existing run index, and only then removes archived heavy
subdirectories.  Current, live, nonterminal, locked, referenced, pinned,
unknown, or inconsistent entries fail closed.  The implementation is enabled
and tested, but the release workflow does not apply it to real historical data
automatically.

### 7. Use existing FlowGuard owners and one focused child model

Existing models remain primary:

- control-plane friction;
- event idempotency;
- daemon liveness;
- controller wait-receipt audit;
- progress lifecycle;
- complete workstream orchestration;
- validation artifact canonicalization;
- acceptance TestMesh;
- test tiering/slow-test contract;
- model mesh and model-test alignment.

A focused resource-boundedness child model composes these obligations:

`Observe(InputFingerprint x RouterState) -> Set(DeltaClassification x RouterState)`

`Reconcile(ReceiptSet x ActionState) -> Set(ActionEffects x ActionState)`

`Persist(ChangeSet x PersistentState) -> Set(WriteResult x PersistentState)`

`RecordProgress(Status x LeaseState) -> Set(PersistedOrCoalesced x LeaseState)`

`StoreEvidence(StreamResult x ProofState) -> Set(ArtifactRefs x ProofState)`

`Retain(TerminalEvidence x RetentionState) -> Set(ProtectOrArchiveCandidate x RetentionState)`

The project topology and authoritative ModelSystemSnapshot are rebuilt after
model/source changes.  The complete candidate snapshot is activated only
through one accepted ModelRevisionSet against the exact observed head.

### 8. Freeze once for installation, SkillGuard, and release

Focused checks run while implementation changes.  One final full model owner
and one final full test owner run only after source, toolchain, impact plan,
version, and owner inventory are frozen.

The clean FlowPilot consumer projection is installed transactionally and
audited without `.skillguard` or author evidence.  Immediately before
SkillGuard maintenance, the current installed SkillGuard source/version is
rechecked because it is being maintained concurrently.  SkillGuard compiles
and validates the FlowPilot maintenance unit using its then-current contract
and private evidence roots.

The release uses version `0.13.0` unless an already published remote tag makes
that identity unavailable.  Source HEAD, local installed FlowPilot projection,
remote default branch, annotated tag, and GitHub Release must resolve to the
same frozen release identity.

## Risks / Trade-offs

- **Risk: content comparison hides a required timestamp update** → Timestamps
  that are part of semantic contracts remain in the canonical comparison;
  observation-only timestamps are removed or kept only in liveness status.
- **Risk: v5 direct replacement makes old proof unavailable to normal
  execution** → Expected behavior.  v4 stays readable as historical files by
  humans/tools, while one explicit v5 seed baseline restores current proof.
- **Risk: a reference target is deleted while a compact proof still points to
  it** → Retention treats every proof/checkpoint/release reference as a hard
  protection and verifies archive contents before index commit.
- **Risk: parallel AI changes overlap changed files** → Re-read before every
  patch, preserve unknown changes, stage only task-owned files, and revalidate
  affected evidence if a peer modifies an input.
- **Risk: final background validation itself creates large output** → v5
  streaming/index contracts apply to the validation owner; terminal proof
  remains complete without a second raw copy.
- **Trade-off: runtime-kit copies remain** → The measured cost is small
  compared with validation logs, and retaining frozen per-run kits avoids a
  broad resolver/migration change in this release.

## Migration Plan

1. Upgrade and audit the local FlowGuard project record; establish the first
   observed model-system authority from current topology/model/runner sources.
2. Land OpenSpec proposal, delta specifications, design, tasks, and strict
   validation.
3. Add resource-bounded FlowGuard scenarios, field lifecycle rows, TestMesh
   ownership, and focused negative cases.
4. Implement no-op Router/receipt/ledger persistence and bounded daemon output.
5. Implement progress/workstream coalescing and content-aware core projection.
6. Implement v5 background evidence, reject v4 in normal runtime, and execute
   one explicit v5 seed baseline after freeze.
7. Extend and test retention plan/archive/apply without applying it to real
   historical data.
8. Rebuild/check project topology; construct and validate the complete
   candidate model snapshot; activate one accepted revision set.
9. Run focused checks, then one frozen full model/test validation and repair
   all failures.
10. Bump to `0.13.0`, install/audit the clean local FlowPilot projection,
    recheck current SkillGuard, run FlowPilot's SkillGuard maintenance unit,
    and verify installed-current state.
11. Commit only owned files, push the release commit, create an annotated tag
    and source-only GitHub Release, then verify local/remote/install parity.

Rollback before publication is ordinary source rollback plus revalidation of
the previous snapshot.  After publication, any correction uses a new immutable
version and tag.  Model-authority rollback is allowed only through FlowGuard's
revision rollback transaction with restored/compensated effects and current
old-snapshot evidence.
