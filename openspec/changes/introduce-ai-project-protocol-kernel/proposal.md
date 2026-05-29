## Why

The user wants a clean AI project execution system that reaches the same goal
as the current FlowPilot work, but without inheriting the old fixed-role
topology, compatibility buildup, stale route state, or evidence ambiguity.

The core purpose is not to rebuild FlowPilot as-is. The core purpose is to
define a reusable protocol where a project can be split into isolated AI task
packets, routed through dynamic background agents, independently reviewed, and
closed only after FlowGuard-backed evidence proves that the work is complete.

## What Changes

- Preserve the current legacy source as a read-only backup/reference before
  new protocol work mutates source files.
- Add a new AI project protocol kernel, separate from old FlowPilot runtime
  state, that defines:
  - a project black-box ledger as the single source of truth;
  - dynamic agent leasing instead of fixed permanent AI roles;
  - sealed task packets and sealed result packets;
  - deterministic router decisions;
  - independent review gates;
  - FlowGuard sub-skill routing by work phase and risk;
  - final backward validation from user goal to delivered evidence.
- Add executable model checks and fake-agent scenarios for common long-run
  failures: missing ACK, ACK without output, stale output, dead/closed agents,
  wrong packet format, self-review, weak review, stale evidence reuse, route
  mutation with old packets, and final closure gaps.
- Keep old startup panel visuals and brand assets available for later reuse,
  but do not inherit old runtime state or old compatibility rules.

## Capabilities

### New Capabilities

- `ai-project-protocol-kernel`: Clean, model-first protocol for dynamic AI
  project execution with packet isolation, FlowGuard-routed validation, fake
  agent rehearsal, and final backward evidence closure.

### Modified Capabilities

- `repository-maintenance-guardrails`: Treat legacy backup and explicit
  non-reuse boundaries as required when starting a clean successor protocol.
- `flowguard-background-observability`: Permit heavyweight model regressions
  to run in background only when final artifacts are inspected before pass
  claims.

## Impact

- Affected code: new protocol reference assets under `skills/flowpilot/assets/`,
  new simulations under `simulations/`, focused tests under `tests/`, and local
  install/version metadata.
- Affected OpenSpec files: this change, including the new capability spec.
- Affected evidence: backup manifest, protocol contract, FlowGuard model
  checks, fake-agent scenario results, OpenSpec validation, background Meta and
  Capability regressions, install sync/audit/check, and local git commit.
- Out of scope: replacing the current FlowPilot runtime, launching a new full
  UI, remote push, tag, release, deploy, destructive runtime cleanup, secret or
  private account handling, and silent acceptance-contract changes.
