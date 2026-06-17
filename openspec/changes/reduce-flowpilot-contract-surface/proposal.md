## Why

FlowPilot's recent hardening added useful capabilities, but the packet/result
surface became too wide: fields, final evidence obligations, and role checks
now leak across lifecycle stages. Historical run
`WorldGurd_20260613/.flowpilot/runs/run-20260613-140526` shows a successful
mainline route shape, while later runs show that added terminal, test, and
model-report requirements can block early packets for evidence that belongs to
later stages.

This change contracts FlowPilot back to one clear lifecycle path per packet
family. It keeps the useful later additions only where they are necessary:
acceptance items, route parent/child ownership, Reviewer blocking authority,
FlowGuard model evidence, PM disposition, parent replay, and terminal replay.

## What Changes

- **BREAKING**: Replace wide packet-result contracts with per-stage minimal
  contracts. A field is either kept in exactly one stage, moved to exactly one
  later stage, or deleted from the current contract.
- **BREAKING**: Replace multi-field PM disposition acceptance arrays with a
  single `acceptance_item_disposition[]` table.
- **BREAKING**: Remove FlowGuard model-detail fields from the FlowGuard result
  body. FlowGuard model details live only in the packet-owned run-local
  `flowguard_evidence.json`; the result body carries the PM-facing decision.
- **BREAKING**: Remove Reviewer report helper fields that duplicate Runtime
  mechanics or FlowGuard modeling. Reviewer keeps blocking authority through
  fixed blocker classes and findings.
- Promote the stage/evidence matrix into the single stage contract authority:
  each packet family declares current required fields, moved fields, deleted
  fields, allowed blocker classes, and fixed blocker-class next actions.
- Keep Runtime mechanical only. Runtime validates packet/result identity,
  field shape, currentness, blocker enum membership, and blocker next-action
  mapping; it does not judge quality, model truth, or evidence sufficiency.
- Keep FlowGuard responsible for modeling. FlowGuard self-repairs small model
  and test-obligation gaps in its own evidence file instead of making PM
  pre-fill FlowGuard model fields.
- Keep Reviewer blocking power. Reviewer can block current-stage quality,
  evidence, and completion issues, but must choose a current-stage blocker
  class and fixed next action.
- Keep parent/child route ownership and acceptance-item assignment at planning
  stage. Keep final closure strict at terminal replay stage.
- Delete old fallback and compatibility surfaces from the new contract:
  aliases, wrapper guessing, newest-run fallback, repo-root fallback,
  historical result promotion, old packet evidence, manual fallback blocker
  evaluation, and target-project dependency on FlowPilot development scripts.

## Capabilities

### New Capabilities

- `flowpilot-contract-surface-reduction`: Defines the contracted packet
  lifecycle, keep/move/delete field rules, fixed blocker enum mapping, and
  all-packet validation coverage for the current FlowPilot runtime.

### Modified Capabilities

- `flowpilot-packet-review-flow`: Review and FlowGuard packets use
  stage-owned contracts and fixed blocker classes instead of broad report
  bodies.
- `blocker-repair-policy`: PM repair routing consumes fixed blocker classes and
  fixed handling routes, while PM keeps the finite structured repair-branch
  decision instead of inheriting role-authored freeform repair shapes.
- `formal-gate-review-standards`: Reviewer gates remain blocking, but their
  blocker classes are stage-owned and cannot demand future-stage evidence.
- `historical-live-run-replay-package-suite`: Historical replay must prove the
  2026-06-13 successful mainline stays passable and later first-packet failure
  is covered as one regression among all packet families.

## Impact

- Runtime and contracts:
  `skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py`,
  `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`,
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Role and phase prompt cards:
  FlowGuard operator, human-like Reviewer, Project Manager, PM FlowGuard
  request/report loop, node acceptance plan, route skeleton, repair, and
  Reviewer/FlowGuard child cards.
- FlowGuard models and evidence:
  FieldLifecycleMesh, Architecture Reduction, Model-Test Alignment,
  ContractExhaustionMesh, TestMesh, information-flow alignment, and historical
  replay evidence.
- Tests:
  stage matrix, packet result contracts, Reviewer stage boundaries, FlowGuard
  self-repair evidence, no-fallback surfaces, historical live replay, PM
  repair/disposition contracts, and parent/terminal replay contracts.
- Install and sync:
  local installed skill sync, install checks, smoke checks, topology rebuild,
  Meta and Capability regressions.
