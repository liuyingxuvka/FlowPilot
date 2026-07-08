## Why

FlowGuard is now installed at `0.53.0`, while FlowPilot's project adoption
record still declares `0.52.6`; release confidence is also stale for the
Capability layered full proof. FlowPilot needs one current maintenance pass
that absorbs the upgraded FlowGuard route surface without adding fallback,
compatibility, UI, or unnecessary runtime fields.

## What Changes

- Refresh FlowPilot's FlowGuard project adoption record through the explicit
  project-upgrade path and keep the artifact/model/test upgrade scan visible.
- Add FlowGuard 0.53 Behavior Commitment Ledger and Primary Path Authority
  coverage to FlowPilot maintenance so broad no-fallback claims enumerate
  external commitments, assign one primary owner, and reject alternate success
  after primary-path failure.
- Re-review the unfinished `enforce-pm-visible-role-summaries` change under
  current-contract field discipline before completing it: keep only fields that
  have one owner, one commit point, one terminal disposition, and negative
  coverage; otherwise shrink or reject the field/path surface.
- Refresh model-test alignment, ContractExhaustionMesh, TestMesh, topology,
  meta/capability release evidence, install sync, and local git evidence after
  the maintenance changes.
- Keep release-only obligations visible when they are not run and do not make
  a public release, tag, push, or deployment claim in this change.

## Capabilities

### New Capabilities

- `flowguard-053-project-adoption`: FlowPilot adoption records, logs, and
  validation evidence must match the installed FlowGuard 0.53 check engine
  before broad confidence.
- `flowpilot-primary-path-authority`: FlowPilot maintenance must represent
  no-fallback behavior commitments with one primary path authority and negative
  evidence for alternate success after primary failure.
- `flowpilot-field-surface-review`: Field-bearing runtime, prompt, packet,
  result, and OpenSpec changes must pass FieldLifecycleMesh-style ownership and
  old-field disposition before completion.

### Modified Capabilities

- `repository-maintenance-guardrails`: Maintenance completion must consume the
  project upgrade, BCL/PPA, field lifecycle, release evidence, install sync,
  and local git gates.
- `flowguard-boundary-test-alignment`: Alignment must bind BCL/PPA and field
  lifecycle obligations to model, owner code contracts, and ordinary tests.
- `tiered-flowpilot-test-validation`: Release-only suites and full-regression
  proof refresh must be current before release confidence is claimed.
- `flowguard-model-hierarchy`: Meta/Capability parent release confidence must
  distinguish fresh layered full proof from stale input fingerprints.
- `flowpilot-packet-review-flow`: Packet and result review paths must not
  accept new PM-visible summary or authorized-read fields unless the current
  field lifecycle review keeps them as canonical.
- `role-output-transaction-boundaries`: Formal role output fields must remain
  current-contract surfaces with no fallback aliases, generated prose
  substitutes, or compatibility readers.
- `blocker-repair-policy`: PM repair guidance must use existing blocker,
  packet, result, and repair paths unless a field lifecycle review proves a
  new field is necessary.

## Impact

- FlowGuard project adoption artifacts: `.flowguard/project.toml`,
  `.flowguard/adoption_log.jsonl`, `docs/flowguard_adoption_log.md`, and
  `AGENTS.md` if the managed record changes.
- OpenSpec artifacts for this maintenance change and possible reconciliation
  of `openspec/changes/enforce-pm-visible-role-summaries`.
- FlowPilot model and coverage surfaces under `simulations/`, especially model
  test alignment, synthetic coverage, ContractExhaustionMesh, TestMesh,
  meta/capability parent checks, and topology.
- Runtime contract and prompt-card sources only where necessary to preserve the
  current single path; no UI, no fallback, no compatibility shims, and no
  runtime semantic matching.
- Install and local repository evidence: source-owned skill sync, install
  audit/checks, focused tests, background long-check artifacts, and local git
  commit.
