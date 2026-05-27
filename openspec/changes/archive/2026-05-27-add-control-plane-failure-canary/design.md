## Context

FlowPilot now has synthetic AI trace packs, hard-gate red-team packs, and end-to-end synthetic chaos replay. Those packs prove many protocol-level mistakes are rejected or recovered, but the next confidence gap is control-plane infrastructure behavior: lock conflicts, stale lock records, half-written artifacts, launcher/daemon death, duplicate heartbeat wakeups, and peer-run authority collisions.

The repository already has focused runtime slices for startup daemon, foreground scheduler locks, resume/liveness, control blockers, terminal fences, and background supervisor artifact contracts. This change should reuse those surfaces instead of creating another recovery framework.

## Goals / Non-Goals

**Goals:**

- Add a finite canary matrix for realistic control-plane failure injection.
- Exercise real FlowPilot runtime/test-tier helpers where available.
- Prove every canary row has a recovery expectation and a standard-state expectation.
- Reject known-bad canary definitions that omit protected state, recovery route, final state, or final proof evidence.
- Register the canary in fast validation and model-test alignment evidence.

**Non-Goals:**

- Do not mutate a live user `.flowpilot/` run.
- Do not create destructive OS-level tests such as killing unrelated processes, forcing power loss, or locking user files outside an isolated temp run.
- Do not claim every possible Windows, hardware, antivirus, or filesystem failure is proven.
- Do not change production runtime behavior unless executable canary evidence exposes a concrete defect.

## Decisions

1. **Represent canary rows as a bounded matrix.**
   Each row names the failure injection, control-plane surface, protected invariant, recovery route, standard final state, evidence role, and test owner. This keeps the confidence claim finite and reviewable.

2. **Use isolated temp runs for runtime replay.**
   Tests create temporary FlowPilot run roots and artifacts, then call existing runtime helpers or background artifact classifiers. This avoids destructive live-state mutation while still exercising real code paths.

3. **Keep background proof freshness explicit.**
   Rows that involve supervisor artifacts must require final `exit` and `meta` evidence. Progress logs, stale meta, or missing final artifacts are known-bad inputs.

4. **Treat launcher/daemon death as resume/liveness recovery, not success.**
   A dead daemon or missing launcher record must lead to restart/recovery/blocker state, never ordinary route advancement.

5. **Register only routine canary evidence in fast tier.**
   The canary tests should be fast and deterministic. Heavyweight model regressions remain background evidence with final artifact inspection.

## Risks / Trade-offs

- **Risk: Canary tests overclaim real OS coverage.**
  Mitigation: every matrix result includes a confidence boundary that excludes unmodeled OS/hardware failures.

- **Risk: Tests become destructive or flaky if they lock real files.**
  Mitigation: use isolated temp artifacts and simulated lock/error paths exposed through existing helpers.

- **Risk: Matrix duplicates existing router child suites.**
  Mitigation: the canary matrix is a parent confidence view; runtime tests target cross-surface failure stories that existing slices test individually.

- **Risk: Background artifact freshness is mistaken for pass/fail.**
  Mitigation: tests and adoption records must inspect final `exit/meta/combined` paths and timestamps before counting proof.
