## Context

FlowPilot's current-contract runtime already has the correct architectural spine: Runtime/Router owns mechanics, PM owns product/route/acceptance/integration, substantive roles return sealed results, FlowGuard checks process/state risks, Reviewer judges quality, and PM chooses repair or progression. The upgrade therefore contracts and strengthens this spine instead of replacing it.

The current drift has four connected causes:

1. Route-decomposition wording treats a leaf as a very small outcome and treats Worker planning as leakage. This protects PM authority but can reduce a capable AI to a shallow micro-task executor.
2. Role cards require self-check and in-scope repair but do not make the role's own numbered execution plan and completion status a visible part of every report.
3. `task.discovery` and older material cards combine mandatory local-skill discovery with mandatory material scan/sufficiency semantics, producing a special stage even when ordinary PM reading or a normal work package is sufficient.
4. Existing fake-AI and Cartesian infrastructure is broad but does not yet make complete-workstream semantics and honest finite-universe accounting the direct owner of the new obligations.

The repository is concurrently completing `restore-flowpilot-test-evidence-closure`. This change consumes that canonical fake-AI/background evidence work and must not create a second evidence framework. The real FlowGuard engine is required; project adoption must be upgraded to the installed engine before final confidence.

## Goals / Non-Goals

**Goals:**

- Make each substantive AI role perform one complete, bounded, high-standard workstream rather than a token task.
- Make the role's own plan and plan execution auditable in its existing result body.
- Preserve PM global authority while allowing serious local Worker planning, delegation, verification, and repair.
- Remove mandatory special material processing while retaining mandatory local capability/skill discovery.
- Preserve independent FlowGuard and Reviewer assurance and allow risk-triggered role-local FlowGuard without self-approval.
- Prove the change through the existing real packet/result path, canonical fake responder, finite contract mesh, ordinary tests, MTA, TestMesh, ModelMesh, topology, SkillGuard, and background evidence.

**Non-Goals:**

- No light/simple FlowPilot mode; direct AI use remains the answer for ordinary small tasks.
- No second route tree, project constitution, role plan ledger, result family, controller workflow, reviewer family, or compatibility parser.
- No Runtime semantic judgement of plan quality or report completeness.
- No universal per-leaf pre-worker FlowGuard model.
- No claim that finite fake-AI enumeration proves arbitrary natural-language intelligence or future model behavior.
- No automatic product/acceptance/route changes by Worker, Reviewer, FlowGuard Operator, or Controller.

## Decisions

### 1. One semantic complete-workstream contract, projected through existing prompts

Every substantive AI role receives the same semantic lifecycle:

`understand -> numbered plan -> risk/FlowGuard decision -> execute/delegate -> integrate -> verify -> self-repair -> submit`.

The shared packet output prompt and each role card define the lifecycle. Role-specific cards add authority boundaries. Controller is excluded because its current foreground action ledger is machine-owned coordination rather than substantive project work.

The result body records a `Workstream Plan and Completion` subsection inside the existing `Contract Self-Check` section. Each row contains a stable step number, intended outcome, status (`completed`, `partial`, `blocked`, or `not_started`), evidence refs, and deviation/reason. The section also records delegation integration, verification performed, unresolved items, and whether the final claim matches the completed steps.

Runtime does not reject a result merely because this semantic subsection is weak or absent. Reviewer checks it against the actual artifact and evidence. This preserves the mechanical/semantic split and avoids a second plan authority.

Alternatives rejected:

- A new top-level required result field or plan schema: too mechanical and would enlarge all result families.
- A run-level role plan ledger: duplicates result evidence and creates a second state owner.
- Prompt-only planning with no returned trace: not auditable and cannot expose shallow completion.

### 2. Leaf means complete accountability, not micro-action

PM continues to own route decomposition, product intent, acceptance, dependencies, and cross-node integration. A route leaf is redefined as the smallest independently accountable workstream that can be assigned to one role with a coherent outcome and proof boundary. It may contain multiple local execution steps, internal checks, bounded helper delegation, and repair iterations.

Worker local planning is valid when it implements the already accepted packet. It becomes a PM-level leak only when Worker must invent product scope, route nodes, acceptance criteria, dependency order outside the packet, or cross-role authority. Reviewer evaluates both under-decomposition and fragmentation.

### 3. PM receives an explicit project operating posture

The PM core card and startup/planning cards state that FlowPilot is for long, complex, high-standard projects. PM must establish target quality, hard failure bar, architecture, proof strategy, integration touchpoints, and closure runway. PM must disposition all Reviewer quality scores below 9/10: repair, accept with explicit rationale where the hard contract is met, route additional work, waive with authority, or stop. A sub-9 score is not itself a Runtime hard block, but silent disregard is invalid PM integration.

### 4. Keep `task.discovery`; narrow its authority

The current family id remains `task.discovery`. Its sole mandatory purpose becomes local capability/skill/environment discovery for planning. Runtime enumerates current candidate skill paths and basic availability into the existing packet body; PM classifies candidates and returns `decision` plus `candidate_skill_inventory`. Only selected skills proceed to existing `task.skill_standard` deep reading and role-skill bindings.

The current positive fields `material_sources` and `material_sufficiency` are removed from `task.discovery`, their validators, skeletons, stage matrix, fake responses, model obligations, and positive tests. They remain only in explicit forbidden/deleted-field registries, negative tests, or historical labels.

No replacement material form is added. PM reads ordinary non-sealed project material directly. When deeper reading, external research, experiment, or source verification requires separate work, PM uses the existing ordinary role-work request/batch and normal result/disposition/review path. Reviewer material/source checking is risk-triggered by the ordinary work's acceptance needs rather than a mandatory startup gate.

### 5. Material artifact map becomes optional derived navigation

