## Context

FlowPilot is a current-contract runtime. Runtime/router owns mechanical
validity, FlowGuard operator owns process/model/state review, and Reviewer owns
substantive quality review. Existing code already blocks some Reviewer
self-review cases, but live-run evidence showed the same producer agent can be
leased as the FlowGuard operator for that producer's result.

Parent backward replay is a special route-scope task produced by Reviewer. In
the generic post-result path it currently behaves like an ordinary task result:
task result, FlowGuard post-result check, Reviewer review packet, system
closure. For parent backward replay that creates an unnecessary
Reviewer -> FlowGuard -> Reviewer shape.

Blocker records are append-only history, while runtime decisions should use the
current-effective blocker projection. Existing runtime projection already has a
currentness helper; this change keeps that helper as the single source instead
of introducing another blocker table or compatibility shape.

## Goals / Non-Goals

**Goals:**

- Prevent a result producer from checking the same result as Reviewer or
  FlowGuard operator.
- Keep legitimate role reuse: the same Reviewer or FlowGuard operator can check
  a later result produced by another agent.
- Close parent backward replay after the existing FlowGuard post-result pass,
  then release the existing PM disposition path without opening a second
  Reviewer packet.
- Keep active blocker displays and gates tied to current-effective blockers
  only, while preserving historical blocker rows for audit.
- Add focused tests and FlowGuard/OpenSpec evidence for the exact observed
  family and non-regression cases.

**Non-Goals:**

- No new runtime fields, packet kinds, role kinds, ledgers, fallback parsers, or
  legacy aliases.
- No broad rewrite of packet review flow, role assignment, or blocker repair.
- No compatibility path for old packet/result shapes.
- No change to ordinary Worker -> FlowGuard -> Reviewer -> PM flow.

## Decisions

1. Use an existing-target producer check at assignment and submission time.

   The runtime will derive the target result producer from the current packet's
   existing `target_result_id` and the target result's existing
   `producer_agent_id`. For `reviewer` on `review` packets and
   `flowguard_operator` on `flowguard_check` packets, a matching agent id is a
   mechanical blocker.

   Alternative considered: add a new checker lineage field. Rejected because
   existing packet/result fields already express the needed relationship.

2. Keep the existing Reviewer reason string and add one FlowGuard-specific
   reason string.

   Reviewer self-review keeps `reviewer_self_review_forbidden` so existing
   tests and diagnostics remain stable. FlowGuard self-check uses
   `flowguard_operator_self_check_forbidden` so failures are specific without
   changing schema shape.

   Alternative considered: collapse both into `self_check_forbidden`. Rejected
   because role-specific diagnostics are more repairable and do not add data
   shape.

3. Parent backward replay bypasses only the second Reviewer packet after
   FlowGuard pass.

   When the subject task result has `route_scope=parent_backward_replay`, a
   passing FlowGuard check accepts the subject result, records parent backward
   replay closure, and opens the existing PM disposition packet. Other task
   result families still require the ordinary Reviewer packet.

   Alternative considered: skip FlowGuard before parent replay closure.
   Rejected because FlowGuard still owns process/state freshness and should
   check the replay before parent route state mutates.

4. Treat blocker currentness as projection, not mutation.

   Historical blocker rows are not deleted just because their target packet or
   repair packet is non-current. Runtime displays, final preflight, and gate
   decisions must call the existing currentness predicate or explicit PM gate
   exception. Tests should assert that raw history can remain while the current
   projection is clean.

   Alternative considered: remove old rows from `active_blockers`. Rejected
   because the ledger keeps audit history and existing currentness projection
   can express the repair without another cleanup mechanism.

## Risks / Trade-offs

- Assignment-only blocking could miss old ledgers with already-open illegal
  leases -> submission-time mechanical blocker mitigates this.
- Over-broad role reuse prevention could waste agents -> tests must cover same
  role reused for a different producer result.
- Parent replay closure could accept too early -> the shortcut is limited to
  `parent_backward_replay` after FlowGuard pass and still records the existing
  parent closure/PM disposition effects.
- Historical blocker rows can look scary in raw JSON -> tests and status
  projections must prove user-facing/current decisions use only
  current-effective blockers.
