# Architecture Reduction Evidence

## Review Boundary

This evidence belongs to the `reduce-flowpilot-contract-surface` change. It
uses ArchitectureReduction to decide which accumulated FlowPilot contract
surfaces are current behavior, which are prompt/model/test debt, and which are
deleted instead of preserved through compatibility paths.

The observable contract is:

- Runtime/router accepts one current packet/result contract per family.
- Runtime/router validates mechanical shape, current ids, route scope,
  blocker enum membership, fixed blocker handling route, and forbidden old
  fields.
- FlowGuard writes model/process/evidence-detail findings into the current
  run-local evidence surface and compact PM-facing result body.
- Reviewer reviews current-stage quality and blocks only with a current-stage
  blocker class allowed by the stage matrix.
- PM receives a fixed blocker handling route, then chooses one finite PM
  repair-decision branch from the current blocker context.
- Historical runs can explain why a rule exists, but cannot become current
  completion evidence.

## Model-To-Code Mapping

| Model responsibility | Current implementation surface | Contract action |
| --- | --- | --- |
| Stage/packet authority | `skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py` | Keep as the single matrix for required, moved, deleted, and blocker-owned fields. |
| Packet result shape | `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py` | Keep reduced result bodies and reject old aliases/wrappers. |
| Runtime mechanical gate | `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py` | Keep enum/shape/id/route validation; reject old or fallback-like submissions. |
| FlowGuard evidence detail | run-local `flowguard_evidence.json` contract | Keep as the single detailed model evidence body. |
| PM/Reviewer/FlowGuard prompts | `skills/flowpilot/assets/runtime_kit/cards/**` | Keep role-owned instructions only; remove duplicate gate or future-stage requirements. |
| Negative proof | contract-surface, cartesian, exhaustion, field, and model-test tests | Keep explicit rejection tests for deleted paths. |

## Compatibility Surface Classification

| Surface | Classification | Disposition |
| --- | --- | --- |
| Broad FlowGuard report body fields in compact result packets | `prune_candidate` | Removed from packet result bodies; detailed model evidence belongs in run-local evidence files. |
| Reviewer duplicate fields that restate FlowGuard/runtime checks | `prune_candidate` | Removed from Reviewer packet contract; Reviewer keeps current-stage quality and evidence authority. |
| PM disposition acceptance-item arrays | `prune_candidate` | Replaced by `acceptance_item_disposition[]`; old arrays are rejected, not translated. |
| Legacy aliases, wrappers, prose guessing, old packet families, old result promotion | `negative_legacy_test` | Must keep rejection tests; do not restore compatibility. |
| Newest-run and repo-root fallback discovery | `negative_legacy_test` | Rejected as current evidence authority; current run scope is required. |
| Manual fallback blocker evaluation | `negative_legacy_test` | Rejected; blockers must use fixed blocker classes and fixed handling routes. |
| Duplicate prompt language that asks FlowGuard Operator to do Reviewer quality gates | `prune_candidate` | Remove or rewrite as FlowGuard model/process review only. |
| Duplicate prompt language that asks early packets for final/worker evidence | `prune_candidate` | Remove or rewrite into the correct later-stage packet family. |
| `fallback_target_id` in repair-loop diagnostic family output | `prune_candidate` | Renamed to neutral `packet_subject_id`; it remains diagnostic grouping context, not a submission authority. |
| `subject_stage` as an information-flow marker for stage matrix source | `prune_candidate` | Replaced by the current matrix field `lifecycle_stage`; `subject_stage_evidence_matrix` remains the current packet body object name. |

## Reduction Candidates

| Candidate | Type | Proof status | Target action | Required next route |
| --- | --- | --- | --- | --- |
| Move FlowGuard model details out of PM-facing result bodies | `remove_state_field` | `safe_by_equivalence` | `remove` | FieldLifecycleMesh and Model-Test Alignment keep proving the compact body plus run-local evidence file. |
| Remove Reviewer duplicate FlowGuard/runtime check fields | `remove_duplicate_validation` | `safe_by_equivalence` | `remove` | Reviewer prompt tests and stage-matrix tests prove Reviewer keeps blocker authority without owning those fields. |
| Collapse PM disposition acceptance arrays into `acceptance_item_disposition[]` | `remove_state_field` | `safe_by_equivalence` | `remove` | Packet contract tests and runtime validation reject old arrays. |
| Reject old aliases, wrappers, old packet/result promotion, and fallback parsing | `remove_branch` | `safe_by_equivalence` | `remove` | ContractExhaustionMesh and cartesian tests keep negative coverage. |
| Remove broad-leaf wording that names a `fallback safety gate` | `remove_branch` | `safe_by_equivalence` | `remove` | Card instruction coverage now checks `route-depth safety gate`. |
| Collapse role prompts to role-owned duties | `remove_duplicate_validation` | `needs_conformance_replay` | `manual_review` | Historical live-run replay must still cover the named 2026-06-13 mainline and later failure across all families. |
| Rename repair-loop `fallback_target_id` diagnostic field | `remove_state_field` | `safe_by_equivalence` | `remove` | Runtime output now uses `packet_subject_id`, and regression tests assert the old diagnostic key is absent. |
| Rename information-flow stage marker from `subject_stage` to `lifecycle_stage` | `remove_state_field` | `safe_by_equivalence` | `remove` | Information-flow alignment and high-standard handoff tests prove the current matrix field is `lifecycle_stage`. |

## Hazard Review

- Existing model grounding is present through FieldLifecycleMesh,
  ContractExhaustionMesh, Model-Test Alignment, TestMesh, and the stage matrix.
- The observable contract is declared above and does not preserve old inputs.
- Model-to-code mapping is declared above before any contraction claim.
- Compatibility-like surfaces are classified; none are silently kept as valid
  current submissions.
- Negative legacy tests are retained as evidence and must not be deleted
  without replacement rejection evidence.
- Archive-only historical runs are process evidence only, not runtime
  completion authority.
- Public entrypoint behavior is not being changed by this review; public
  packaging/install sync remains outside this batch per current coordination.
- Risky or evidence-needed candidates remain visible as obligations instead of
  disappearing from the plan.

## Result

ArchitectureReduction supports the current-contract contraction already made
for broad report fields, duplicate gate language, and fallback/compatibility
surfaces. It does not authorize release confidence by itself. A follow-up
maintenance pass rebuilt and checked the topology, synced the local installed
FlowPilot skill, passed local install audit, passed the project install gate,
and added the named 2026-06-13 contract-surface baseline to the historical
live-run replay matrix. The remaining release boundary is target-workspace
smoke plus explicit release/archive actions.

Executable ArchitectureReduction review passed on 2026-06-17 for the completed
contraction candidates:

- `remove_prompt_fallback_safety_gate_wording`
- `rename_fallback_target_id_diagnostic`
- `remove_subject_stage_marker`

The review decision was `completed_reduction_candidates` with zero findings.

The same follow-up pass removed duplicate lifecycle helper definitions from
`simulations/capability_model.py` after detecting that the shadowed copy omitted
current-run isolation from the route-scaffold lifecycle predicate. Capability
and Meta full-fast parent checks passed afterward with release confidence
`current_with_layered_full_parent`.

Historical replay matrix coverage now includes the P0
`contract_surface_reduction_baseline` row for `run-20260613-140526`, the later
first-packet regression, and every mainline packet family.
