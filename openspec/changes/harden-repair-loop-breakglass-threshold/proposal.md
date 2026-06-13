# Harden Repair Loop Breakglass Threshold

## Why

The current FlowPilot repair path can keep producing fresh packets, route
versions, and repair nodes while repeating the same missing-information or
handoff failure. The lifecycle guard sees mechanical progress because new
events are written, but the user-visible route is semantically looping.

ProjectRadar exposed this as a long `node-032` repair chain with many
same-family `missing_required_information` blockers and no Controller
break-glass incident.

## What Changes

- Add one simple hard threshold: more than five same-family repair attempts
  enters Controller break-glass evaluation instead of issuing another ordinary
  PM repair packet.
- Compute the repair family from existing ledger data; do not add a broad
  persistent field mesh.
- Reuse existing Controller break-glass and Recovery Supervisor paths.
- Update PM, Controller, break-glass, and FlowGuard Operator guidance so new
  packets and route versions are not mistaken for real progress.
- Add FlowGuard and runtime regression coverage for long same-family repair
  loops.

## Non-Goals

- No three-stage retry ladder.
- No new recovery subsystem.
- No authority for Controller or Recovery Supervisor to approve project work,
  close gates, mutate routes, or bypass PM/Reviewer/FlowGuard validation.
- No compatibility with old packet shapes or historical artifact promotion.
