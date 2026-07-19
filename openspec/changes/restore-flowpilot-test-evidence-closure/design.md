## Context

FlowPilot has a strong finite-contract registry and several large generated
matrices, but the current proof chain has four breaks:

1. `current_handoff_contract`, packet-body mirrors, and private helpers can all
   influence a fake response, so one green replay does not prove the role-visible
   checklist is correct.
2. Model cells, test-name reuse, and hard-coded TestMesh status are counted as
   passed execution even when no public runtime call was made.
3. Large Cartesian universes have no single formal claim boundary, exclusions,
   executable oracle, or parent-consumed proof receipt.
4. The existing test tiers do not directly own the formal fake-AI/current-
   contract suites, and background progress can outlive the evidence cited by a
   release claim.
5. Current authority is often named by prose path or role memory rather than a
   structured, fingerprinted reference that binds the original user intent,
   accepted contract, active route/node/packet, and current evidence identity.
6. Public manual resume is requested-role driven, but the retained diagnostic
   router can derive a wider set from all same-run role slots and bindings.
7. Reviewer behavior is correctly stage-specific and adversarial, but a stale
   handoff/model description still treats the deleted
   `independent_challenge` object as a positive result field.
8. Timeout or interrupted-launch evidence is not reusable unless the complete
   descendant process tree is proven empty, and broad checks are not comparable
   unless every producer and consumer binds the same frozen source fingerprint.

The current-contract discipline forbids compatibility shims and parallel
authorities.  The existing packet/result registry, handoff envelope, result
validator, blocker/reissue path, TestMesh, MTA, and ModelMesh surfaces are
sufficient; this design extends those owners rather than adding another
runtime, ledger, or packet family.

## Goals / Non-Goals

**Goals:**

- Establish one mechanical data flow from the result registry to the role-
  visible checklist and the public submit validator.
- Exhaust the declared finite structural universe while executing the smallest
  proof-complete representative set through expensive runtime paths.
- Make forbidden/alias, review-policy, identity, timing, route, replay, and
  side-effect coverage non-vacuous and measurable.
- Keep current authority explicit through one structured reference shape
  carried by existing handoff and node-context surfaces.
- Make public and diagnostic resume agree on one exact current-obligation role
  target without prewarming idle or historical responsibilities.
- Preserve the existing complete-workstream structure and compact Reviewer
  result contract while making Reviewer the owner of semantic completeness and
  evidence quality.
- Require descendant-zero cleanup after every timeout, cancellation, or
  interruption before evidence reuse or a new execution owner.
- Bind each release claim to current child evidence,
  code/test/model alignment, parent receipt consumption, one frozen covered-
  source fingerprint, installation sync, and same-commit Git/GitHub
  publication evidence.
- Keep PR, nightly, and release validation within explicit, measured budgets.

**Non-Goals:**

- Prove every possible future natural-language AI response.
- Run the unconstrained multi-billion-cell product through the full runtime.
- Preserve packet-body contract mirrors, old role aliases, daemon authority,
  private-helper replay, or generic unknown-family success.
- Create a new packet kind, result family, role, compatibility schema, or
  second evidence ledger.
- Create a universal fixed role set, prewarm every possible role, or treat an
  idle current-run binding as a current work obligation.
- Add a production natural-language judge, make Runtime score workstream
  semantics, or restore `independent_challenge` as a successful result field.
- Add a compatibility reader, legacy translator, alias, newest-result
  selector, or fallback success path for any replaced authority.

## Decisions

### 1. One contract authority and one role-visible projection

`packet_result_contracts.effective_result_contract_*` remains the mechanical
owner.  Runtime projects the complete effective contract into the envelope
`current_handoff_contract.required_report_contract`.  `open-packet` creates a
checklist solely from that envelope and adds only current run/packet/lease/open
identity plus a canonical contract fingerprint.

Packet bodies remain semantic input.  Missing handoff fields or an invalid
handoff schema block; body values never repair or override the checklist.

Alternative: preserve envelope/body parity and compare both.  Rejected because
it retains two authorities and makes tampering/freshness ambiguous.

### 2. Canonical fake AI starts from the real open result

