## Context

The current FlowPilot contract is intentionally new-only and single-route. Runtime owns mechanical hard gates, FlowGuard owns process/state modeling, PM owns route/repair decisions, and Reviewer owns quality review. The existing `recursive-route-parent-entry` spec already requires parent/module nodes to be entered before descendants, and PM route-model guidance already requires a local entry loop before child execution.

The observed failure is narrower: after one node completes, runtime can choose a later sibling parent/module, call the nonworker scope handler first, set the parent to `awaiting_children`, move the frontier to the first child, and open the child's node plan. The parent therefore never becomes the active node long enough to get its own accepted `node_acceptance_plan` and `node_context_package`.

## Goals / Non-Goals

**Goals:**

- Enforce the existing node-entry gate for every selected effective node, including parent/module nodes, before child descent.
- Provide a single hard-gate escape return path that freezes final dispatch, identifies the first leaked owning gate, returns to that normal gate, and reruns affected downstream evidence.
- Preserve final backward review as a quality/composition review, not a hard-gate audit.
- Upgrade existing FlowGuard model and TestMesh coverage so this miss and same-class cases are represented explicitly.
- Sync repository source to the installed FlowPilot skill and prove source/installed digest equality before final confidence.

**Non-Goals:**

- No fallback, compatibility shim, legacy alias, backfill, or alternate controller path.
- No new Reviewer duty to inspect runtime hard gates.
- No third node-entry artifact beyond the existing `node_acceptance_plan` and `node_context_package`.
- No broad redesign of route mutation or terminal closure beyond the affected hard-gate return path.

## Decisions

### Decision 1: Make node-entry gating the only preventive fix

Runtime should check the selected node itself before `_enter_nonworker_route_scope` can descend into children. If the selected node lacks a current accepted node plan/context, the runtime keeps the frontier on that node and issues the normal node-acceptance-plan packet.

Alternative considered: add extra blocker handling in parent replay, PM disposition, and final dispatch. Rejected because that makes the late stages look like fallback defenses. Late stages may assert impossible state only.

### Decision 2: Use `control_plane_hard_gate_escape` as a return-to-owner signal

Final-dispatch preflight should not continue into Reviewer when hard-gate evidence is missing. It should classify the leak as `control_plane_hard_gate_escape:<gate_type>:<subject_id>`, record the attempted action and owning normal gate, and return the frontier to the gate that should have owned the work.

Alternative considered: let final closure or Reviewer collect missing evidence. Rejected because final review must remain quality-oriented and cannot repair runtime ordering.

### Decision 3: Keep existing artifacts and cards as the source of truth

The implementation should reuse `route_nodes[].node_acceptance_plan_id`, `route_nodes[].node_context_package_id`, `node_acceptance_plans`, `node_context_packages`, parent replay packets, PM disposition packets, and terminal/final review packets. Prompt-card changes should clarify ownership and ordering, not add result fields unless runtime evidence requires them.

Alternative considered: add a separate parent-entry ledger. Rejected because the existing plan/context artifacts already express the hard gate.

### Decision 4: Prove with model-backed Cartesian coverage

The observed miss is a same-class control-plane ordering bug, not a one-off ledger defect. Coverage must include first parent, later sibling parent, nested parent, mutation-created parent, and repair replacement parent across missing/open/stale/current gate states and across child descent, parent replay, PM disposition, final dispatch, and close-project attempts.

Alternative considered: one regression test for the observed sibling parent. Rejected because previous tests missed the sibling/late-entry class.

## Risks / Trade-offs

- [Risk] A late assertion could be mistaken for a recovery path. -> Mitigation: code, cards, and specs must state that late stages freeze and return to the owning normal gate without backfill.
- [Risk] Existing final-ledger logic may already build broad blocker lists. -> Mitigation: final-dispatch preflight should remain thin and mechanical; Reviewer quality packets are issued only after it passes.
- [Risk] Broad router tests are slow. -> Mitigation: add focused unit/fake-E2E/model checks first and run router tier/background checks with final artifact inspection for broad confidence.
- [Risk] Installed skill can remain stale after source edits. -> Mitigation: run repository-owned install sync and digest audit, then compare source and installed digests.
