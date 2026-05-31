## Why

FlowPilot currently checks worker results with FlowGuard before Reviewer review,
but a route node can still reach the worker before FlowGuard has challenged the
PM's node design, route assumptions, evidence plan, and skill/test route. That
puts FlowGuard after the expensive work instead of before the work gate.

The new FlowPilot runtime should treat every executable route node as a guarded
work gate: PM defines the node, FlowGuard checks the node before work starts,
and only then may the worker receive the node task.

## What Changes

- **BREAKING** Require a current accepted pre-work FlowGuard gate for each
  executable route node before the worker task packet can be issued.
- Make the pre-work FlowGuard packet runtime-issued, not PM-optional.
- Let the FlowGuard operator choose one or more applicable FlowGuard routes from
  the route scheduler based on the node's modeled target, risks, and evidence
  needs.
- Require PM-visible FlowGuard evidence, report fields, skipped-check
  disposition, confidence boundary, and repair guidance for the node design.
- If pre-work FlowGuard blocks, route back to PM repair. Repaired node designs
  must pass a fresh pre-work FlowGuard gate before worker execution resumes.
- Preserve the existing post-result FlowGuard and independent Reviewer gates.

## Capabilities

### New Capabilities

- `flowpilot-prework-flowguard-node-gate`: Runtime-enforced FlowGuard gate
  between PM node design and worker execution for every current route node.

### Modified Capabilities

- `flowguard-work-order-protocol`: Work orders now include a mandatory
  pre-work node gate, not only advisory/non-trivial decision support.
- `runtime-requested-role-bindings`: Runtime dispatch now requests the
  FlowGuard operator for node pre-work gates before worker packets.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- Affected tests: high-standard control-flow and runtime packet tests.
- Affected FlowGuard model: a focused node pre-work gate model/check.
- Local installed FlowPilot skill must be synchronized after repository
  validation.