The canonical responder accepts a successful current `open-packet` result,
verifies ACK, identities, checklist schema/fingerprint, required material
delivery, and then derives legal or adversarial payloads from the checklist.
Selected execution cases submit through the public `submit-result` command or
function.  Reissue uses a fresh current packet/open result; an old checklist is
not a repair authority.

Reviewer rehearsal consumes the delivered `review_window.review_depth_rule`.
It does not reconstruct policy from a static flow-id table.  Unknown family,
missing policy, or missing identity fails closed.

Alternative: add a second responder beside body-based helpers.  Rejected
because old helpers would remain an alternate green path.

### 3. Full means full only within a declared finite universe

ContractExhaustionMesh owns a `ContractCoverageUniverse` with finite axes,
interaction groups, payload boundaries, exclusions, required child receipts,
and claim scope.  Every reject/block/reissue/repair case has a `ContractOracle`
with expected status, feedback fields, repair fields, forbidden next step, and
side-effect boundary.

Case ids include the full source contract path.  Many-to-one canonicalization
is permitted only when the cases share an `oracle_signature`:

`(validator branch, status, error code, state transition, allowed side
effects, feedback schema, next action)`.

Alternative: retain sanitized names and accept collisions.  Rejected because
distinct aliases/paths can silently share one test target.

### 4. Structural enumeration and expensive execution are separate lanes

- Lane A: enumerate every model-scoped structural cell and exclusion.
- Lane B: execute every single mechanical mutation through the real validator.
- Lane C: generate a constraint-aware pairwise covering array and execute every
  selected row through dispatch, lease, ACK, open, checklist response, and
  public submit.
- Lane D: execute three-wise (and selected four-wise) combinations for
  identity/timing/route, decision/branch/owner, review-policy/material,
  accepted-pointer/closure, and repair/retry/no-delta risk groups.
- Lane E: always replay historical misses and run deterministic malformed JSON,
  size/depth, duplicate-key, encoding, replay, concurrency, and cross-run fuzz
  cases.

Historical defects are pinned and cannot be removed by covering-array
optimization.  Full model enumeration does not increment executed/passed
runtime counts.

Alternative: run all 7.1 million scoped cells end to end.  Rejected because it
adds days of cost without adding distinct behavior proof.

### 5. Proof-backed evidence mesh

Each execution shard writes selected case ids, command, result path, final exit
status, duration, environment, source/test/runtime/result fingerprints, and a
`ProofArtifactRef`.  Reuse requires a current `TestResultReuseTicket`.
TestMesh reports actual selected/executed test counts, never owned model-cell
counts.

MTA splits the former broad Cartesian obligation into risk-shard obligations
bound to owner `CodeContract`s, current external tests, source audit, and
runtime/boundary observations.  Observed values come from execution artifacts,
not copied expected metadata.  ModelMesh parent receipts consume every required
child receipt through `CompositeHandoffAcceptance` before broad confidence.

### 6. Tiered execution and background evidence

The initial engineering budgets are:

- focused formal-submit fast lane: 2-4 minutes after profiling;
- full PR gate: at most 10-15 minutes;
- nightly: at most 45-60 minutes;
- release/final confidence: approximately two hours.

Windows background runs default to two isolated workers.  Each supervisor and
child writes `.out.txt`, `.err.txt`, `.combined.txt`, `.exit.txt`, and
`.meta.json`.  Progress is liveness; only final result plus exit status is pass.
Budgets are gates after an initial 30-80-case public-path benchmark, not assumed
performance claims.

### 7. Current execution-source and responsibility policy

`daemon_replay` is a historical negative input and must never continue a
current stage.  Unsupported/unknown responsibilities are rejected instead of
normalized to Worker.  Result-body role labels remain a separate enum and do
not authorize packet responsibility aliases.

Every positive current-runtime decision consumes structured current-authority
references from the existing handoff or `node_context_package` surfaces.  A
reference item is discriminated by `reference_kind` and binds an
`authority_id`, owner, repository/run-scoped path, content fingerprint,
consumer scope, and exact applicable identity such as run id, route version,
node id, packet id, result id, or source generation.  Applicable identity is
declared by the reference kind; it is never filled from chat history, a newest
artifact search, an old run pointer, or a missing-field default.

