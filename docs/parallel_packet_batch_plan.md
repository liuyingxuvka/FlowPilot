# Current Parallel Packet Work Contract

## Status

This document describes the current single FlowPilot path. It is not a plan to
add a universal `parallel_packet_batch` ledger or a second batch runtime.
Parallel work reuses the packet, result, review, PM-disposition, blocker, and
route-node records that already own the relevant work family.

## Current owners

| Work kind | Current owner and path | Join and advance rule |
| --- | --- | --- |
| Research or source verification | Existing PM research package and research packet/result reconciliation | PM absorbs every required current result; risk-appropriate Reviewer or FlowGuard checks use the ordinary review path before any dependent route decision. |
| Current-node implementation | Existing current-node packet/result family and write-grant boundary | Every packet remains bounded by the accepted node contract; PM integrates accepted results before node completion. |
| PM role work | Existing PM role-work request/batch, result, and disposition records | PM records a disposition for every required returned result before the request closes. |
| FlowGuard modeling | Existing FlowGuard Operator packet/result and formal gate surfaces | Role-local modeling is advisory; formal independent FlowGuard and Reviewer authority remains unchanged. |
| Available project material | Ordinary PM reading or an ordinary research/source-verification work package | No dedicated material phase, result family, sufficiency gate, or mandatory artifact map exists. |

The PM may issue work in parallel only when every packet can start inside the
current Router-authorized scope. Each substantive role writes its numbered
local workstream plan, executes and integrates its bounded delegation, verifies
the result, repairs in-scope defects, and reports per-step completion through
the existing result body. Router enforces mechanical packet identity and
currentness; Reviewer audits substantive completeness against actual artifacts
and evidence.

## Current invariants

- A role cannot infer route advancement, product acceptance, or batch
  completion from its own packet.
- Partial results cannot be projected as completed PM integration.
- Reviewer and formal FlowGuard decisions remain independent of role-local
  self-checks.
- Controller handles envelopes and Runtime-derived foreground actions; it does
  not read sealed bodies or invent a substantive plan.
- Missing material reading, research, experiment, or source verification is an
  ordinary PM-selected work package, not a mandatory startup gate.
- An optional material artifact map is navigation only and cannot satisfy an
  acceptance or evidence gate.

## Retired positive surfaces

The former `pm.material_scan`, `worker.material_scan`,
`worker_material_scan_result`, `reviewer.material_sufficiency`, dedicated
material repair/reconciliation actions, and material-intake templates are
retired current-contract names. They may appear only in negative tests,
forbidden/deleted lists, or explicitly historical diagnostics. Runtime must
reject them rather than translate, default, or route them through an alternate
success path.

## Validation ownership

FlowGuard models partial-result, stale-evidence, duplicate-authority,
self-approval, and route-advance hazards. Ordinary tests exercise the real
packet/result/review APIs. Acceptance TestMesh compiles current frozen-source
all, adversarial, and release artifacts; strict parent checks consume that
proof before repository final confidence runs as the terminal consumer.
