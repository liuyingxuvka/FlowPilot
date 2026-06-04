## Context

FlowPilot is a current-contract runtime. Existing project rules forbid
compatibility shims, old-router fallback, legacy field aliases, prose/shape
guessing, and missing-field defaults unless a named migration is approved.

The current live run has route version 6, progress `14/22`, and repeated
FlowGuard/PM loops around `materialize-reviewed-route`. A separate FlowPilot run
reported stale `result_submitted` packets and PM decision packet reuse. The
shared cause is that runtime routing can still treat old, unaccepted, blocked,
or future-state references as current targets.

Existing FlowGuard models already cover some stale evidence and staged-effect
risks, but they do not directly model `result_submitted` packets without
`accepted_result_id`, blocked PM decision packet reuse, missing responsibility
fallback, or same-family staged-effect expansion.

## Goals / Non-Goals

**Goals:**

- Keep exactly one current repair target at every routing and blocker boundary.
- Reuse existing packet/result/blocker/gate/route-node records instead of
  adding a global current-packet ledger.
- Make old replaced packets audit-only by marking them noncurrent.
- Keep PM decision format strict and top-level only.
- Move mechanical validity to runtime/router; FlowGuard and Reviewer inspect
  real current artifacts and effects.
- Add model and test coverage for the generalized bad class, not just observed
  packet ids.

**Non-Goals:**

- No compatibility parser for nested PM repair decision wrappers.
- No fallback responsibility or subject inference.
- No old-router, newest-run, repo-root, or historical-artifact promotion.
- No new packet kind, role family, candidate ledger, or per-scenario state
  table.
- No silent migration of historical packet shapes into current evidence.

## Decisions

### Current Target Gate Instead Of A New Ledger

Add internal runtime helpers that validate a packet/result/blocker target
against the existing ledger. The gate checks status, route version, route-node
currentness, accepted/current result identity, blocker status, packet kind,
responsibility, and explicit repair replacement records.

Alternative considered: create a unique current-packet mapping table. Rejected
because existing statuses and repair transaction records can express the repair,
and a new table would recreate old-router complexity.

### Supersede Replaced `result_submitted` Packets

When a repair/reissue creates a fresh current packet for a blocker chain, mark
the old blocked or replaced `result_submitted` packet as
`superseded_after_repair`. This applies only when a newer explicit repair target
exists; ordinary pending `result_submitted` packets still remain valid while
waiting for FlowGuard/review.

Alternative considered: treat every `result_submitted` packet as noncurrent.
Rejected because `result_submitted` is valid while a current FlowGuard/review
chain is pending.

### PM Decision Packets Are Strict And Single-Use After Blocking

The parser remains top-level `decision` only. Runtime improves the issued PM
packet instruction so the required JSON shape is explicit. If a PM decision
packet becomes mechanically or semantically blocked, the runtime issues a fresh
PM decision packet for the same blocker instead of returning the blocked packet
from `_find_packet`.

Alternative considered: parse nested `repair_decision` and
`pm_repair_decision` wrappers. Rejected because it would preserve legacy shape
compatibility.

### Missing Responsibility Is A Hard Control-Plane Block

Recovery commands must derive responsibility from the current packet envelope.
If the envelope cannot provide it, runtime reports a control-plane blocker
instead of falling back to `next_action` or another source.

Alternative considered: keep fallback as a convenience. Rejected because it can
hide stale or wrong packet selection.

### Staged Effect Convergence

FlowGuard and Reviewer inspect the pending staged effect as the real current
effect. They must not demand future committed route-node fields before the gate
closes. Lifecycle/replay checks must detect repeated same-family staged-effect
loops even when packet ids keep changing.

## Risks / Trade-offs

- Current-target checks could be too strict and block legitimate pending work.
  Mitigation: add focused tests where ordinary pending `result_submitted`
  packets still receive FlowGuard/review packets.
- Superseding `result_submitted` after repair could hide useful audit context.
  Mitigation: preserve result ids and supersession metadata; only routing
  authority changes.
- Same-family loop detection could block distinct new repair attempts.
  Mitigation: key by current route node, gate/effect kind, blocker class, and
  target identity, not by packet id alone.
- Model changes can stale topology and model-test alignment. Mitigation:
  rerun focused FlowGuard checks, model-test alignment, fake/bad packet tests,
  topology build/check, install sync audit, and install check before done.
