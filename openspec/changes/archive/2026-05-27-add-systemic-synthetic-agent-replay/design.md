## Overview

This change adds story-shaped replay packages on top of the existing
synthetic trace helper and router runtime fixtures. Each story starts with fake
AI activity and must end in one of two legal outcomes:

- the run is still blocked with a specific recovery/control-plane reason; or
- the run is eligible to continue only after current, replayable evidence has
  replaced the bad or stale work.

The implementation must not create another fake framework. It should reuse
real FlowPilot runtime APIs and existing router test fixtures.

## Story Classes

System-level synthetic replay covers these story classes:

1. Valid envelope, bad content: the AI writes through a legal envelope, but the
   payload lacks deliverable evidence, references an invalid target, or carries
   contradictory completion signals.
2. Stacked blockers: ACK-only, control blocker, PM suggestion, or dirty ledger
   evidence overlap and the highest-priority control-plane blocker preempts
   normal work.
3. Failed PM repair loop: a legal PM repair attempt fails to produce a valid
   deliverable, retry budget is consumed, and the flow escalates instead of
   completing or looping forever.
4. Restart and stale state: stale saved state, old packet body, or old PM
   disposition cannot satisfy the current obligation after reentry.
5. Peer or parallel interference: foreign or stale writes cannot overwrite the
   current run's authority or count as completion evidence.
6. Terminal total gate: final completion is blocked while any dirty PM
   suggestion, defect, material, self-interrogation, or background evidence
   remains unresolved.

## Matrix Fields

System-level rows should extend the existing coverage row shape with:

- `story_level`: `local` or `system`;
- `recovery_loop`: a short identifier such as `pm_repair_escalation`,
  `resume_preemption`, `stale_state_quarantine`, or `terminal_total_gate`;
- `story_steps`: ordered labels for the fake AI/control-plane/recovery steps;
- `terminal_expectation`: `blocked`, `continue_allowed`, or
  `completion_rejected`.

The matrix should fail if a `story_level: system` row lacks a recovery loop,
story steps, or terminal expectation.

## Validation Strategy

1. Add focused system-level replay tests to the existing synthetic trace replay
   test module.
2. Add matrix validation for required system-level row fields and known-bad
   rows.
3. Regenerate the synthetic coverage matrix JSON.
4. Run focused synthetic tests and matrix tests.
5. Run model-test alignment and fast tier.
6. Run Meta and Capability checks in background under `tmp/flowguard_background`
   and inspect final out/err/combined/exit/meta artifacts.
7. Sync and audit the local installed FlowPilot skill after validation.

## Non-Goals

- Do not claim mathematical coverage for every possible future AI response.
- Do not claim live semantic answer quality from fake packages.
- Do not replace ordinary router runtime suites with synthetic stories.
- Do not change production FlowPilot runtime behavior unless a test exposes a
  concrete bug that cannot be fixed in test/evidence logic.
