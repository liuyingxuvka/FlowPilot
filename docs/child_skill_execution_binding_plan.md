# Child Skill Execution Binding Plan

Date: 2026-05-11

## Goal

FlowPilot must not only extract child-skill standards into route and node
contracts. When a current node is derived from a child skill, the node
acceptance plan and worker/reviewer packets must explicitly bind the relevant
child skill for that node slice, tell the worker to use the source skill, and
require result evidence proving the child skill was used. The PM packet is the
minimum floor; stricter child-skill requirements win unless an explicit approved
waiver is recorded.

## Optimization Sequence

| Step | Change | Minimal target files | Verification |
| --- | --- | --- | --- |
| 1 | Add a node-level `active_child_skill_bindings` contract that names the current-node child skill slice, source skill path, required references, applicable standards, and stricter-than-PM precedence rule. | `templates/flowpilot/node_acceptance_plan.template.json`, `cards/phases/pm_node_acceptance_plan.md` | Planning-quality tests assert the field and wording exist. |
| 2 | Preserve and propagate those active bindings into current-node work packets, including source paths/references the worker is allowed to open. | `templates/flowpilot/packets/packet_body.template.md`, `skills/flowpilot/assets/flowpilot_router.py` | Router/template tests prove accepted plan bindings are not dropped. |
| 3 | Require workers to use the bound child skill only for the current node slice and return `Child Skill Use Evidence`. | `cards/roles/worker_a.md`, `cards/roles/worker_b.md`, `templates/flowpilot/packets/result_body.template.md`, `contracts/contract_index.json` | Output-contract tests require evidence when active bindings exist. |
| 4 | Require reviewers to block missing child-skill use, missing source opening, omitted evidence, or PM-standard downgrades below the child skill. | `cards/reviewer/node_acceptance_plan_review.md`, `cards/reviewer/worker_result_review.md` | Planning-quality and reviewer-contract tests assert blocker language. |
| 5 | Run local install sync and local git commit only after FlowGuard and focused tests pass. | install scripts, local git | Install audit/check passes; no remote push. |

## Risk List and FlowGuard Coverage

| Risk | Failure mode to catch before code edits | FlowGuard coverage to add |
| --- | --- | --- |
| 1 | PM extracts standards but never writes an execution-time child-skill binding for the current node. | Invariant: projected child-skill standards cannot reach worker dispatch unless active node bindings are written. |
| 2 | Worker packet mentions inherited standards but does not tell the worker to open/use the actual child skill. | Invariant: active bindings must appear in the worker packet with source path and direct use instruction. |
| 3 | Packet fails to allow the bound `SKILL.md` or referenced files, so the worker cannot actually inspect the child skill. | Invariant: every active binding requires source paths in packet read allowances. |
| 4 | Worker uses the whole child skill blindly instead of the node-relevant slice. | Invariant: active binding must include node-slice scope and selected standards. |
| 5 | PM packet has weaker wording than the child skill and the worker follows the weaker floor. | Invariant: stricter child-skill requirement must be applied or an approved waiver must exist before completion. |
| 6 | Worker returns output without proving direct child-skill use. | Invariant: worker result review cannot proceed without `Child Skill Use Evidence`. |
| 7 | Reviewer passes output without checking child-skill use evidence and stricter-standard precedence. | Invariant: child-skill completion cannot be verified until reviewer checked usage evidence and downgrade risk. |
| 8 | Router drops new binding fields from file-backed PM payloads or accepted node plans. | Hazard case: node plan with active bindings must preserve the binding field and packet projection. |
| 9 | Fix becomes overbroad and forces every selected skill into every node. | Invariant: bindings are scoped to current-node active child-skill slices, not route-wide availability. |

## FlowGuard Pass Criteria Before Implementation

1. The upgraded capability model rejects each risk above as a known-bad hazard.
2. The upgraded model accepts the intended sequence: PM writes active binding,
   packet carries binding and source paths, worker uses the child skill for the
   node slice, worker returns use evidence, reviewer verifies evidence and
   stricter-standard precedence, then child-skill completion can pass.
3. The final implementation reruns the capability checks and, because this
   touches project-control flow and packet routing, the meta checks as well.
