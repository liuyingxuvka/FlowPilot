## Context

The new black-box FlowPilot runtime intentionally uses a small current-run
ledger, dynamic responsibility leases, lifecycle guard, and foreground duty
instead of the old persistent Router daemon and fixed-role monitor. Earlier
changes already added wait patrol, progress-preserved waits, liveness-check
thresholds, and assignment-race repair.

The remaining failure class is narrower:

- user stop/cancel can stop the conversation or subagents without writing a
  terminal lifecycle fact into the new runtime ledger;
- old progress can keep a lease looking healthy even after the host reports
  `not_found`, `cancelled`, or `timeout_unknown`;
- mechanical evidence can exist on disk after a runner completed, but the
  formal result envelope can still be absent, leaving the foreground duty in an
  endless result wait.

The fix should borrow old Router contracts but keep new-runtime authority in
the current ledger.

## Goals / Non-Goals

**Goals:**

- Add durable user stop/cancel terminal fences to the new runtime.
- Add a current-run host-liveness report command that records machine-readable
  lease liveness separately from progress prose.
- Make fresh host failure/no-output evidence override stale progress when
  choosing wait recovery.
- Detect and expose orphan mechanical evidence for FlowGuard/mechanical packets
  before the runtime keeps waiting or replaces the lease.
- Prove the same-class miss through FlowGuard, focused unit tests, and public
  fake AI rehearsal.
- Sync the installed local `flowpilot` skill and commit the scoped local git
  change after validation.

**Non-Goals:**

- Do not restore the old Router daemon, Controller action ledger, old monitor
  UI, or fixed six-agent topology as new-runtime authority.
- Do not read sealed packet or result bodies for liveness, stop, or orphan
  evidence classification.
- Do not treat progress, host liveness, runner exit code, or orphan evidence as
  packet completion by itself.
- Do not change unrelated validation/PM-gate behavior owned by the parallel
  `auto-close-after-system-validation` change.

## Decisions

### Decision: Stop/cancel is a terminal lifecycle fence, not completion

`flowpilot_new.py stop` and `cancel` will call a small runtime helper that
marks the ledger terminal, closes active leases, marks open/assigned packets as
stopped or cancelled, refreshes lifecycle guard/foreground duty, and updates
the current pointer. Final preflight should allow the foreground Controller to
exit only because the run is terminal-stopped/cancelled, not because the user
request was completed.

Alternative considered: close only local subagents. That reproduces the
observed mismatch where `.flowpilot/current.json` and the run ledger remain
`running`.

### Decision: Host liveness is a separate signal from progress

Add `host-liveness` as the public command for current host observations. It
will store `liveness_status`, `liveness_checked_at`, and a compact
`host_liveness_history` row on the active lease. `progress` remains available
for `still_working`, but a newer explicit liveness failure such as
`not_found`, `cancelled`, `timeout_unknown`, `completed_without_result`, or
`no_output` wins over older progress.

Alternative considered: keep overloading `progress --status`. That works for
tests but blurs "still working" with host addressability and makes live-host
bridging hard to audit.

### Decision: Orphan evidence creates a recovery duty, not success

For mechanical FlowGuard packets, the guard will inspect metadata-only
runner artifacts such as `evidence/flowguard/<packet_id>/runner_summary.json`.
If all recorded runner commands exited successfully but the packet has no
accepted result and no result body/envelope, the guard records
`orphan_evidence_detected` and returns a `recover_or_reissue` foreground duty.
The recovery may instruct the holder or replacement to submit a formal result
from existing evidence, but the evidence alone does not complete the packet.

Alternative considered: auto-accept successful runner summaries. That would
violate the packet/result envelope contract and hide missing handoff bugs.

### Decision: Keep evidence detection narrow and metadata-only

The first implementation will handle FlowGuard/mechanical evidence under the
new run root using known runner summary metadata. It will not scan arbitrary
directories or infer semantic quality from logs. This keeps the repair small
and prevents accidental body reads.

Alternative considered: broad orphan artifact sweeps. That belongs in a later
maintenance audit, not this hot path.

## Risks / Trade-offs

- **Risk: stop/cancel can hide unfinished work** -> Mitigation: stopped and
  cancelled are terminal lifecycle states, not success states; closure remains
  incomplete and the final preflight reports the stop reason.
- **Risk: host liveness reports can be stale** -> Mitigation: record timestamps
  and use the latest current-run host status; tests cover liveness failure
  overriding earlier progress.
- **Risk: orphan detection overclaims** -> Mitigation: successful runner
  summary produces a recovery duty only; formal result submission remains
  required.
- **Risk: concurrent peer-agent edits in `runtime.py`** -> Mitigation: keep
  edits additive and scoped, and commit only selected files for this change.

## Migration Plan

1. Add the OpenSpec specs and tasks for the stop/host/orphan behavior.
2. Extend or add a focused FlowGuard model for the miss class.
3. Implement runtime helpers and `flowpilot_new.py` commands.
4. Add focused unit tests and fake AI public CLI rehearsal scenarios.
5. Run focused tests and FlowGuard checks, then broader relevant regression.
6. Sync the installed local skill after source validation.
7. Commit the scoped files locally.

Rollback: revert the scoped commit and installed skill sync. Existing new runs
without the added fields should continue to load because the new fields are
optional ledger extensions.

## Open Questions

- None for this implementation. The live host bridge records host observations
  supplied by the foreground/host adapter; automating direct multi-agent
  probing can be a later adapter-specific enhancement.
