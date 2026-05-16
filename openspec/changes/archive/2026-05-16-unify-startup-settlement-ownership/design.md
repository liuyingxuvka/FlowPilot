## Context

FlowPilot already has a runtime JSON write-lock contract and a Controller
receipt application path. The daemon path waits when it sees a fresh writer
lock, but foreground startup can still surface that same fresh lock as a fatal
startup error. Startup daemon bootloader rows also have a direct postcondition
completion helper that can mark action rows as reconciled outside the receipt
application path, which leaves two owners for the same startup fact.

## Goals / Non-Goals

**Goals:**
- Reuse the existing write-lock liveness check for foreground startup/status
  commands.
- Reuse the existing startup Controller receipt application path as the only
  final owner of startup action-row reconciliation.
- Preserve stale-lock, corrupt-JSON, unsupported-receipt, and real blocker
  paths.
- Keep receipt replay idempotent.

**Non-Goals:**
- Do not add a second startup workflow, daemon, ledger, or lock mechanism.
- Do not weaken startup gates or make Controller receipts count as role work
  without the existing Router-owned postcondition checks.
- Do not modify unrelated repair-transaction, packet, PM, or reviewer
  authority behavior.

## Decisions

1. Foreground commands wait through the existing runtime lock contract.
   - Rationale: a fresh lock already means "another writer may still be
     settling JSON"; foreground and daemon code should classify it the same
     way.
   - Alternative considered: retry only the `start` command by name. Rejected
     because status/read paths can hit the same active-writer boundary.

2. Staleness remains the stop condition for writer waits.
   - Rationale: the current lock contract already distinguishes fresh progress
     from stale failure. Waiting while the writer keeps the lock fresh avoids
     false startup failure without hiding a dead writer forever.
   - Alternative considered: add a short fixed timeout. Rejected because a
     legitimate writer can take longer while still making progress.

3. Startup daemon postconditions fold through receipts.
   - Rationale: `_apply_startup_bootloader_receipt_effects` is already the
     central place where Controller receipts become Router-owned startup facts.
   - Alternative considered: keep the daemon postcondition writer and add
     blocker suppressions. Rejected because that preserves split ownership and
     can drift again.

4. Already reconciled startup receipts are no-ops.
   - Rationale: startup reconciliation runs on repeated daemon ticks and manual
     foreground retries, so duplicate observations must not create duplicate
     side effects or repair blockers.

## Risks / Trade-offs

- [Risk] Waiting too broadly could mask unsupported startup receipt logic.
  Mitigation: wait only for concrete fresh write-lock evidence; stale locks,
  corrupt JSON without active writer evidence, and unsupported receipt effects
  still use existing failure paths.
- [Risk] Moving final ownership to receipts could miss a startup action that
  only the daemon postcondition helper understood. Mitigation: extend the
  existing startup receipt effect helper for the daemon bootloader receipt
  payload instead of leaving a direct second owner.
- [Risk] Parallel agents may have compatible edits in the same runtime file.
  Mitigation: inspect local diffs around touched functions and keep edits
  limited to the lock-wait and startup receipt boundaries.

## Migration Plan

1. Confirm real FlowGuard is importable and the focused startup-settlement
   model passes before runtime edits.
2. Patch foreground command execution to retry after fresh runtime writer
   locks using the existing lock liveness helper.
3. Patch startup daemon bootloader completion to call the existing receipt
   reconciliation path instead of directly finalizing action rows.
4. Add focused runtime tests for foreground writer settlement and single-owner
   startup receipt reconciliation.
5. Run focused FlowGuard, tests, OpenSpec validation, local install sync, and
   background heavyweight regressions.

## Open Questions

None. The default is to preserve existing stale-lock and blocker semantics.
