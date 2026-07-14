# FlowGuard Existing-Model Preflight

## Decision

This change reuses the current `flowpilot_new.py` / core-runtime authority and
the existing FlowGuard parent models. It adds two focused child models only
where the existing parents are intentionally too broad to provide direct
counterexample evidence. It does not introduce a second runtime, route tree,
report family, plan ledger, material ledger, or approval chain.

## Current primary owners

| Behavior or risk | Existing primary owner | Change route | Duplicate-boundary decision |
|---|---|---|---|
| Long-project quality posture, PM architecture, route decomposition, Worker authority, integration and closure | `simulations/flowpilot_planning_quality_model.py` | Extend parent obligations and add the focused `flowpilot_complete_workstream_orchestration` child | The child owns only role-local lifecycle counterexamples; the parent remains the project/route quality owner. |
| Current packet/result mechanics and preplanning sequencing | `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py` and `packet_result_contracts.py` | Narrow the existing `task.discovery` family and project workstream guidance through existing packet/handoff surfaces | No new packet/result family or gate. |
| Current field ownership, removed-field rejection, readers/writers and terminal disposition | `simulations/flowpilot_field_contract_model.py` | Add retained/removed discovery and semantic-report rows | No separate field registry. |
| External behavior registration and one primary path per behavior | `simulations/flowpilot_053_ppa_maintenance_model.py` | Extend the existing Behavior Commitment Ledger | No second commitment ledger. |
| Mandatory shallow local skill inventory and selected-skill deep reading | `simulations/capability_model.py` plus current discovery/skill-standard packets | Add the focused `flowpilot_ordinary_resource_discovery` child, then update the existing capability parent | Inventory is packet input; PM selection remains the existing result/skill-standard path. |
| Ordinary evidence, reading, research or experiment work | Existing PM role-work request/batch, role-work result and PM disposition path | Reuse ordinary work packages and risk-appropriate existing FlowGuard/Reviewer review | No special material packet, material sufficiency result, or material gate. |
| Optional material navigation index and sealed-source access | Existing material-access/index behavior | Keep optional and non-authoritative when present | Absence cannot block planning, execution or closure. |
| Formal independent FlowGuard boundaries | `simulations/flowpilot_prework_flowguard_gate_model.py` and current core review routing | Preserve product, route/mutation, applicable post-result, model-miss, parent and terminal boundaries | Role-local modeling is advisory evidence and never self-approval. |
| Reviewer stage scope and semantic quality challenge | `review_window_contracts.py`, core review packets and existing high-standard tests | Add plan-execution audit guidance to existing Reviewer window/report fields | No plan-review result family. |
| Canonical fake AI | `simulations/flowpilot_contract_driven_fake_ai.py` | Add semantic profiles only through `ContractDrivenFakeAIResponder.from_open_packet_result` | Standalone fake dictionaries remain forbidden. |
| Finite contract coverage | Existing ContractExhaustionMesh, current Cartesian matrix, MTA, Acceptance TestMesh and ModelMesh | Add workstream/resource rows and receipts to the existing parents | Each parent keeps its present evidence authority. |
| Tier freshness, background evidence and final claims | Existing test-tier runner, DevelopmentProcessFlow ownership and source fingerprint machinery | Register focused checks and rerun parents after source freeze | Predecessor evidence is diagnostic only after covered source changes. |
| Install/release parity | Existing installer, install audit, SkillGuard, topology and release checks | Serial source-to-install sync after source freeze | No concurrent install/audit or newest-run fallback. |

## Function-boundary summary

Every substantive role uses one shared lifecycle:

`bounded assignment x current role state -> {numbered local plan, execution and integration, verification, self-repair, role-authored report}`.

The PM remains the owner of product ambition, route shape, cross-node ordering,
acceptance boundaries and final integration. Workers may plan the internal
execution of one independently accountable workstream, but may not create new
product scope, route nodes, cross-node dependencies or acceptance authority.
The Controller continues to expose only the Runtime-derived foreground action
ledger.

## Evidence freshness and peer-write disposition

The predecessor `v0.12.0-all` supervisor became orphaned: its process ended
without final supervisor exit metadata, one completed child failed, and its
covered-source fingerprint predates this change. Its individual artifacts are
retained as diagnostic evidence only. No pass claim in this change may reuse
that parent run. All required parent checks will be restarted after the final
covered-source freeze.