The reference shape reuses `node_context_package.relevant_references`,
`current_handoff_contract`, review-window material references, and their
existing currentness gates.  It does not create a new authority ledger or
parallel packet field.  Missing, duplicate, stale, foreign-run, hash-mismatched,
or mutually conflicting references block at the current owner with structured
repair feedback.

Alternative: leave references as human-readable strings and ask each role to
rediscover the right file.  Rejected because the original user standard and
current runtime identity can silently drift without a mechanical currentness
boundary.

### 8. Ordered sync, candidate closure, and publication

Source and verification freeze precedes topology rebuild.  Repository-owned
skill sync runs before install audit/check and must not run concurrently with
them.  Candidate scope consumes `all`, `release`, and `final-confidence`
evidence, then updates version/changelog/README, runs local public-boundary
checks, writes a verified handoff, and creates one exact task-owned local Git
commit.  The maintainer's latest 2026-07-18 scope update supersedes both the
earlier no-commit boundary and the later publication deferral: this task must
commit only the agreed task-owned files, push the task branch, fast-forward
the GitHub default branch to that exact commit, create annotated tag
`v0.12.0`, and create a source-only GitHub Release for the same tag and commit.
Any non-fast-forward default-branch update, tag collision, release collision,
or commit mismatch blocks publication instead of selecting another path.

The intended version is `0.12.0` because this is a public workflow/evidence
contract expansion rather than a narrow patch.

### 9. Existing workstream structure, semantic Reviewer ownership

Every substantive PM, Worker, research/evidence Worker, Reviewer, FlowGuard
Operator, or helper result continues to expose the existing `Workstream Plan
and Completion` subsection inside `Contract Self-Check`.  The role accounts
for numbered steps, intended outcomes, status, evidence, deviations,
delegation integration, verification, unresolved items, and claim consistency.
Runtime projects and preserves the current mechanical report contract but does
not infer whether prose, evidence, or completion quality is semantically
sufficient.

Reviewer consumes the delivered stage-specific `review_depth_rule`, the
current authority references, the real subject artifacts, and the workstream
rows.  Reviewer decides whether the plan was complete, the difficult work was
actually performed, delegation was integrated, verification was meaningful,
and the final claim matches current evidence.  Hard gaps go to `blockers`;
nonblocking higher-standard improvements go to `pm_suggestion_items`.

Reviewer remains on the compact current result contract:
`pm_visible_summary`, `reviewed_by_role`, `passed`, `findings`, `blockers`,
`pm_suggestion_items`, and `contract_self_check`.  Independent challenge is
mandatory behavior inside the review process, not a positive payload object.
`independent_challenge` remains deleted and forbidden except in
deleted/forbidden inventories, negative tests, or historical labels.

Alternative: require a broad challenge object or have Runtime score workstream
semantics.  Rejected because either path recreates the retired result
subprotocol or turns mechanical validation into an unreliable language judge.

### 10. Requested-role resume has an exact target set

The public `flowpilot_new.py resume` plus returned `foreground_duty` remains
the only formal resume authority.  The exact rehydration target is the
deduplicated union of:

- roles that own current unresolved packet or Controller-wait obligations; and
- the immediate current foreground-duty recipient when that duty requires an
  addressable role.

PM is included only when a current PM decision is required.  Same-run role
slots that are idle, completed, superseded, or absent from the exact obligation
set remain continuity/audit context and are not opened, restored, replaced, or
waited on merely because they exist.  Prior-run ids, route history, chat
history, and fixed role-set topology are never positive target inputs.

The retained diagnostic router must project the same exact target set and
current-authority identities.  If it cannot, its result is diagnostic only and
cannot support current progress, resume success, or completion.  A missing
required target, an extra idle target, duplicate role, stale binding, or
foreign-run memory blocks with the current recovery command.

Alternative: rehydrate every same-run role slot to maximize apparent team
continuity.  Rejected because idle continuity is not a current obligation and
would restore fixed-role-set behavior through a different name.

