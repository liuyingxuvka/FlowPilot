## Context

FlowPilot now has several synthetic coverage layers: single-boundary hard-gate
rows, synthetic trace replay, end-to-end synthetic chaos replay, and real Router
dry-run rehearsal. Those layers catch many bad fake AI packages, but the latest
control-plane failure exposed a second-hop gap: a PM repair decision can be
rejected or accepted independently of whether it creates a real producer for
the next wait.

The existing ownership boundaries are still correct:

- `executable-repair-transactions` owns whether PM repair transactions are
  executable and producer-backed.
- `flowpilot_e2e_synthetic_chaos_matrix.py` owns full-flow fake AI sequences.
- `flowpilot_real_router_dry_run_rehearsal_matrix.py` owns real Router/runtime
  dry-run confidence boundaries.
- model-test alignment owns whether the new evidence remains attached to the
  FlowGuard obligation.

## Goals / Non-Goals

**Goals:**

- Add explicit multi-round fake AI rehearsal rows for bad package, bad PM
  repair, corrected PM repair, stale evidence, and legal continuation.
- Make no-producer PM repair decisions a required known-bad rehearsal case,
  not only a focused unit regression.
- Ensure real-Router dry-run evidence names producer-proof repair waits as a
  required control-plane gate.
- Register the new evidence in model-test alignment and fast-tier checks.
- Keep validation layered so short gates run quickly and Meta/Capability
  regressions can run in background with final artifacts.

**Non-Goals:**

- Do not run live external AI models.
- Do not claim prepared fake AI packages prove live model semantic quality.
- Do not redesign the repair transaction framework or introduce a second repair
  system.
- Do not change release, publish, tag, or push behavior.

## Decisions

1. Extend existing matrices instead of creating a third rehearsal framework.
   - Rationale: the missing behavior belongs to the current E2E chaos and real
     Router rehearsal evidence surfaces. A new framework would create another
     ownership boundary without adding protection.
   - Alternative considered: add a standalone test file only. Rejected because
     it would not force future matrix/model-test alignment visibility.

2. Treat producer proof as part of the multi-round script, not just a unit
   assertion.
   - Rationale: the failure happened after a repair loop, so the evidence must
     cover the route from rejection to corrected continuation.
   - Alternative considered: rely on `role_reissue_without_event_producer`
     model coverage alone. Rejected because it does not exercise the fake AI
     package path that starts a real run.

3. Keep the fast gate bounded and delegate heavier confidence to background
   regressions.
   - Rationale: the user wants this to protect startup without turning every
     work session into a full release run. Fast gates must catch known control
     plane hazards; background Meta/Capability runs refresh broader confidence.

## Risks / Trade-offs

- [Risk] Matrix rows overclaim live AI quality. -> Mitigation: require
  `live_ai_semantic_quality_proven: false` and confidence text that names the
  prepared-package boundary.
- [Risk] The new row only proves a metadata entry, not runtime behavior. ->
  Mitigation: connect it to existing runtime tests and add exact evidence ids
  consumed by model-test alignment.
- [Risk] The fast gate becomes too slow. -> Mitigation: keep new direct checks
  focused on matrix validation, existing E2E replay, repair transaction checks,
  and model-test alignment; run parent Meta/Capability checks in background.
- [Risk] Future changes drop the evidence silently. -> Mitigation: update tier
  assertions and model-test alignment tests to require the new evidence id.
