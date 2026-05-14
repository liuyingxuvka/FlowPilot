# FlowPilot Requirement Traceability Upgrade Plan

## Risk Intent Brief

This change uses FlowGuard before production edits because it changes the way
FlowPilot carries user requirements through product architecture, root
acceptance, route design, node acceptance, route mutation, child-skill gates,
and final closure. The protected harms are silent requirement loss, fake
closure by report-only evidence, stale evidence after route mutation, external
tool output becoming authority without PM import, and accidentally introducing
light/simple FlowPilot profiles.

FlowPilot remains standalone. OpenSpec-style ideas are used only as design
principles: stable requirement ids, change status, source trace, supersession,
impact analysis, and final closure trace. FlowPilot does not call, require, or
delegate authority to OpenSpec, OpenSpark, SparkKey, or any other installed
tool.

## Ordered Upgrade List

| Order | Existing FlowPilot Area | Current Shape | Upgrade | Concrete Artifact Changes | Done When |
| --- | --- | --- | --- | --- | --- |
| 1 | Product-function architecture | PM already maps tasks, capabilities, low-quality risks, semantic fidelity, and acceptance matrix. | Add a stable requirement-trace spine at the product layer. | Add `requirement_trace`, `source_requirement_ids`, and trace links from user tasks, capabilities, feature decisions, low-quality risks, and functional acceptance items. | Every important user/PM hard requirement has a stable id before root contract drafting. |
| 2 | Root acceptance contract | Root requirements already exist with proof requirements and scenario pack. | Add explicit change status and source provenance. | Each root requirement records `source_requirement_ids`, `change_status`, optional `supersedes_requirement_ids`, `changed_reason`, and approval owner. Proof matrix must point back to the same ids. | Root requirements cannot appear, disappear, or change meaning without a recorded source and status. |
| 3 | Route skeleton | Route nodes already carry gates, decomposition policy, and complexity review. | Make route nodes explain requirement ownership. | Each node records `covers_requirement_ids`, `covers_scenario_ids`, `source_product_capability_ids`, `why_this_node_exists`, `why_not_merged`, and `why_not_split`. Route-level policy states formal FlowPilot always uses the full protocol. | Every route node exists for a specific requirement/risk/proof boundary, and no light/simple profile can weaken the run. |
| 4 | Node acceptance plan | Node plans already inherit root requirements, child-skill standards, experiments, and advance gates. | Bind node closure evidence directly to requirement ids. | Node requirements, inherited root requirements, experiments, work packets, and child-skill bindings carry `covers_requirement_ids` / `source_requirement_ids`; advance gate requires all covered ids closed or explicitly triaged. | A node cannot close unless its own covered requirements have direct evidence or a PM-approved disposition. |
| 5 | Route mutation and repair | Mutations already invalidate affected stale evidence after reviewer blocks. | Make mutation impact explicit by requirement id. | Mutation records list impacted requirements, impacted nodes, stale evidence ids, rerun models/checks, and superseded requirement relationships. | Changed or superseded requirements cannot be closed by old evidence. |
| 6 | Final route-wide gate ledger | Final ledger already scans route gates, evidence, residual risk, generated resources, and terminal backward replay. | Add route-wide requirement closure table. | Add `requirement_trace_closure` with one row per effective root requirement and covered product requirement. Each row names owner nodes, evidence, direct checks, stale status, waiver authority, and unresolved state. | Completion is allowed only when every effective requirement is resolved, superseded with reason, or explicitly waived by required authority. |
| 7 | Router validation | Router validates several artifact families and final ledger/root replay. | Enforce trace fields on the highest-risk artifacts. | Add or strengthen validation for node acceptance plans and final ledgers first; then extend product/root/route validation where CLI artifact validation already fits. | Invalid traceability artifacts fail before they can become route authority. |
| 8 | Local install sync | Repo templates/cards and installed skill can drift. | Sync after validated edits. | Run local install/sync checks, then sync repo-owned FlowPilot skill files to the local installed skill copy. | Local repo and installed FlowPilot agree without pushing remote GitHub. |

## Risk And Bug List