### 11. Interrupted owners require descendant-zero cleanup

Every heavyweight launcher has one execution owner and one recorded process
tree identity.  On Windows, a current virtual-environment interpreter request
binds its base interpreter as the direct process owner while preserving the
requested virtual-environment identity; a short-lived launcher shim cannot
stand in for the real command owner.  After a normal real-owner exit, the
launcher permits one bounded fifteen-second settlement window for
already-recorded exact descendants to finish naturally.  A descendant that
survives that window, or any timeout,
cancellation, interruption, or supervisor failure, causes the owner to
invalidate the partial receipt, terminate or reconcile the exact full
descendant tree, and write terminal cleanup evidence showing descendant count
zero.  Survivors still make the owner fail even when cleanup succeeds.  Until
that evidence exists, the result is `cleanup-unconfirmed`, is not reusable,
and blocks another owner from starting the same heavy check.

Scheduled tasks, background resume scripts, and unattended retry loops are not
allowed to replace the explicit owner.  Progress, PID, stdout, or a parent
process exit alone never proves descendant cleanup.

Foreground startup and the newly opened Router daemon share the current
runtime JSON lock authority.  A transient Windows permission denial while
acquiring that exact lock is current writer contention and stays within the
existing bounded settlement budget.  Persistent denial becomes structured
`RouterLedgerWriteInProgress` and blocks; it does not authorize an alternate
write path, unlocked write, or second startup route.

The public `start` command allocates and persists one fresh bootstrap before
advancing it. A later writer-contention retry resumes that same bootstrap and
reattaches its exact live in-flight daemon; it never re-enters fresh-run
allocation. Completed folded-action evidence from pre-contention advancement
is carried into the terminal command receipt. Multiple live startup owners,
more than one allocated run, or lost completed-action evidence fail closed.

Alternative: accept the supervisor exit and start a new run immediately.
Rejected because surviving children can mutate shared evidence and invalidate
both executions.

### 12. One fingerprint and one ordered validation snapshot

Before broad validation, freeze the covered source, toolchain, test inventory,
dependencies, verification plan, and one covered-source fingerprint.  The
`all`, `formal-submit-adversarial`, and `release` supervisors record the same
fingerprint at start and end; every child record, proof artifact, and compiled
acceptance manifest binds that fingerprint and terminal exit.

After the final manifest is compiled, ContractExhaustion, current Cartesian,
MTA, acceptance TestMesh, and ModelMesh consume that exact manifest.
`final-confidence` runs only after those consumers pass; Meta and Capability
parents run afterward.  Topology build/check and installed-skill
sync/audit/self-check follow only after governed source and evidence are
stable.  OpenSpec strict validation is the final provider check.

Any covered input change invalidates only mapped owners and all dependent
receipts, but no consumer may mix fingerprints, choose the newest result,
infer equivalence from command text, or silently downgrade claim scope.

Alternative: let each check fingerprint its local inputs independently.
Rejected because locally current results can describe different source
snapshots while appearing jointly green.

### 13. Predecessor changes have explicit dispositions

This successor consumes earlier requirements and fixtures without allowing
their checked tasks or generated reports to remain independent release proof:

| Predecessor | Disposition in this successor |
| --- | --- |
| `harden-flowpilot-control-plane-ledger-hygiene` | Retain verified ledger behavior; its remaining KB/report work closes separately and its old coverage report is not successor proof. |
| `adopt-runtime-requested-role-bindings` | Merge requested-role requirements and negative cases; supersede its standalone resume-closure claim after this successor passes. |
| `harden-flowpilot-role-continuity-memory` | Retain current-run memory as conditional recovery input; reject any all-slot or fixed-role restoration interpretation. |
| `strengthen-flowpilot-reviewer-pm-challenge-chain` | Merge stage-specific semantic challenge and PM disposition behavior; retain zero-new-field boundary. |
| `reduce-flowpilot-contract-surface` | Retain compact Reviewer contract and deleted-field authority; `independent_challenge` stays forbidden. |
| `harden-flowpilot-fake-ai-review-window-coverage` and `harden-review-window-completeness-matrix` | Merge declared flows, fixtures, and stage coverage; supersede standalone broad evidence claims after same-fingerprint successor proof. |
| Earlier Cartesian, contract-exhaustion, formal-artifact, and AI-projection coverage changes | Retain requirements and pinned historical misses; supersede generated-cell, test-name, or abstract-green closure claims only after successor verification. |

