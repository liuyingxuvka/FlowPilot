# FlowPilot Node-Local Repair Upgrade Plan

Date: 2026-05-10

## Optimization Checklist

| # | Optimization | Concrete change | Acceptance signal |
|---|---|---|---|
| 1 | Make route mutation a semantic escalation, not the default reviewer-block response. | PM guidance must say that missing fields, unclear wording, incomplete matrices, missing evidence refs, malformed envelopes, and supplementable reports are node-local repair candidates first. | A PM can explain why the current node cannot contain the repair before choosing route mutation. |
| 2 | Allow same-node PM revision after node acceptance-plan blocks. | Router accepts a PM-revised node acceptance plan after reviewer block and sends it back to the same reviewer gate instead of forcing a new route node. | `reviewer_blocks_node_acceptance_plan -> pm_revises_node_acceptance_plan -> reviewer.node_acceptance_plan_review` is routable. |
| 3 | Allow worker or officer supplement/reissue as fresh work, not in-place mutation of old failed evidence. | PM guidance allows asking the original role to produce a new report/result based on the old artifact as context. The old blocked artifact remains stale context, not passing evidence. | Repair packets/results get a new generation and must be reviewed again before PM can complete the node. |
| 4 | Keep route mutation for route-level defects. | Route mutation remains available for missing product capability, wrong node boundary, wrong route topology, frozen contract impact, stale evidence that invalidates a segment, or work that the current node cannot semantically contain. | Route mutation records stale evidence, topology, return/supersede policy, and reopens route checks. |
| 5 | Put prompts only at the decision points that need them. | Update PM core principles, PM review-repair phase, and reviewer node-plan review. Avoid duplicating the rule across every card. | PM sees the rule in general decisions and at the exact repair point; reviewer classifies resolution without becoming PM. |
| 6 | Make FlowGuard catch the risky failure modes before runtime changes. | Extend the control-plane friction model with block classification, local repair, route mutation reason, fresh evidence, recheck, and routability states. | Hazard states for known bad paths fail, while the intended local-repair and route-mutation paths pass. |
| 7 | Verify and sync locally only. | Run targeted FlowGuard/router/install checks, then sync the installed local FlowPilot skill and commit locally. | Local repo, installed skill, and local git include the change; remote GitHub remains untouched. |

## Regression Risks To Catch

| # | Risk | What would go wrong | Required model/test coverage |
|---|---|---|---|
| 1 | Over-correction blocks real route mutation. | A route-level defect is incorrectly forced into a tiny local edit, leaving architecture or acceptance scope wrong. | Model hazard: route-invalidating block handled as same-node repair must fail. Router keeps route mutation path. |
| 2 | Node-local blocker still forces route mutation. | PM adds a repair node for missing wording, missing table rows, or other local plan/report defects. | Model hazard: node-local block mutated without a current-node-incapability reason must fail. |
| 3 | Router dead-end after reviewer block. | Same-node PM revision is allowed in prompts but no router event can receive it. | Model hazard: same-node repair path unavailable must fail. Router test must route revised plan to reviewer recheck. |
| 4 | Old failed evidence becomes accepted evidence. | A blocked report or plan is reused as if it passed after PM says "fixed." | Model hazard: stale blocked evidence used as passing evidence must fail. |
| 5 | Repair skips reviewer recheck. | PM revises or asks for a supplement, then proceeds without the same review class passing the new artifact. | Model hazard: same-node repair without reviewer recheck must fail. |
| 6 | Route mutation lacks a real escalation reason. | PM writes a new route version without saying why the current node could not contain the repair. | Model hazard: route mutation without current-node-incapability reason must fail. |
| 7 | Repair transaction is only a rerun label. | Packet reissue work is described in prose but not materialized into packet runtime files and ledger. | Existing model hazard remains: reissue specs not materialized must fail. |
| 8 | Prompt rule is duplicated too widely. | Many cards drift from one another and future changes become inconsistent. | Documentation and diff review: only PM core, PM repair phase, and reviewer node-plan review are changed. |
| 9 | Installed skill falls behind repo. | Local Codex continues to use old FlowPilot prompts/router even though repo was updated. | Run install sync and install check after tests. |

## FlowGuard Coverage Map

| Coverage item | Model state or invariant | Bad path that must fail | Good path that must pass |
|---|---|---|---|
| Block classification | `review_block_scope` | Treating `route_invalidating` as node-local repair. | `node_local` and `route_invalidating` are routed through different decisions. |
| Local repair availability | `same_node_repair_path_routable` | PM selects same-node repair but router has no legal next event. | Revised plan or fresh result can be rechecked. |
| Route mutation threshold | `current_node_cannot_contain_repair_reason_present` | Mutating route for local defect without escalation reason. | Route mutation includes why the current node cannot contain the repair. |
| Fresh evidence | `fresh_repair_evidence_written` and `stale_blocked_evidence_reused_as_pass` | Old blocked artifact is treated as accepted. | New plan/result/report is written and old artifact stays context only. |
| Reviewer recheck | `same_review_class_rechecked_repair` | PM continues after repair without reviewer pass. | Repaired artifact passes the same review class before continuation. |
| Route recheck | Existing route-draft and route-check flags | Mutated route keeps stale route approvals. | Mutation resets hard route gates and waits for route checks. |

