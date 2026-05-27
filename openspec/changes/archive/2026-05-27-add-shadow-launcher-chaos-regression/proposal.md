## Why

Prepared fake-AI package tests now cover the real Router runtime, but they do
not yet prove that the installed launcher, process/liveness recovery, peer-run
contention, upgrade migration, malformed package rejection, and repeated soak
loops return to a standard state under realistic workspace conditions. This
change closes that next confidence gap with bounded, executable shadow
regressions.

## What Changes

- Add a shadow-launcher regression matrix that declares finite rows for real
  launcher startup, crash recovery, peer-agent conflicts, upgrade migration,
  malformed fake packages, and repeated soak loops.
- Add runtime tests that exercise the installed skill and real Router/CLI
  surfaces with prepared fake AI artifacts while keeping live AI calls mocked
  or fixture-backed.
- Add deterministic crash/recovery and peer-conflict bad cases that must return
  to blocked, recoverable, quarantined, or clean terminal states.
- Register the new evidence in fast TestMesh coverage and FlowGuard
  Model-Test Alignment.
- Preserve an explicit confidence boundary: these tests prove current
  control-plane resilience for prepared package classes, not arbitrary live AI
  semantic quality.

## Capabilities

### New Capabilities

- `shadow-launcher-chaos-regression`: Defines the regression contract for
  installed-launcher shadow runs, crash recovery, peer-agent contention, upgrade
  migration, malformed fake packages, and bounded soak loops.

### Modified Capabilities

- `flowguard-background-observability`: Adds the requirement that shadow
  launcher and soak regressions use final background exit/meta artifacts before
  pass claims.
- `parallel-flowpilot-run-isolation`: Adds peer-agent conflict rows that prove
  shared artifacts and run ownership cannot cross-contaminate active runs.
- `persistent-router-daemon`: Adds crash/restart rehearsal evidence for daemon
  death, stale locks, and resume recovery.

## Impact

- New simulation matrix and generated result JSON.
- New pytest runtime tests for installed launcher shadow flow, crash recovery,
  peer conflict, migration, malformed package fuzzing, and soak loops.
- Test tier registration, FlowGuard model-test alignment evidence, and
  FlowGuard adoption logs.
- Local installed FlowPilot skill synchronization after source changes.
