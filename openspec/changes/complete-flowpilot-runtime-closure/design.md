## Context

FlowPilot has already moved from a monolithic prompt toward a prompt-isolated
router, runtime cards, packet envelopes, role-output runtime, and FlowGuard
models. The remaining gaps are now narrower but still behavior-bearing:
Process/Product FlowGuard officer reports can still lean on generic PM
role-work channels, continuation can import prior evidence without a dedicated
current-run quarantine contract, terminal closure lacks a durable user-facing
report artifact, and route display refresh is not yet a first-class runtime
obligation.

This change continues the conservative maintenance style used in v0.9.3:
add explicit contracts, small runtime helpers, focused models, focused tests,
install checks, and documentation updates without replacing the router or
changing public startup semantics.

## Goals / Non-Goals

**Goals:**

- Make officer model requests and reports packet-backed, router-authorized, and
  contract-validated instead of depending on direct invented role events.
- Make continuation import boundaries explicit so old run state, old agent IDs,
  and stale artifacts cannot become current authority by accident.
- Emit a durable final user report only after terminal replay and PM closure
  approval are clean.
- Refresh chat route signs and UI snapshots when route/frontier state changes.
- Preserve existing CLI compatibility and installed skill sync behavior.
- Validate with focused FlowGuard models/tests first, then broad background
  regressions and install audits.

**Non-Goals:**

- No release, remote push, tag publication, or destructive cleanup.
- No large rewrite of `flowpilot_router.py` beyond the seams needed for this
  runtime closure pass.
- No new external dependencies.
- No replacement of the existing packet runtime, role-output runtime, or
  FlowGuard model mesh.
- No native Cockpit implementation beyond producing UI-readable state.

## Decisions

1. **Officer lifecycle extends the existing packet/runtime layer.**

   Process and Product FlowGuard officer work will use explicit PM request
   packets and officer report envelopes. The router will accept officer report
   completion only through registered packet/result or role-output contracts.
   This avoids adding a parallel officer-only channel and prevents direct event
   names from bypassing current Router wait authorization.

2. **Quarantine is current-run metadata, not a cleanup operation.**

   Continuation quarantine will record imported prior evidence, stale or
   prohibited authority sources, and disposition decisions under the current run.
   The maintenance pass will not delete historical files. Old run data can be
   referenced as evidence only after the quarantine check marks it read-only and
   non-authoritative.

3. **Final user report is downstream of closure, not a substitute for closure.**

   The user-facing report is emitted only after final ledger, terminal backward
   replay, and PM closure approval are clean. It summarizes delivered outcome,
   validation, residual none/waivers, and continuation status, but it cannot
   create completion authority by itself.

4. **Route display refresh is metadata-driven.**

   Route signs and UI snapshots will be regenerated from current route/frontier
   data and written as display artifacts. The Controller can show them, but
   display artifacts do not replace route state, packet ledgers, or PM
   decisions.

5. **Verification remains tiered.**

   Focused FlowGuard models and tests own the new risk boundaries. Meta and
   Capability regressions run through the repository background artifact
   contract, preferably with proof reuse when inputs are unchanged. A skipped
   or reused heavy check remains visible.

6. **Router settlement remains single-owner and idempotent.**

   Runtime receipt repair extends the existing Router reconciliation pass. If a
   Controller action is already `reconciled` but its Router scheduler row is
   still `receipt_done`, Router backfills that row from the action's durable
   reconciliation evidence. This is not a second pusher, a second daemon, or a
   PM-status shortcut.

7. **Active runtime writers are a wait state, not a control blocker.**

   Existing JSON write-lock settlement remains the mechanism for foreground
   commands and daemon ticks. A fresh or visibly progressing runtime writer
   keeps the reader in wait/retry behavior; only stale, non-progressing write
   evidence falls back to the existing corruption/repair path.

## Risks / Trade-offs

- Officer reports still bypass Router authorization -> Add model hazards and
  runtime tests for invented direct events and missing PM packet references.
- Quarantine blocks valid continuation evidence -> Allow read-only imported
  evidence with explicit current-run disposition and source hashes.
- Final user report becomes a false completion shortcut -> Require it to be
  generated only after terminal closure approval and never accepted as a PM
  closure input.
- Route sign refresh becomes noisy or stale -> Tie refresh to route/frontier
  version and include freshness metadata in the display artifact.
- Full regressions are expensive -> Use focused checks for touched boundaries
  and background Meta/Capability artifacts for broad confidence.

## Migration Plan

1. Add focused FlowGuard model coverage for officer packet lifecycle,
   continuation quarantine, closure user report, route display refresh, and
   Router runtime settlement drift.
2. Add runtime helpers, templates, cards, and validators for each boundary.
3. Add focused runtime and install tests.
4. Update documentation and adoption logs.
5. Run focused checks, background broad regressions, install sync/audit, and
   OpenSpec validation.
6. Commit locally. Do not push, tag, or publish without explicit approval.

## Open Questions

- None blocking. Native Cockpit rendering remains out of scope; this pass
  produces the state needed for a future UI consumer.
