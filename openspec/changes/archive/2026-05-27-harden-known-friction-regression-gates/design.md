## Context

The same FlowPilot control-plane failure class has appeared across several
completed changes: worker self-check failures, PM repair transaction recovery,
stale material generation projection, ACK clearance, daemon/state consistency,
and lifecycle stop. The previous fixes improved local boundaries, but some
green evidence was scoped: live audit or projection checks were skipped, daemon
checks timed out, or tests used direct Router calls that reloaded clean state
instead of exercising daemon-visible interleavings.

The current repair must therefore change both behavior and evidence policy. A
known historical failure is not closed until it has a replay package, a
FlowGuard obligation, ordinary tests, daemon/runtime evidence where relevant,
and a completion claim that names skipped or scoped checks.

## Goals / Non-Goals

**Goals:**

- Make the six accepted friction surfaces hard regression gates.
- Preserve existing FlowPilot architecture and reuse the current Router,
  daemon, packet, role-output, lifecycle, and model-test alignment surfaces.
- Fix PM repair decision finalization so post-decision waits are executable in
  the same state version visible to the daemon.
- Fix user-visible status and ACK wording so receipts, completion, and current
  blockers cannot be confused.
- Add realistic worker-output fixtures and historical bad-case replays.
- Require final background artifacts and non-skipped live/daemon evidence
  before claiming full confidence.
- Sync the repository-owned installed skill only after source tests pass.

**Non-Goals:**

- Do not redesign FlowPilot startup, role authority, or packet runtime.
- Do not add a parallel workflow outside Router/PM/control-blocker ownership.
- Do not restart or continue the stopped historical run.
- Do not push, publish, tag, deploy, or archive unless separately requested.

## Decisions

### Historical bad cases become first-class replay rows

Each friction surface gets a named replay row with source class, triggering
state, required model obligation, runtime test, and evidence boundary. This is
preferable to only adding ad hoc tests because it prevents future changes from
dropping a known-bad class while still reporting broad confidence.

### PM repair finalization uses one post-decision state boundary

The Router must not write active blocker allowed events that require
`pm_control_blocker_repair_decision_recorded` while the daemon-visible state can
still observe that flag as false. The repair decision handler and event
finalizer should share a single post-decision state boundary before blocker
indexes, repair transactions, and next-action projection are treated as
current.

Alternative considered: relax the required flag on recheck events. Rejected
because that weakens the invariant and would allow recheck events before a PM
repair decision is actually recorded.

### Packet reissue resumes material work instead of projecting stale PM wait

A valid `packet_reissue` repair should leave the system in a material repair
continuation state. The next user-visible action may be an executable wait only
when the producer exists and the wait is current-state executable; otherwise
Router should relay or prepare the fresh packet work.

### Status projection is tested as behavior, not decoration

Current status and action summaries are part of the control plane. Tests must
assert that resolved ACKs, committed PM decisions, and generation-scoped
material repair are reflected in user-visible status without stale wording.

### Stop is a lifecycle reconciliation boundary

Controlled stop must update current-run lifecycle facts, daemon status,
heartbeat/manual-resume behavior, pending Controller actions, and role
continuation authority together. A stopped run should not still look active via
`.flowpilot/current.json` or resume evidence.

### Background checks are evidence only after final artifacts exist

Long checks may run in the background, but completion requires exit artifacts,
stdout/stderr/combined paths, metadata, completion status, and proof-reuse
classification. `ok: true` with skipped live audit, model-only conformance, or
timeout notes is scoped evidence, not full pass evidence.

## Risks / Trade-offs

- [Risk] Broader regression gates can slow iteration. -> Mitigation: keep
  focused tests fast and run heavyweight Meta/Capability checks in the stable
  background artifact contract.
- [Risk] Repair finalization changes may affect existing blocker tests. ->
  Mitigation: add known-bad tests first, keep behavior scoped to the
  post-decision repair transaction boundary, and rerun affected router child
  suites.
- [Risk] Historical replay fixtures may become too synthetic. -> Mitigation:
  include exact observed live-run fields where available and test through real
  Router/role-output/status/lifecycle surfaces.
- [Risk] Install sync could race validation. -> Mitigation: serialize
  `install_flowpilot.py --sync-repo-owned`, install audit, and install check
  after source validation, never in parallel.
