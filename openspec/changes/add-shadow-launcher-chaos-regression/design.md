## Context

FlowPilot now has several layers of fake-AI package coverage: synthetic trace
replay, hard-gate red-team packages, full-flow E2E chaos replay, control-plane
canaries, and real-Router dry-run rehearsal. The remaining gap is closer to
the user's real failures: startup/install surfaces, process/liveness recovery,
multi-agent contention around shared artifacts, upgrade from older persisted
state, malformed package fuzzing, and repeated soak loops.

This work must preserve the existing Router and runtime contracts. It should
reuse current CLI/runtime helpers, TestMesh tiers, background artifact
contracts, and FlowGuard Model-Test Alignment instead of introducing a parallel
test framework.

## Goals / Non-Goals

**Goals:**

- Add executable shadow tests that prove prepared fake AI packages can traverse
  the installed launcher and real Router/CLI control surfaces.
- Add deterministic recovery packages for stale locks, daemon shutdown, resume,
  progress-only proof, peer-run authority conflicts, and migration from older
  persisted state.
- Add a bounded malformed-package generator that rejects finite bad package
  classes without mutating protected state.
- Add a short soak loop that repeats clean startup/recovery/terminal cycles and
  checks residue-free final state.
- Register all new evidence in fast TestMesh and Model-Test Alignment.

**Non-Goals:**

- No live AI model calls are required for these tests.
- No claim is made that all future AI semantic mistakes are impossible.
- No release, publish, tag, push, or OpenSpec archive is part of this change.
- No broad Router refactor is intended unless validation exposes a root-cause
  bug that cannot be fixed through test/evidence registration.

## Decisions

- Use prepared fake AI artifacts plus the real installed skill/Router runtime
  instead of live AI calls. This keeps the tests deterministic while exercising
  the control plane that failed in real use.
- Add a matrix script first, then runtime tests. The matrix names finite rows,
  expected standard states, entrypoints, and known-bad cases; the runtime tests
  prove selected rows through real code.
- Treat process crashes and peer conflicts as recovery-state tests. A pass is
  not "nothing bad happened"; a pass is that the system enters a recognized
  blocked, recoverable, quarantined, or clean terminal state.
- Reuse `scripts/run_test_tier.py` background artifacts for long evidence.
  Progress output alone is not proof.
- Register model-test evidence as distinct obligations when multiple negative
  cases prove different hazards. This avoids duplicate same-kind evidence owner
  failures.

## Risks / Trade-offs

- Long regression cost can grow quickly -> keep the new soak loop bounded and
  use background tier evidence for broad runs.
- Peer agents may change tests or model evidence while this work is running ->
  rerun final TestMesh/Model-Test Alignment after all visible writes and inspect
  final artifacts.
- Shadow launcher tests can overclaim if they only inspect installation files
  -> require an actual subprocess/CLI or installed-skill import boundary in the
  runtime tests.
- Migration fixtures can become stale -> keep them minimal and assert only the
  compatibility boundary needed for recovery.

## Migration Plan

1. Add matrix and runtime tests without changing production behavior.
2. Register the new tests in fast tier and Model-Test Alignment.
3. Run focused tests, strict OpenSpec validation, fast tier, Meta and Capability
   background checks.
4. Sync the local installed FlowPilot skill from the repository source.
5. Commit locally only after final evidence is current.
