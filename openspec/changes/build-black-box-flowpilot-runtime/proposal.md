## Why

The protocol kernel and stress harness prove the core idea, but they do not yet
deliver the user's requested system. A complete clean successor needs a real
black-box runtime that can start from a user request, route isolated work
packets, lease background AI workers on demand, run FlowGuard work orders for
the right modeled target, review results independently, display safe status in
a minimal console, and close only when the backward evidence chain is current.

The goal is not to recreate the old fixed six-role FlowPilot topology. The goal
is to keep the old system as a reference library and build the clean capability
directly from the newer protocol decisions: stable responsibilities, dynamic
agent leases, sealed envelopes, explicit FlowGuard target selection, and
TestMesh-style evidence.

## What Changes

- Add a clean black-box runtime under the FlowPilot assets without deleting or
  rewriting the legacy router.
- Add a ledger-backed router that chooses legal next actions from durable
  project state rather than chat memory or old run folders.
- Add dynamic agent leases for planner, worker, reviewer, and FlowGuard
  operator responsibilities; leases can be closed, replaced, or superseded.
- Add sealed task and result packets with hash-backed envelopes and private
  bodies.
- Add FlowGuard work-order scheduling by modeled target and risk type.
- Add independent review gates and final backward closure checks.
- Add a minimal public console/status projection that never exposes sealed
  packet or result bodies.
- Add executable FlowGuard development-process modeling for the build itself,
  runtime simulations, focused tests, install inventory, and version notes.

## Capabilities

### New Capabilities

- `black-box-flowpilot-runtime`: A clean runtime implementation for dynamic AI
  project execution with ledger authority, on-demand leases, packet isolation,
  FlowGuard routed validation, review isolation, safe console status, and final
  closure.

### Modified Capabilities

- `ai-project-protocol-kernel`: The kernel becomes the contract source for the
  concrete runtime rather than only a standalone model.
- `repository-maintenance-guardrails`: The new runtime may reuse old assets by
  explicit reference only and must not import old runtime state as authority.
- `flowguard-background-observability`: Background regressions may support
  release confidence only after final artifacts and exit records are inspected.

## Impact

- Affected code: new assets under `skills/flowpilot/assets/ai_project_runtime/`,
  new simulations under `simulations/`, focused tests under `tests/`, install
  inventory, version, changelog, and local install sync.
- Affected OpenSpec: this change and its new capability spec.
- Required evidence: OpenSpec strict validation, FlowGuard development-process
  model, runtime simulation results, focused pytest, existing protocol/stress
  regressions, background Meta/Capability checks, install sync/audit/check, and
  a local git commit.
- Out of scope: destructive cleanup, remote push, remote deploy, tag creation,
  and accepting any fixed-role requirement as a new runtime invariant.