The map may still be generated when a long project benefits from source navigation, but its absence cannot block startup, planning, route activation, node work, or closure. When present it remains index-only and cannot grant sealed-body access or prove sufficiency. Mandatory material-map creation, special package release, and dedicated material-sufficiency Reviewer expectations are removed.

### 6. FlowGuard is both a role tool and an independent boundary authority

Any substantive role may invoke role-local FlowGuard for process/state/coverage risk within its authorized workstream and cite the resulting evidence in its report. The same role cannot use that model as approval of its own result. Formal independent FlowGuard remains required at existing named boundaries: product architecture, route creation or structural mutation, post-result where modeled, model miss, parent composition, and terminal coverage/closure. A normal leaf does not gain a second mandatory pre-worker model.

### 7. Extend the canonical fake responder, not the result-family surface

`ContractDrivenFakeAIResponder.from_open_packet_result` remains the sole fake response construction path. Semantic profiles mutate the opened packet result and report content while the real runtime still owns packet open, mechanical validation, submit, PM disposition, FlowGuard, review, repair, and retry.

Required profiles include complete plan/pass, missing plan, vague plan, incomplete step claimed complete, blocked step disclosed, evidence mismatch, stale evidence, delegation unintegrated, role-local FlowGuard used as self-approval, Reviewer under-9 PM disposition, corrected retry, ordinary material work package, and mandatory skill inventory with selected-skill deep read.

### 8. Finite coverage accounting is explicit and non-inflating

The coverage universe records separate counts and ids for declared, applicable, excluded with reason, generated, selected, executed, passed, failed, stale, and proof-backed cases. Static finite contract values are exhaustively enumerated. Every single-axis mutation runs at the real owner. Public-path coverage uses deterministic pairwise combinations plus named high-risk triples and selected four-way combinations. Historical misses, bounded fuzz, fake projects, and sampled live-AI outputs are separate evidence classes.

No parent receipt can claim more proof-backed cases than its current child artifacts demonstrate. Stale or skipped children remain visible.

### 9. Model-first implementation order

The change updates the owning FlowGuard models before prompt/runtime edits:

- Behavior Commitment Ledger for every externally visible behavior and removal.
- DevelopmentProcessFlow for staged implementation, peer writes, evidence freshness, install sync, and final claims.
- Architecture Reduction for the special material path and stale dual-model wording.
- FieldLifecycleMesh for removed discovery fields and new packet-only inventory projection.
- ContractExhaustionMesh for semantic profiles and finite combinations.
- Model-Test Alignment, TestMesh, and ModelMesh for direct evidence ownership and parent freshness.

The large `capability_model.py` and `meta_model.py` consume focused child model results rather than absorbing another parallel state family.

## Risks / Trade-offs

- **Semantic plan evidence may be fabricated or generic** -> Reviewer compares every step with current artifacts, commands, evidence freshness, and deviations; fake profiles prove shallow-plan rejection.
- **Worker planning may drift into PM authority** -> Role cards and Reviewer distinguish local execution steps from product/route/acceptance decisions; the existing `needs_pm` and route mutation paths remain the only escalation.
- **Removing material gates may hide genuine source risk** -> PM assesses evidence needs inside ordinary planning and work packages, applies risk-triggered review when warranted, and preserves final source-intent and closure checks without creating another form.
- **Material removal touches many historical/legacy surfaces** -> Architecture Reduction classifies each hit as delete, negative/historical retain, or current generic material access; unsupported positive paths receive negative tests.
- **Concurrent predecessor work may be overwritten** -> Recheck timestamps/diffs before each overlapping edit, consume its canonical fake/background changes, and do not stage unrelated files.
- **Full regressions are slow** -> Run focused checks first, freeze a source fingerprint, then run isolated bounded background parents with final artifacts; source changes invalidate rather than silently reuse evidence.
- **Final confidence can become circular evidence** -> Keep one acyclic dependency graph: all/adversarial/release artifacts compile into TestMesh, strict parents consume the manifest, and repository final confidence runs last; active-run terminal return remains owned by that run's final-preflight.
- **FlowGuard project version may change during work** -> Verify module file and package version before model and final phases, run official project-upgrade after suite visibility is resolved, and rerun affected evidence.

## Migration Plan

1. Let the active predecessor evidence-closure run settle; classify its final artifacts as predecessor evidence only.
2. Complete FlowGuard project preflight and canonical suite visibility, then upgrade project records with the official tool.
3. Add focused complete-workstream/ordinary-resource models and executable checks; update parent model mesh and topology ownership.
4. Narrow `task.discovery` and remove material-positive fields in one current-contract change with no alias or fallback.
5. Update shared/role prompts, cards, result skeletons, Reviewer challenges, and PM integration guidance.
6. Remove dedicated material-scan/sufficiency positive routes; route additional material work through existing ordinary role work.
7. Extend the canonical fake responder, finite coverage generators, MTA, TestMesh, ModelMesh, and ordinary tests.
8. Run focused checks and foreground parents; freeze source; run background all, formal-submit-adversarial, and release; compile TestMesh; run strict parent consumers; then run repository final-confidence, Meta, and Capability regressions and repair every owner failure.
9. Rebuild topology, refresh SkillGuard evidence, update version/docs, sync the installed FlowPilot serially, and prove source/install digest parity.
10. Verify and archive OpenSpec only after current evidence passes; create a scoped local Git commit without unrelated/user-owned artifacts.

Rollback is a normal Git revert of this single current-contract change before public release. Runtime compatibility aliases are not retained. If rollback is required after local install sync, reinstall the selected source revision rather than teaching Runtime to accept both contracts.

## Open Questions

No product-direction questions remain. Implementation may choose the smallest existing prompt/card insertion points and the narrowest focused model partition, provided the single-authority and evidence rules above remain intact.
