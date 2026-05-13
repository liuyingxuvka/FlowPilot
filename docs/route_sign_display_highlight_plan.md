# Route Sign Display Highlight Plan

## Scope

This change repairs the user-facing FlowPilot Route Sign projection used by
chat and Cockpit UI. It does not change route execution, node completion,
packet routing, review authority, or remote publishing.

Current observed issue in `run-20260513-034857`:

- `execution_frontier.json` says the active leaf is
  `leaf-flowguard-runtime-source-model`.
- The shallow Mermaid graph displays only module-level nodes.
- The visible parent module `module-runtime-authority` is not highlighted.
- The canonical Mermaid comment still says `temporary placeholder route sign`.
- The startup placeholder shows a repair loop even though every future node can
  iterate internally.

## Optimization Sequence

| Step | Optimization point | Concrete change | Acceptance signal |
| --- | --- | --- | --- |
| 1 | Model-first risk boundary | Upgrade `simulations/user_flow_diagram_model.py` so known-bad display plans fail before production code is edited. | Hazards for missing visible active highlight, stale placeholder wording, default placeholder repair loop, and summary-only active visibility are detected. |
| 2 | Clean visible graph labels | Keep Mermaid node labels surface-neutral: node/module title only. Do not write `Now`, `Done`, `Next`, or hidden leaf names into graph boxes. | Route-node Mermaid labels contain titles only while classes carry state. |
| 3 | Hidden active leaf projection | When the active node is hidden by `display_depth`, highlight the nearest visible active-path ancestor instead of leaving every visible box pending. | Current run shape highlights `module-runtime-authority` while `leaf-flowguard-runtime-source-model` stays in the status summary. |
| 4 | Aggregated visible state classes | Compute visible node classes from descendants: active descendant -> `active`; all visible/hidden descendants complete -> `done`; blocker descendant -> `blocked`; otherwise `pending`. | Completed earlier modules can render as `done`; the active module renders as `active`; future modules render as `pending`. |
| 5 | Canonical-vs-placeholder wording | Canonical route Mermaid comments must not call themselves temporary placeholders. Placeholder wording is only allowed when no canonical route source exists. | Canonical route comments say realtime/canonical route sign; startup placeholder comments say temporary placeholder. |
| 6 | Linear startup placeholder | Replace the default startup placeholder repair loop with a straight progress line. | Startup placeholder has no `Repair Return`, no default repair node, and no return edge. |
| 7 | Preserve real repair topology | Keep visible `returns for repair` edges for real review failure, validation failure, route mutation, and repair-node topology. | Existing repair and supersede tests still pass; repair edges appear only for concrete repair state. |
| 8 | Local sync only | Sync repository scripts/assets to the local installed FlowPilot skill and verify local install freshness. Do not push to GitHub. | `scripts/install_flowpilot.py --sync-repo-owned` and install checks pass locally. |

## Bug/Risk Checklist

| Risk id | Possible bug from this change | FlowGuard/model expectation | Runtime/test expectation |
| --- | --- | --- | --- |
| R1 | Active leaf is hidden by shallow display and no visible parent/module is highlighted. | Model rejects `active_node_resolved` plus shallow projection where no visible active highlight exists. | Unit test with active hidden leaf expects `class <parent> active` and no all-pending graph. |
| R2 | The implementation treats `Current path` summary text as enough even when the graph itself has no active class. | Model rejects summary-only active visibility after reviewer pass. | Reviewer check requires graph-highlight metadata, not only active path membership. |
| R3 | Mermaid labels become cluttered with `Now`, `Done`, `Next`, or hidden leaf text, conflicting with Cockpit expanded detail. | Model rejects state/detail text embedded in shared graph labels. | Unit tests assert route-node labels do not contain status prefixes or hidden leaf id/title. |
| R4 | Canonical route graph still says `temporary placeholder`, confusing real route state with startup placeholder state. | Model rejects canonical graph with placeholder wording. | Unit test asserts canonical route Mermaid does not contain `temporary placeholder`. |
| R5 | Startup placeholder still displays a default repair loop, implying only one stage has loop semantics. | Model rejects placeholder graph with a repair loop before canonical route exists. | Startup placeholder test asserts no `Repair Return` and no return edge. |
| R6 | Real repair, validation failure, route mutation, or supersede edges are accidentally removed while cleaning placeholder loops. | Model keeps return-edge-required states failing unless a repair edge is present. | Existing repair/supersede tests still pass and assert repair edge behavior. |
| R7 | Descendant aggregation marks a module done while one hidden child is active, blocked, or pending. | Model includes active/blocked/complete precedence expectations for visible projection classes. | New tests cover active descendant wins over done, blocked descendant wins over pending, and all complete -> done. |
| R8 | Chat and Cockpit drift by using different graph semantics. | Model treats graph labels/classes as shared surface-neutral projection, with detail outside the graph. | Display packet keeps active path/current node metadata for Cockpit/detail panes while Mermaid labels stay neutral. |
| R9 | Local repository and installed skill diverge after the fix. | Adoption log records local sync check as a required postcondition. | Hash/install checks verify repo scripts and installed skill assets match after sync. |

## FlowGuard Preflight Plan

Before production code edits:

1. Update `simulations/user_flow_diagram_model.py` with the risks above.
2. Run `python simulations/run_user_flow_diagram_checks.py`.
3. Confirm the safe graph passes.
4. Confirm the hazard set detects R1-R8 model-level risks.

After production code edits:

1. Re-run `python simulations/run_user_flow_diagram_checks.py`.
2. Run focused unit tests for route sign generation.
3. Run syntax checks for changed scripts.
4. Run broader FlowPilot checks that are practical in the dirty multi-agent
   workspace.
5. Sync local installed FlowPilot assets and verify local install freshness.

## Non-Goals

- No remote GitHub push.
- No change to route execution semantics.
- No change to packet/router authority.
- No graph label expansion with active leaf details.
- No removal of real repair/mutation/supersede topology.
