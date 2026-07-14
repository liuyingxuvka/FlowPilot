# DevelopmentProcessFlow Record

## Selected modes

- `plan_detailing`: compile the agreed discussion into OpenSpec obligations,
  model owners, implementation steps, validation commands and repair branches.
- `agent_workflow`: rehearse PM, Worker, research/evidence Worker, Reviewer and
  FlowGuard Operator handoffs against the single current packet/result path.
- `execution_freshness`: bind focused, parent, background, install and final
  claims to source fingerprints and final artifacts.

## Ordered process

1. Audit current owners, peer writes, active runs, real FlowGuard and suite
   visibility.
2. Establish OpenSpec and FlowGuard behavior/field/reduction obligations.
3. Execute the two focused models and inspect counterexamples before changing
   runtime or prompts.
4. Change existing core/prompt/card owners without adding a second path.
5. Add canonical fake-AI profiles and focused ordinary tests.
6. Extend existing MTA, TestMesh, ModelMesh and parent models.
7. Run focused checks, backfeed every miss, then run foreground tiers.
8. Freeze covered source; run isolated all, formal-submit-adversarial, and
   release backgrounds; compile TestMesh; run strict parent consumers; then
   run repository final-confidence, Meta, and Capability with complete final
   artifacts. Active-run terminal return remains a separate run-local gate.
9. Rebuild topology/SkillGuard/docs/version, then serially sync and audit the
   local installation.
10. Verify and archive OpenSpec, audit every requirement, stage only owned
    changes, create a local commit, and perform KB postflight.

## Failure and rework branches

- A model counterexample changes the design/model before production edits.
- During repair, run only the directly affected tests/models and their owning
  parents. Collect all failures from a broad run before making a repair batch;
  do not restart the broad run after each individual fix.
- Run a new all-tier regression only after the affected scope is green and the
  covered source is frozen. A further all-tier run is required only when the
  frozen source changes again.
- A semantic fake-AI miss is backfed to the owning profile, Reviewer oracle,
  focused test, MTA row and parent receipt.
- A covered-source change invalidates all earlier parent/background proof.
- A final-confidence/TestMesh/MTA dependency cycle is rejected; the terminal
  consumer cannot be counted as its own upstream evidence.
- Running, progress-only, path-only, missing-exit, stale, timed-out, skipped or
  failed artifacts remain non-passing.
- A peer write is inspected and integrated or kept untouched; it is never
  silently overwritten.
- Install parity is checked only after serial source-to-install sync; no dirty
  peer resync and no newest-run fallback are allowed.

## Current preflight receipts

- FlowGuard schema: `1.0`.
- Installed/project/rendered FlowGuard package version: `0.55.0`.
- Canonical 17-member FlowGuard skill suite: `pass`.
- Project audit: `pass`, missing rule ids: none.
- Predecessor background parent: orphaned/incomplete and diagnostic-only;
  final source-frozen replacement required.
- Source-frozen diagnostic on 2026-07-10 was stopped at 92/164 after three
  failures reproduced and the persistent-writer quiet-period defect made the
  remaining old-source run non-authoritative; all final evidence will be rerun
  from the repaired frozen source.
- The `final15` all/adversarial/release roots passed and remained current for
  source fingerprint
  `9142ec014e60a263e758bc23b49d8fb23b4e340676fb5e98311bef767b126ba8`,
  but the downstream strict Acceptance TestMesh correctly exposed missing
  FlowGuard 0.55 final-receipt identity fields. The repair changed covered
  source, so every `final15` root is now diagnostic-only and `final16` is the
  required source-frozen replacement.

## Model-miss backpropagation (2026-07-12)

- Miss type: `evidence_overclaimed` at the TestMesh final-receipt adapter.
- Previous claim: passing all/adversarial/release tier artifacts were treated
  as sufficient input for the strict TestMesh consumer.
- Observed failure: strict release TestMesh produced the built-in
  `background_incomplete` family plus missing run id, terminal status, result
  fingerprint, covered obligations, artifact version and verifier version.
- Supported root cause: the evidence compiler projected proof artifacts and
  counts but did not project the FlowGuard 0.55 `TestSuiteEvidence` final
  receipt identity fields or exact receipt coverage set.
- Generalized case: one six-axis missing-field family now runs as six negative
  subtests; all compiled routine/release rows derive their receipt identity
  from concrete proof fingerprints, and the release tier now owns the complete
  Acceptance TestMesh contract module.
