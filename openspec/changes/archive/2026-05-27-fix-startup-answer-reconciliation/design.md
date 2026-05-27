## Context

The observed failure happened during live native startup intake. The startup UI
result was accepted and deterministic seed evidence was written, but the live
daemon projected a later `record_startup_answers` Controller row whose ordinary
receipt could not satisfy Router's bootloader postcondition. The scheduler then
exhausted its retry budget and created a PM/control blocker.

Relevant current constraints:

- Formal startup must only accept interactive native intake artifacts.
- Startup deterministic foundation work must remain Router-owned and must not
  become ordinary Controller work after seed completion.
- Controller receipts are evidence, not final workflow completion, unless the
  registered Router reconciliation path can prove the postcondition.
- Unsupported startup receipts must still block instead of being silently
  accepted.

## Goals / Non-Goals

**Goals:**

- Make confirmed startup intake the single authoritative owner for startup
  answers and deterministic seed side effects.
- Prevent live-daemon reconciliation from reissuing `record_startup_answers`
  after startup answers are already durably recorded.
- Make repeated `record_startup_answers` receipts safe when they match durable
  startup answers.
- Add regression tests for the observed live-daemon interleaving and for the
  same-class idempotent replay case.
- Preserve the existing blocker path for unsupported or incomplete receipts.

**Non-Goals:**

- Do not change the native startup UI schema.
- Do not weaken interactive-native provenance requirements.
- Do not change heartbeat, role spawning, Controller core loading, or PM route
  behavior except where they depend on startup answer settlement.
- Do not absorb unrelated peer-agent edits.

## Decisions

1. Use startup intake as the canonical answer owner.

   The direct `open_startup_intake_ui` path already records startup answers and
   runs deterministic seed materialization. The repair should preserve that
   ownership and make daemon/controller reconciliation project the same facts,
   rather than introducing a second owner for `record_startup_answers`.

2. Add an idempotent receipt effect for `record_startup_answers`.

   A normal Controller receipt with `startup_answers` should be accepted only
   when it validates and can set or confirm the same durable postcondition. If
   answers already exist and match the validated payload, the effect is a replay
   confirmation. If answers do not exist, the same validation path records them.

3. Treat completed deterministic seed evidence as a live projection source.

   If seed evidence is complete, Router must sync the seed-owned flags before
   choosing later bootloader work. This prevents deterministic setup rows from
   appearing after a completed startup intake.

4. Keep blocker behavior for unsupported receipts.

   The unsupported-receipt path remains the guardrail for malformed payloads,
   missing provenance, missing seed evidence, or receipts that cannot prove the
   requested postcondition.

5. Validate with targeted runtime tests before broader background regressions.

   The fastest confidence path is a focused runtime reproduction test for the
   observed interleaving, then startup/Controller related tests, then background
   model and router tier checks.

## Risks / Trade-offs

- Idempotent replay might accidentally hide a real mismatch -> Validate payloads
  and compare durable answers before accepting a replay.
- Syncing seed evidence before next-action selection could mask corrupted seed
  proof -> Accept only completed seed evidence with required flags, otherwise
  keep the existing failure/blocker path.
- Background regressions can be long-running -> Use documented background log
  roots and treat progress-only logs as liveness, not completion.
- Parallel agents may change unrelated files -> Keep edits to startup
  reconciliation, focused tests, and OpenSpec artifacts; re-check git status
  before install sync and final reporting.

## Migration Plan

1. Add OpenSpec requirements and tasks for the startup answer reconciliation
   boundary.
2. Add or update FlowGuard-focused model coverage for the observed miss when
   practical.
3. Implement the minimal Router reconciliation fix.
4. Add focused tests that reproduce the live-daemon receipt/apply interleaving.
5. Run targeted tests, then start required model/router regressions in
   background where supported.
6. Sync the local installed FlowPilot skill from the repository source and run
   the install audit/check.
7. Re-check git state and report which files were changed by this task versus
   pre-existing peer edits.
