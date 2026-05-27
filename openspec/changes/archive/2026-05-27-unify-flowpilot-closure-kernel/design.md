## Context

FlowPilot already has stronger contracts for Controller receipts, signed
artifacts, ACK settlement, and current-scope reconciliation. The remaining
repeated failure class is smaller but cross-cutting: each module still decides
locally whether a row is open, closed, terminal, repairable, or unknown.

The latest observed miss was a Controller action whose `status=resolved` and
`router_reconciliation_status=reconciled` still blocked
current-scope reconciliation because one scanner only recognized
`done`, `blocked`, and `skipped`. The same pattern can recur for Worker, PM,
Reviewer, packet, ACK, and terminal records if their scanners keep local status
vocabularies.

## Goals / Non-Goals

**Goals:**

- Provide one shared closure classification helper for FlowPilot runtime code.
- Make high-risk blocker/wait scans ask whether a record still blocks progress,
  instead of testing ad hoc closed-status lists.
- Preserve role-specific semantics by adapting local records into a common
  closure view only at the lifecycle/blocking boundary.
- Extend FlowGuard coverage so same-class closure vocabulary drift is caught
  beyond Controller-only scenarios.
- Keep the implementation narrow enough to coexist with active peer-agent work.

**Non-Goals:**

- Do not merge all ledgers into one physical table in this change.
- Do not collapse role-specific states into one global status vocabulary.
- Do not treat ACK settlement as semantic work completion.
- Do not weaken reviewer package sufficiency, worker self-check, Controller
  foreground patrol, worker isolation, or signed-artifact immutability.
- Do not publish, push, release, or change dependencies.

## Decisions

1. **Use a small closure kernel, not a table rewrite.**

   Runtime modules will call a shared helper that returns a normalized
   classification such as `open`, `closed_success`, `closed_terminal`,
   `repair_required`, `invalid_or_incomplete`, or `unknown_needs_recheck`.
   This avoids a large migration while removing the repeated local-status-list
   failure mode.

   Alternative considered: merge Controller, Router, Worker, PM, Reviewer, and
   packet lifecycle records into one ledger now. Rejected for this change
   because it would be broader than needed and would create unnecessary conflict
   with active parallel work.

2. **Keep domain vocabularies, normalize decisions.**

   Controller records, scheduler rows, system-card returns, worker results,
   PM dispositions, reviewer packages, packet relay entries, and terminal rows
   may keep their existing fields. Each adapter maps its record to the common
   closure result at the point where Router asks whether progress is blocked.

   Alternative considered: rename all statuses to a single vocabulary.
   Rejected because it would blur semantic differences and force a large data
   migration.

3. **Treat unknown or inconsistent records as non-clear, not silently closed.**

   If a record lacks enough evidence to classify as success or terminal closure,
   the kernel returns `invalid_or_incomplete` or `unknown_needs_recheck`; callers
   must keep it visible as a blocker or repair item rather than advancing.

4. **Separate lifecycle closure from semantic completion.**

   The kernel answers "does this record still mechanically block progress?"
   It does not decide whether a reviewer approved quality, whether PM absorbed a
   worker result correctly, or whether a sealed artifact can be read.

5. **Adopt incrementally through high-risk gates.**

   The first runtime pass should target current-scope pre-review blockers,
   controller/scheduler reconciliation summaries, ACK return waits, role dispatch
   busy gates, and terminal closure scans. Lower-risk callers can be converted
   later after the first regression set is stable.

## Risks / Trade-offs

- **Risk: over-normalizing semantic state** -> Mitigation: keep helper names and
  return values explicitly about lifecycle blocking, not approval quality.
- **Risk: unknown statuses accidentally clear work** -> Mitigation: default
  unknown/incomplete records to blocking or repair-required.
- **Risk: peer-agent conflict in broad runtime files** -> Mitigation: keep edits
  to a new helper plus narrow call-site replacements; avoid unrelated formatter
  or router-facade cleanup.
- **Risk: FlowGuard model passes but runtime call-sites remain local** ->
  Mitigation: add tests that exercise real helper calls and audit high-risk
  local status checks.

## Migration Plan

1. Add FlowGuard same-class hazards for Controller, Worker/role, PM/reviewer,
   packet/ACK, and terminal closure drift.
2. Add the shared closure helper as an internal runtime module.
3. Replace high-risk blocking scans with helper calls while preserving existing
   JSON shapes.
4. Add focused regression tests from observed failures.
5. Run focused models/tests, then start heavyweight meta/capability checks in
   the background using the repository log contract.
6. Sync the installed local FlowPilot skill and verify install freshness.
7. Record adoption evidence and leave any broader table consolidation as a
   follow-up only if evidence shows it is still needed.

## Open Questions

- None blocking. If inventory finds a heavily active peer-owned module, that
  call-site should be skipped and reported rather than forcing a conflict.