- Owner code contract: `compile_flowpilot_acceptance_testmesh_evidence.py`,
  `flowpilot_evidence_truth.py`, `flowpilot_acceptance_testmesh_model.py` and
  `run_flowpilot_acceptance_testmesh_checks.py` form one current evidence path.
- Current targeted closure: 21 Acceptance TestMesh tests/93 subtests, 20 direct
  parent tests/6 subtests, 34 tier tests/504 subtests, TestTier FlowGuard, and
  the Behavior Commitment Ledger pass. Broad confidence remains blocked until
  the `final16` roots and strict parents pass.

## Final source-frozen closure (2026-07-12)

- Covered source fingerprint:
  `971bda2044bdaf263bbf78e57c35f2e27ed587e5cfc31c28ce3c5ecaaf27c954`.
- `complete-workstream-all-final16`: 166/166 child commands passed, exit 0,
  no proof reuse, and identical start/end/current source fingerprints.
- `complete-workstream-adversarial-final16`: 6/6 child commands passed, exit
  0, no proof reuse, and identical start/end/current source fingerprints.
- `complete-workstream-release-final16`: 6/6 child commands passed, exit 0,
  no proof reuse, and identical start/end/current source fingerprints. This
  tier includes the complete Acceptance TestMesh contract module.
- The v3 final evidence manifest records 179 selected/executed child commands,
  concrete artifact fingerprints, final receipt identity, exact covered
  obligations, and FlowGuard 0.55 verifier identity.
- ContractExhaustionMesh, the current-contract Cartesian matrix,
  Model-Test Alignment, Acceptance TestMesh, ModelMesh, and the repository
  final-confidence terminal consumer all passed. Acceptance TestMesh reported
  zero findings.
- Exact `run_meta_checks` and `run_capability_checks` background artifacts are
  complete, exit 0, current for the same source fingerprint, and not reused.
- The Python editable binding was found at another 0.55.0 FlowGuard checkout.
  Its 125 package files had the same aggregate SHA-256 as the required
  `FlowGuard_20260427` checkout, so prior evidence remained behaviorally
  current. The editable install was rebound to `FlowGuard_20260427`, then the
  project audit, Behavior Commitment Ledger, Acceptance TestMesh, Meta parent,
  and Capability parent were rerun as the affected scope and passed.
- FlowPilot source/install digests match, installed runtime self-check passes,
  full install check passes 907 checks, SkillGuard is `deep-pass`, public
  release has zero errors, and topology is current.

## DevelopmentProcessFlow post-change scan (refreshed 2026-07-14)

| Signal | Disposition | Owning route |
|---|---|---|
| `final15` and `final16` receipts | Diagnostic-only after governed prompt, contract, model, test, and process inputs changed; excluded from final claims and never resumed. | TestMesh / Model Miss Review |
| Final receipt identity gap | Closed through one v3 compiler path plus six missing-field negative subtests and a release-owned full TestMesh module. | Model-Test Alignment / TestMesh |
| Mandatory material scan/sufficiency path | Deleted from the positive current path; old names remain only in negative tests, forbidden/deleted inventories, historical labels, or archived specs. | Architecture Reduction / FieldLifecycleMesh |
| Role-local FlowGuard | Retained as advisory self-modeling only; independent Reviewer and formal FlowGuard gates remain authoritative. | Behavior Commitment Ledger / Primary Path Authority |
| Split or reduction pressure | No new report family, plan ledger, controller plan authority, material result family, or compatibility path was introduced; existing packet/result/gate owners remain sufficient. | Architecture Reduction / StructureMesh |
| SkillGuard current-contract projection | The V2 source/compiled/manifest trio, exact four-route/seven-check native bindings, focused FlowGuard model, maintenance-field lifecycle, MTA family, ModelMesh child receipt, source-freshness boundary, and read-only final receipt consumer are current. Missing, extra, duplicate, defaulted, or fallback bindings block global selection. Contract-depth mapping remains explicitly weaker than execution-depth evidence. | SkillGuard / FieldLifecycleMesh / Model-Test Alignment / ModelMesh |
| Parent-model freshness | Meta and Capability thin parents were rerun once after the new SkillGuard child receipt changed their inputs. Routine confidence is current; full-parent proof remains visibly pending for the single frozen release execution. | ModelMesh / TestMesh |
| UI route | Not affected by this prompt/runtime/process change; no UI completion claim is made. | Explicitly skipped: UI Flow Structure |
| Peer and local-only files | Root `.agents/`, `.skillguard/`, browser artifacts, temporary evidence, reports, promotion kit, and the peer `restore-flowpilot-test-evidence-closure` change remain outside this change's staging boundary. | DevelopmentProcessFlow / Git integration |
| Open obligations after scan | Strict local OpenSpec verification, scoped staging/commit, archive, and KB postflight only. | OpenSpec / DevelopmentProcessFlow / predictive KB |

