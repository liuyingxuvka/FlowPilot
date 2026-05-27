## Why

The existing fake-AI package regressions cover several normal and chaos flows,
but they still do not bind enough historical real-run failure shapes to the
same real Router, launcher, daemon, relay, install, and evidence surfaces that
failed during live testing. This change adds a higher-pressure replay package
suite for those control-plane edge cases before we rely on another real run.

## What Changes

- Add a historical live-run replay package matrix that enumerates finite
  packages for historical snapshots, host/role lifecycle recovery, production
  replay adapter boundaries, relay/receipt mechanical failures, parallel
  stress, background proof edges, install split-brain, route mutation stale
  evidence, semantic overclaim, UI/display projection staleness, and Windows
  filesystem hazards.
- Add focused runtime tests that use prepared fake AI artifacts through real
  Router, packet runtime, role-output runtime, background artifact, and resume
  surfaces.
- Add known-bad package cases that must be rejected before protected state,
  completion evidence, or current-run authority advances.
- Register the package suite in fast TestMesh and FlowGuard Model-Test
  Alignment so future runs cannot silently drop it.
- Preserve the confidence boundary: this proves bounded control-plane behavior
  for named package classes, not arbitrary live AI reasoning quality.

## Capabilities

### New Capabilities

- `historical-live-run-replay-package-suite`: Defines the replay package
  contract for historical real-run snapshots and multi-error fake AI packages
  through real FlowPilot control surfaces.

### Modified Capabilities

- `flowguard-background-observability`: Adds stale-run, progress-only, exit/meta
  mismatch, and proof-reuse edge rows to routine package evidence.
- `parallel-flowpilot-run-isolation`: Adds high-parallel and stale peer evidence
  package rows that must preserve current-run authority.
- `resume-rehydration-obligation-replay`: Adds host/role lifecycle replay
  packages for full six-role rehydration and standard recovery after partial
  host failure.
- `controller-completion-evidence`: Adds relay/receipt package rows that block
  done claims unless the real runtime state mutation and receipt evidence agree.

## Impact

- New simulation matrix and generated result JSON.
- New pytest matrix and runtime replay tests.
- Fast test-tier registration and FlowGuard Model-Test Alignment updates.
- Synthetic coverage matrix refresh and FlowGuard adoption log entry.
- Local installed FlowPilot skill synchronization and install audit after the
  repository source changes.
