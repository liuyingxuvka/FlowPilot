## Why

Recent FlowPilot control-plane runs exposed a model miss: a FlowGuard packet
reissue could lose packet-owned evidence policy, the result could be accepted
while the FlowGuard work order failed, and a reviewer packet could continue
without matching FlowGuard evidence. These are finite control-contract cases,
so they should be generated and checked by FlowGuard-backed matrices instead
of relying on ad hoc scenario selection.

## What Changes

- Add a contract-exhaustion matrix for current FlowPilot packet/result,
  FlowGuard evidence, reviewer, blocker, and repair-control surfaces.
- Generate missing-body, missing-field, wrong-type, wrong-target,
  missing-authorized-read, missing evidence-file, evidence-path mismatch,
  result/work-order mismatch, empty required manifest, reissue-inheritance,
  and repeated no-delta cases from real current contracts.
- Require runtime oracle outcomes for each generated case: block, reissue with
  concrete missing information, stop downstream review, count no-delta loops,
  or record a GlassBreak alarm when repeated same-root blockers prove normal
  repair failed. Formal rehearsals that reach GlassBreak are not accepted
  success paths.
- Add history-derived failure families for missing bodies, missing mail,
  wrong addresses, stale context, vanished evidence, install split-brain,
  invalid repair targets, and repeated blocker storms; each family must name a
  normal repair route before GlassBreak.
- Require every matrix-emitted evidence owner to be registered as a current
  TestMesh child suite so upstream generated rows cannot pass without
  downstream consumption.
- Require live-run replay and coverage inventory to be zero-tolerance for
  `live_runtime_or_state_findings`; a current `control_plane_stuck` or
  unrepairable blocker must block completion instead of being preserved as an
  expected-green baseline.
- Extend parent/child closure evidence so FlowGuard result acceptance,
  packet outcome, work-order decision, evidence artifact, reviewer authorized
  reads, reviewer manifest, and system validation cannot disagree silently.
- Extend break-glass loop detection to track stable root-cause identity across
  changing surface blocker classes when the same control-plane evidence chain
  repeats without repair progress.
- Keep synthetic and matrix evidence classified as control-plane regression
  evidence only; it does not become live target-project completion evidence.

## Capabilities

### New Capabilities
- `flowpilot-contract-exhaustion-mesh`: Current-contract matrix generation,
  oracle expectations, and FlowGuard/TestMesh evidence for finite FlowPilot
  control-plane packet, result, evidence, reviewer, repair, and loop surfaces.

### Modified Capabilities
- `synthetic-agent-coverage-matrix`: Synthetic coverage must consume the
  contract-exhaustion matrix and expose missing generated branch owners.
- `flowguard-layered-boundary-coverage`: Layered proof must include parent
  closure cells for FlowGuard result/work-order/evidence/reviewer/system
  validation consistency.
- `controller-break-glass-repair`: Break-glass eligibility must include
  repeated same-root-cause control-plane loops even when the surface blocker
  family changes.
- `model-test-code-diagnostic-gap-closure`: Diagnostics must report
  contract-exhaustion gaps, stale matrix evidence, and code/test binding gaps.

## Impact

- FlowPilot runtime control-plane code under
  `skills/flowpilot/assets/flowpilot_core_runtime/` and related facades.
- FlowPilot runtime tests under `tests/`, especially packet/result,
  FlowGuard evidence, reviewer, blocker, and break-glass tests.
- FlowGuard simulation runners and result artifacts under `simulations/`.
- OpenSpec specs and tasks for current-contract control-plane coverage.
- Installed FlowPilot skill sync and install validation after implementation.