No predecessor is rewritten or treated as failed merely because its evidence
boundary is narrower.  Archive or supersede status is allowed only after this
successor has current terminal evidence for the inherited obligation.

## Risks / Trade-offs

- [Risk] Removing body/private helpers exposes hidden consumers. -> Add red
  conflict tests first; unknown consumers fail closed and are repaired at the
  single owner.
- [Risk] Pairwise compression misses a higher-order defect. -> Pin historical
  misses, run named high-risk three-wise groups, deterministic fuzz, and
  observed-problem backfeed.
- [Risk] Proof artifacts become large or slow. -> Store compact aggregates and
  failing samples, stable shards, and hashes rather than millions of per-cell
  unittest records.
- [Risk] Two background workers still exceed Windows memory. -> Benchmark with
  one/two workers and keep the lower stable bound; timeouts remain failures.
- [Risk] Structured authority references become another competing contract. ->
  Reuse existing handoff/context reference fields, declare one normalized item
  shape, and reject prose, alias, or inferred fallback references.
- [Risk] Tightening resume loses useful role continuity. -> Keep idle same-run
  memory as audit/reuse context, but rehydrate only the exact current-obligation
  set and test inclusion plus exclusion.
- [Risk] Workstream structure is mistaken for mechanical semantic proof. ->
  Runtime checks only its current contract; Reviewer audits the real artifacts,
  evidence, delegation integration, and claim consistency.
- [Risk] An interrupted child survives its supervisor. -> Make descendant-zero
  cleanup a prerequisite for receipt reuse and the next heavy execution owner.
- [Risk] Old OpenSpec changes appear complete from checked tasks. -> Mark them
  with explicit retain/merge/supersede/archive-history dispositions and
  supersede only after this successor verifies.
- [Risk] Installation evidence becomes stale after version/docs changes. ->
  Run final topology and install sync/audit/check after all source and release
  metadata edits, then rerun only invalidated release gates.

## Migration Plan

1. Add failing authority/cardinality/current-source tests and make evidence
   reports distinguish generated from executed.
2. Normalize structured current-authority items inside existing
   handoff/context reference surfaces and delete every prose/old-run fallback.
3. Complete the envelope projection; switch checklist, fake AI, fake project,
   and current rehearsal to the single public path; delete alternate success
   surfaces.
4. Align public and diagnostic resume with the exact current-obligation target
   set and add idle/history/fixed-role known-bad cases.
5. Reconcile Reviewer prompts, fake AI, models, and tests with the existing
   workstream structure, semantic Reviewer ownership, compact result contract,
   and forbidden deleted field.
6. Add universe/oracle/id/equivalence definitions, descendant-zero cleanup
   evidence, and tiered execution shards.
7. Replace abstract-green TestMesh/MTA/ModelMesh evidence with same-fingerprint
   proof receipts and parent consumption.
8. Freeze one fingerprint; run focused checks, isolated background
   all/adversarial/release, manifest consumers, final-confidence, and
   Meta/Capability parents in order.  Repair failures at their owners and
   invalidate only mapped descendants.
9. Rebuild topology, sync the installed skill, audit digests, update release
   metadata to 0.12.0, synchronize the existing verification
   contract through its owning workflow, run `openspec validate
   restore-flowpilot-test-evidence-closure --type change --strict
   --no-interactive`, create one exact task-owned local Git commit, push the
   task branch, fast-forward the default branch, create the annotated tag and
   source-only GitHub Release, then verify all remote identities match.

Rollback is restoration of the pre-change working-tree state plus reinstall of
the previous repository-owned skill.  No old runtime input is accepted as a
compatibility fallback.

## Open Questions

None.  Actual shard counts and final budgets are derived from the first public-
path benchmark; if the measured budget cannot be met, TestMesh must repartition
the same required cells rather than dropping coverage.