## Verification-contract execution repair (2026-07-12)

- Two `openspec verify` attempts reached outer 10-minute and 30-minute tool
  budgets without producing a new report. Inspection proved that both detached
  OpenSpec child chains survived their outer timeout and concurrently executed
  `scripts/run_test_tier.py --tier fast --json` in the foreground.
- The two agent-owned orphan trees and their 12 descendants were identified by
  exact command line and terminated. No unrelated process was included.
- `check.tier.focused` had duplicated 70 foreground fast commands even though
  the source-frozen `all` parent already contained and had verified those
  children. It now verifies the authoritative `all-final16` background receipt
  instead of re-executing the fast tier.
- This is a verification-process repair only. It does not alter FlowPilot
  runtime behavior or the frozen product source fingerprint. The replacement
  command was run directly and verified the final16 parent before the contract
  was updated.

## Current-contract toolchain and single-owner repair (2026-07-14)

- Later governed FlowPilot prompt, test, contract, and process changes made the
  `final16` roots historical evidence. They remain useful diagnostics but are
  not resumable or admissible for final closure. The next unique frozen roots
  are `complete-workstream-*-final17` and
  `complete-workstream-final17`; none existed when this identity was selected.
- The repaired external SkillGuard tool no longer supports FlowPilot's former
  private V1 regeneration path. FlowPilot now owns one current declarative V2
  trio under `skills/flowpilot/.skillguard/`, uses the public compiler and
  checkers, and explicitly denies a parallel SkillGuard runtime route.
- A focused real-FlowGuard projection now covers the existing opt-in, PM route
  plan, complete substantive-role workstream, and independent closure stages.
  Its eleven known-bad cases, monotonic progress, four-route/ten-obligation
  conformance, final17 read-only receipt binding, MTA plan, fast-tier owner, and
  ModelMesh child receipt are current in narrow validation. This projection
  does not execute FlowPilot work or license an execution-depth claim.
- The first parity check correctly failed because the repaired external
  compiler produced a different deterministic generated contract. A later
  upstream bug-fix completion advanced that compiler once more, and parity
  correctly failed again without any FlowPilot declaration change. On each
  occasion only the two repository-local generated V2 files were rebuilt.
  The final public parity/depth check passed with contract hash
  `46B14F9741CD6B7FAF8D06503AE4A03B59CF67885FCD2AEEC6D8E8DECA45A2B5`
  and manifest hash
  `8C1801D2FFF737EF44091B9E63D2845C4E5C933BBBB5C827E5D067347D8EF95D`.
- The release tier previously ran Meta and Capability full parents directly
  while the final contract also expected separately produced stable
  `run_meta_checks` and `run_capability_checks` logs. The release nodes are now
  the sole execution owners and write those stable receipts through the
  existing background helper; OpenSpec's later checks use `--verify` and never
  relaunch them. This removes one complete duplicate full-parent execution.
- No final17 parent, full OpenSpec verification, install sync, public-release
  audit, archive, or Git closure is claimed by this section. Those remain
  pending until the current source/tool/install identities are frozen.

## Global-router model-miss backpropagation (2026-07-14)

- Affected plane: `development_process`. The existing commitment is
  `commit.release_claims_require_current_evidence`, owned by
  DevelopmentProcessFlow release closure. The related FlowPilot opt-in route
  is typed `agent_operation` context; it is not a second owner.
- Primary model owner: `flowpilot_skillguard_current_contract`.
- Error signature: after source-to-install sync and global-router refresh,
  `resolve-global-skill --route-hint flowpilot` correctly blocked because the
  FlowPilot registry item had no declared native route/check bindings.
- Previous claim: the focused contract model and public compiler parity were
  current. No final17, release, archive, or execution-depth claim had been
  made; the production-facing global selection smoke caught the miss before
  final closure.
- Miss type: `boundary_missing`. The supported cause was two empty source
  arrays, `native_route_bindings` and `native_check_bindings`, in an otherwise
  native-integrated contract.
- `would_have_failed_if`: the prior model/refinement had required the exact
  existing four route ids and seven declared check ids, and the focused gate
  had included a production-facing global-route selection receipt.
