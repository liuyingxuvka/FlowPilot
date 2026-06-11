## Why

The current executable-node flow runs a mandatory FlowGuard gate before every worker node, which makes ordinary route traversal too heavy and blurs the Reviewer's role as the decomposition-quality judge. We need a cleaner contract: normal node execution follows the accepted route, while every PM route/node-structure change receives mandatory FlowGuard simulation, PM absorption, and Reviewer review before it can commit.

## What Changes

- **BREAKING**: Remove `node_prework_flowguard` as a mandatory gate for ordinary node execution after an accepted node acceptance plan.
- **BREAKING**: Treat PM route/node-structure changes as the only node-entry structural FlowGuard trigger. This includes splitting a node, replacing a leaf with child nodes, changing node order, deleting/replacing route nodes, and any route redesign from PM repair or node disposition.
- Add a PM FlowGuard-acceptance packet after mandatory FlowGuard reports for structural PM decisions. PM must absorb the FlowGuard result before Reviewer can review the decision.
- Keep Reviewer as the independent quality/decomposition judge. Reviewer blocks under-decomposed or over-decomposed route plans and node acceptance plans, but Reviewer does not replace FlowGuard's process simulation.
- Keep FlowGuard Operator as decision support, not route authority. FlowGuard may pass or block and may suggest repairs, but it never mutates the route and never releases workers directly.
- Keep one current-contract path only. Do not preserve old `node_prework_flowguard` compatibility, optional FlowGuard branches, legacy aliases, or historical artifact fallback.

## Capabilities

### New Capabilities
- `pm-flowguard-acceptance-gate`: PM must explicitly absorb a mandatory FlowGuard report for a structural PM decision before Reviewer review or route mutation commit.

### Modified Capabilities
- `flowpilot-packet-review-flow`: Reviewer release now requires PM absorption for structural FlowGuard reports, while ordinary accepted node plans no longer require a pre-worker FlowGuard packet.
- `route-repair-replacement-policy`: Structural route mutations must remain staged until FlowGuard passes, PM absorbs the result, Reviewer passes, and system validation closes.
- `flowguard-test-obligation-ownership`: PM still owns test-obligation disposition, but ordinary node entry derives pre-worker obligations from the node acceptance plan without requiring a separate pre-work FlowGuard report.

## Impact

- Runtime packet/result contracts for node acceptance plans, FlowGuard checks, PM decisions, PM FlowGuard acceptance, and Reviewer release.
- Router next-action logic for node acceptance, worker dispatch, PM route redesign, PM disposition redesign, and staged route mutation application.
- Prompt cards for PM, FlowGuard Operator, Reviewer, and node acceptance/review phases.
- Focused runtime tests, fake-AI packet shape tests, route-mutation tests, FlowGuard model checks, model-test-alignment declarations, install sync, and topology artifacts.
