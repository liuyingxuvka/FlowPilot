## Context

PM package result disposition has two identities in practice:

- semantic package identity: router event, batch id, packet ids, and packet
  generation id;
- body authority: the file-backed package disposition body and its body hash.

Earlier fixes correctly made `body_hash` conflict evidence rather than part of
the semantic dedupe key. The remaining gap is the replay source. A durable
role-output row can be older than the current canonical disposition artifact
when foreground direct submission and daemon replay interleave. In that branch,
the stale row is not a valid fresh PM disposition, but treating it as a fatal
new conflict crashes the daemon and can leave split-brain authority.

## Model

Represent the corrected flow as:

`Role-output replay x Canonical package state -> Set(Reconciliation outcome x Canonical package state)`

Important state dimensions:

- replay source: direct event intake, role-output ledger replay, daemon tick;
- canonical package state: no package, package with same body, package with
  different newer body, repair-owned conflict, terminal quarantine;
- authority source: current package artifact, external-event idempotency ledger,
  active repair/blocker ownership;
- save freshness: current run state, stale daemon state, foreground-updated
  state on disk.

Safe outcomes:

- same body replay is idempotent;
- direct different-body intake remains a hard conflict;
- role-output replay of an older different body is quarantined when a newer
  canonical package artifact already owns the semantic identity;
- daemon remains live and keeps the current wait/progress surface visible;
- stale save merges preserve the newer canonical package body and matching
  idempotency fact.

Forbidden outcomes:

- daemon enters `daemon_error` because stale role-output replay sees an older
  unowned package body;
- stale replay appends the older package event after the newer body;
- stale replay overwrites the canonical package artifact or idempotency body;
- tests claim full closure while only covering repair-owned replay.

## Implementation Approach

1. Capture this branch in OpenSpec before code edits.
2. Extend FlowGuard event-idempotency and control-plane friction models with a
   foreground/daemon interleaving branch.
3. Add a focused historical regression test that commits the newer package
   body first, then replays the older role-output row through daemon
   reconciliation.
4. Teach role-output ledger reconciliation to detect stale unowned
   package-disposition replay against the current canonical package artifact.
5. Record stale replay as explicit quarantine/audit evidence while preserving
   the hard direct conflict rule.
6. Add model-test alignment evidence so the branch cannot disappear behind
   green model-only checks again.
7. Run focused tests, model checks, background Meta/Capability regressions,
   install sync, and final OpenSpec validation.

## Validation

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- Strict OpenSpec validation for this change.
- Focused package-disposition role-output reconciliation tests.
- Event-idempotency FlowGuard checks.
- Control-plane friction checks and known-friction matrix checks.
- Model-test alignment checks for the new obligation and evidence.
- Background `run_meta_checks` and `run_capability_checks` with final artifact
  inspection.
- Repo-owned FlowPilot install sync plus install freshness checks.
