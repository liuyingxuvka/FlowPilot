## Context

FlowPilot is a mature FlowGuard-modeled Codex skill with a current-contract
runtime. The repository currently imports FlowGuard `0.53.0`, but its managed
project adoption record still declares `0.52.6`. The latest scan also found
routine validation green while Capability release confidence requires a fresh
layered full proof.

FlowGuard `0.53.0` adds Behavior Commitment Ledger and Primary Path Authority
routes. These match FlowPilot's maintenance rules: one current structured path,
no fallback, no compatibility aliases, no old-field translation, no UI surface,
and no runtime semantic matching. The upgrade must therefore shrink or bind
existing behavior rather than introduce parallel paths.

The unfinished `enforce-pm-visible-role-summaries` OpenSpec change is the
highest-risk local field surface. It introduced `pm_visible_summary`,
`recent_role_report_summary`, `authorized_result_reads`, and `open-result`
intent. Those surfaces may be valid, but they must be re-reviewed under
FieldLifecycleMesh, ContractExhaustionMesh, PPA, and model-test alignment
before the change can be treated as complete.

## Goals / Non-Goals

**Goals:**

- Upgrade FlowPilot's managed FlowGuard project record to the installed
  FlowGuard `0.53.0` toolchain through the official project-upgrade path.
- Add repository-owned evidence that FlowPilot broad no-fallback claims are
  represented by behavior commitments, primary path authority, canonical bad
  cases, test mesh shards, and model-test alignment obligations.
- Decide whether the unfinished PM-visible summary / authorized-read surfaces
  remain canonical current-contract fields or are shrunk/rejected.
- Refresh release-sensitive evidence after the project/tooling/model/test
  surfaces change.
- Synchronize the installed FlowPilot skill with the repository and commit the
  completed local version.

**Non-Goals:**

- No user-interface work, Cockpit work, publication, deployment, push, tag, or
  GitHub release.
- No runtime semantic matcher for user intent, review quality, or core
  deliverable comparison.
- No compatibility shim, old field alias, legacy parser, missing-field
  default, fallback result acceptance, or automatic historical-artifact
  promotion.
- No new ledger/table/role/state family unless FieldLifecycleMesh and PPA prove
  an existing packet/result/gate/blocker/route surface cannot express the
  repair.

## Decisions

### Decision: Use FlowGuard Project Upgrade Before Trusting Evidence

Run `python -m flowguard project-upgrade --root .` before broad claims. The
upgrade report is not itself validation; it only makes the project record and
deterministic artifact upgrade scan current enough for downstream evidence to
be trusted.

Alternative considered: record-only adoption update. Rejected because the
installed tool is newer than the project record and the repository rules require
artifact/model/test upgrade scanning unless intentionally scoped out.

### Decision: Model No-Fallback As Commitments Plus PPA

Represent externally verifiable FlowPilot behaviors as Behavior Commitment
Ledger rows and route path-sensitive behaviors through Primary Path Authority.
PPA must name the primary success path and prove that alternate/fallback paths
do not produce success after primary failure.

Alternative considered: add more runtime checks directly to each observed
failure. Rejected because that recreates parallel compatibility surfaces and
misses broad no-fallback evidence.

### Decision: Re-Review Field-Heavy Surfaces Before Completion

Treat `pm_visible_summary`, `recent_role_report_summary`,
`authorized_result_reads`, and `open-result` as discovered field/path surfaces.
They are not automatically removed, but they cannot be finalized until each has
an owner, reader/writer map, behavior projection, old-field disposition,
negative cases, and downstream evidence.

Alternative considered: complete the existing OpenSpec change by marking its
last task done. Rejected because the user has since tightened the rule against
unnecessary fields and alternate paths.

### Decision: Keep Runtime Mechanical

Runtime/router changes may validate schema, current run, packet/result ids,
lease/currentness, path/hash presence, required opened-body receipt presence,
and unsupported field/path rejection. PM, Reviewer, and FlowGuard continue to
own semantic quality, process review, and model/state review.

Alternative considered: runtime semantic detection of downgraded objectives or
summary quality. Rejected because runtime cannot safely own semantic review.

### Decision: Treat Release Evidence As Separate From Routine Green

Routine checks may stay fast, but release confidence requires current layered
full proof and release TestMesh suites. A green thin parent or topology check
does not close stale full-regression proof or deferred release suites.

Alternative considered: rely on the latest routine model/test alignment pass.
Rejected because Capability reported stale full proof after the previous scan.

## Risks / Trade-offs

- [Risk] Project upgrade changes managed records and may reveal deterministic
  artifact upgrades. -> Mitigation: inspect the upgrade report, keep changes
  scoped, rerun affected checks, and do not treat the upgrade report as pass
  evidence.
- [Risk] BCL/PPA adds conceptual evidence without real tests. -> Mitigation:
  bind commitments to ContractExhaustionMesh, TestMesh, and Model-Test
  Alignment rows before claiming closure.
- [Risk] FieldLifecycleMesh can expand the task if every metadata field is
  modeled at high level. -> Mitigation: inventory leaf rows but project only
  behavior-bearing fields.
- [Risk] Release regressions may be long. -> Mitigation: use the repository
  background artifact contract and inspect exit/status/proof reuse artifacts.
- [Risk] Parallel agents may add unrelated work. -> Mitigation: preserve
  untracked or unrelated changes and stage only this change's files.

## Migration Plan

1. Run project-upgrade and project-audit with FlowGuard `0.53.0`.
2. Add or update FlowPilot model/test surfaces for BCL/PPA, field lifecycle,
   and release evidence freshness.
3. Reconcile the unfinished PM-visible summary change by shrinking or proving
   each field/path.
4. Run focused model/tests and then release-sensitive full proofs.
5. Rebuild/check topology, sync installed FlowPilot, audit install freshness,
   and commit the local version.

Rollback is ordinary git revert before publication. Runtime data migration is
not expected because no compatibility or schema migration is introduced unless
the field review explicitly proves one is current-contract required.