| Risk Id | Possible Bug | Why It Matters | FlowGuard Coverage |
| --- | --- | --- | --- |
| R1 | Product architecture creates hard tasks or capabilities without stable requirement ids. | Later route and final ledger cannot prove the user's original intent was preserved. | `product_trace_required_after_product_phase` catches missing registry, unstable ids, and unmapped product items. |
| R2 | Root contract changes requirement meaning without source or delta status. | A changed requirement can look like the original acceptance floor. | `root_trace_required_after_root_phase` catches missing source ids, change status, supersession, and proof-matrix links. |
| R3 | Route node references no requirement or an unknown requirement. | Work can be done because it looks plausible, not because it serves the contract. | `route_trace_required_after_route_phase` catches missing/invalid coverage links. |
| R4 | Route node exists without explaining why it is separate. | The route may bloat or split work without proof value. | `route_trace_required_after_route_phase` catches missing node rationale, merge/split reasoning, and profile weakening. |
| R5 | Node acceptance closes by generic evidence rather than mapped root/scenario/product behavior. | Report-only or existence-only proof can hide incomplete work. | `node_trace_required_after_node_phase` catches missing inherited ids, experiment coverage, child-skill trace, and direct evidence mapping. |
| R6 | Route mutation changes scope but does not invalidate stale evidence or rerun models/checks. | Old evidence can falsely close new work. | `mutation_trace_required_after_mutation_phase` catches missing impact lists, stale invalidation, rerun obligations, and supersession protection. |
| R7 | Superseded requirement is closed by old evidence. | Final state can claim completion for a requirement that no longer exists in that form. | `mutation_trace_required_after_mutation_phase` catches old evidence reuse against superseded requirements. |
| R8 | Final ledger claims completion while a requirement remains unresolved. | FlowPilot can finish with a missing user requirement. | `final_trace_required_at_completion` catches unresolved effective requirements and missing closure rows. |
| R9 | External OpenSpec/OpenSpark/SparkKey output becomes route authority. | FlowPilot stops being standalone and may trust a tool not present on another machine. | `standalone_authority_preserved` catches external authority without PM import approval. |
| R10 | A light/simple FlowPilot profile is introduced for small tasks. | User explicitly requires FlowPilot to mean the full protocol. | `full_protocol_only` catches light profile or simple-profile waivers. |
| R11 | Child-skill stricter requirements lose the trace link. | A selected skill can require evidence that never appears in node or final closure. | `node_trace_required_after_node_phase` catches dropped child-skill requirement bindings. |
| R12 | Final ledger relies on file existence instead of direct evidence and reviewer/officer checks. | Completion becomes clerical instead of proof-backed. | `final_trace_required_at_completion` catches existence-only closure. |
| R13 | Router-invented or non-router-authorized events create trace outputs. | Trace artifacts could bypass FlowPilot's control plane. | `router_authority_for_trace_events` catches trace outputs without router-owned event authority and validation. |

## FlowGuard Pre-Implementation Gate

Before production edits, run:

```powershell
python simulations\run_flowpilot_requirement_traceability_checks.py --json-out simulations\flowpilot_requirement_traceability_results.json
```

The check must prove both sides:

- all known-bad hazard states above fail with the expected invariant; and
- the intended staged upgrade plan reaches completion with no invariant
  failures, no dead branches, and all required labels reached.

## Implementation Slices

| Slice | Files | Verification After Slice |
| --- | --- | --- |
| A | Add FlowGuard model and this plan document. | Run requirement-traceability checks and compile new Python files. |
| B | Product/root/route/node/final templates. | Rerun requirement-traceability checks; inspect JSON templates parse successfully. |
| C | PM/reviewer/officer cards. | Rerun focused text/schema checks and requirement-traceability checks. |
| D | Router validation for node/final traceability. | Run router artifact validation tests and compile router. |
| E | Existing capability/meta checks and install sync. | Run `run_capability_checks.py`, `run_meta_checks.py`, local install check/sync, and git status review. |

## Explicit Non-Goals

- Do not require OpenSpec, OpenSpark, SparkKey, or any external planning tool.
- Do not create a separate Change Pack that duplicates existing PM/root/route
  artifacts.
- Do not add light, medium, or small-task FlowPilot modes.
- Do not push to remote GitHub in this task.
