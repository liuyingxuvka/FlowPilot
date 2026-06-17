## Why

The acceptance-item registry change is functionally green, but its validation evidence is still scoped to focused runtime, model, and fake-project paths. FlowPilot needs a release-grade TestMesh that makes acceptance-item loop, fake AI payload, route mutation, and terminal replay coverage explicit so broad confidence does not hide skipped, timed-out, or stale child evidence.

## What Changes

- Add an acceptance-registry TestMesh parent gate that partitions the validation claim into child suites for PM contract compilation, route ownership, node packets, PM disposition, terminal replay, route mutation, and fake AI payload chaos.
- Add finite negative payload cells for fake AI/work-package outputs that previously caused or could cause silent pass, endless reissue, stale evidence, or wrong terminal replay target behavior.
- Add current evidence freshness rules for slow quality-gate and router-tier checks so timed-out foreground parent commands cannot be reported as pass evidence.
- Keep the existing FlowPilot packet/result/gate architecture; this change adds tests and model evidence only, not a new runtime authority path.

## Capabilities

### New Capabilities
- `flowpilot-acceptance-testmesh`: Release-grade TestMesh and fake AI payload coverage for acceptance-item registry projection, repair loops, route mutation, and terminal closure.

### Modified Capabilities
- `multiround-fake-ai-control-rehearsal`: Require fake AI rehearsal payloads to derive current segment and acceptance-item fields from the opened packet body instead of static success fixtures.
- `router-runtime-testmesh`: Require slow/tiered router validation claims to expose child-suite evidence, timeout status, and release-scope gaps when acceptance-item paths are in scope.

## Impact

- Affected runtime evidence: fake AI rehearsal runner outputs, acceptance-item focused tests, TestMesh model/result artifacts, and topology freshness.
- Affected files are expected to remain in simulations, tests, OpenSpec artifacts, and adoption logs. Runtime code changes should only occur if a new test exposes a real current-contract miss.
- No public API or compatibility surface should be added.