- Generalized cases: missing/extra/duplicate route binding, missing/extra/
  duplicate check binding, missing source/evidence path, non-required binding,
  missing-field default, and fallback selection all fail closed.
- Owner code contract: `skills/flowpilot/.skillguard/contract-source.json`,
  `simulations/flowpilot_skillguard_contract_model.py`, and
  `simulations/run_flowpilot_skillguard_contract_checks.py`. The existing
  FieldLifecycleMesh now records the single writer, compiler/router/model
  readers, generated/global projections, exact-set source, and blocked
  terminal disposition for both maintenance fields.
- Closure evidence: eleven canonical model bad cases; exact native-binding
  negative tests; 2/2 current maintenance-field contracts; 158/158 critical
  field-code bindings; public V2 compiler parity; MTA and ModelMesh projection;
  and current global registry, prompt, and FlowPilot route resolution.
- Old-field disposition: no alias, compatibility translator, prose guess,
  default, or alternate route was added. Empty binding arrays are invalid.
- Analogous scan: both route and check binding families were checked as exact
  sets. Other installed skills remain under their own migration owners and
  are outside this FlowPilot repair; their blocked status is not rewritten.
- Claim boundary: this closes FlowPilot's global selection contract only. It
  does not prove arbitrary installed skills, final17 execution, release,
  archive, or future AI semantic quality.

## Frozen FlowPilot final18 closure (2026-07-14)

- The public dependency URL repair was the last governed source edit, so the
  earlier `final17` identity was retired without reuse. The final frozen source
  fingerprint is
  `10f38ac754a614ed5508ad30bc16b270a6942087db79b156094f65184c7b4389`.
- Exactly one serial owner ran each fresh parent root: `all` 167/167,
  `formal-submit-adversarial` 6/6, and `release` 6/6. All three roots began and
  ended on the same fingerprint, reported `proof_reused=false`, and passed
  read-only receipt verification.
- The final TestMesh manifest accounts for 179 selected, executed, and passed
  child commands. Contract exhaustion, current Cartesian, Model-Test
  Alignment, Acceptance TestMesh, and ModelMesh consumed that manifest and
  passed without rerunning the parent commands.
- The acyclic `final-confidence` terminal consumer ran once, passed 1/1, and
  left zero matching Python descendants. Meta and Capability full parents
  passed once through their release owner and produced current stable logs at
  `tmp/flowguard_background/run_meta_checks.*` and
  `tmp/flowguard_background/run_capability_checks.*`.
- FlowPilot source/install parity, installed runtime self-check, local install
  audit, topology, V2 SkillGuard projection, privacy/URL/package boundary, and
  public-release checks are current. No external FlowGuard, OpenSpec, or
  SkillGuard repository was modified by this closure sequence.
- Claim boundary: the evidence proves this frozen FlowPilot repository and its
  installed projection satisfy the declared finite contract. It does not
  prove future arbitrary AI quality, optional UI-companion installation, or
  unrelated installed skills.

## Final-contract duplicate-execution repair (2026-07-14)

- The first strict full contract attempt executed all 47 declared checks even
  though the `all`, adversarial, release, Meta, Capability, and final-confidence
  owners already held current immutable receipts. It finished 43 passed and 4
  failed after 41 minutes; the report is invalid as completion evidence.
- The four failures shared a contract-shape cause rather than a FlowPilot
  product regression: a frozen snapshot reran a live-run daemon projection,
  rewrote generated model outputs, made the generated topology stale, and ran
  a Git-dependent public-release check inside a snapshot without `.git`.
  Public validation also invoked the fast smoke path that rewrote the frozen
  topology input, so the run correctly failed closed.
- The repaired contract keeps the existing 47 requirement-facing check ids but
  makes 32 of them pure receipt projections from the current all, adversarial,
  or release owner. Fifteen commands remain: four read-only parent receipt
  verifiers, two stable Meta/Capability receipt verifiers, six strict evidence
  consumers, project/topology read-only checks, and strict OpenSpec validation.
  Dependency edges enforce parent receipts before TestMesh compilation,
  strict consumers before final confidence, and final evidence before strict
  OpenSpec validation.
- A no-run audit reported 15 command owners, 32 receipt projections, zero
  execution, zero blocking issues, and zero dependency cycles. Only the
  affected topology build/check and install check were rerun locally; topology
  passed with zero findings and install passed 915/915. No `--resume`, full
  parent rerun, Scheduled Task, background retry, or external repository write
  was used.
