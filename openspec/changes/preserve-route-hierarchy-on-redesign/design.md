## Context

FlowPilot already has a recursive route model: route nodes can be `root`,
`parent`, `module`, `leaf`, or `repair`; nodes carry `parent_node_id` and
`child_node_ids`; parent/module nodes are entered before children; and parent
backward replay closes composition after child completion. The live regression
was not absence of these fields or traversal mechanics. It was a route-redesign
path where PM returned a strict `route_plan` containing many top-level nodes
without hierarchy fields. Runtime accepted the plan because `node_kind` defaults
to `leaf`, and Reviewer/FlowGuard did not treat a complex all-leaf route as a
hard route-quality failure.

The repository rules prefer current-contract repairs and existing fields over
new ledgers or compatibility surfaces. Therefore this change uses the existing
route node shape and existing staged route-redesign gate.

## Goals / Non-Goals

**Goals:**

- Preserve parent/module hierarchy when PM redesigns an initial route, a whole
  route, a repair scope, or the active node at node-entry time.
- Make the "too broad leaf" path promote the current node to a parent/module
  and attach ordered children under that node.
- Block complex flat all-leaf route plans unless PM records a concrete, narrow
  reason that no parent/module composition boundary is needed.
- Keep Reviewer and FlowGuard responsible for semantic hierarchy quality while
  Runtime owns mechanical route-shape rejection.
- Cover the regression with focused model and unit tests before install sync.

**Non-Goals:**

- Do not add a new route-plan schema version.
- Do not add display-only route plans, compatibility aliases, or field
  migrations.
- Do not remove the staged route-redesign FlowGuard/PM/Reviewer gate.
- Do not change final closure semantics beyond preserving the parent/module
  structure that existing closure already consumes.

## Decisions

### Decision: Use existing route fields as the contract surface

`node_kind`, `parent_node_id`, and `child_node_ids` already exist in strict
route plans, materialized nodes, diagrams, legal next-action logic, and parent
backward replay. Runtime will add targeted validation around those fields
instead of introducing new "decomposition metadata".

Alternative considered: add a new per-node decomposition field. Rejected
because it would duplicate route topology and create maintenance debt.

### Decision: Runtime catches mechanical invalid hierarchy, roles catch quality

Runtime should reject impossible shapes: parent/module without children, leaf
with children, missing child references, child referencing a missing parent, and
active-node redesign that fails to preserve the active node as the subtree root.
Reviewer and FlowGuard should reject quality failures such as a broad complex
route flattened into many peers without justified composition boundaries.

Alternative considered: make Runtime reject every all-leaf route over a fixed
count. Rejected as too blunt; small serial jobs may be valid all-leaf routes.

### Decision: Node-entry redesign is subtree replacement

When PM decides at node entry that the active leaf is too broad, the redesign
result must express that current node as a parent/module or replace it with a
new parent/module scope that owns the proposed children. The child nodes belong
inside that subtree. They are not appended after the current node as unrelated
peers.

Alternative considered: keep existing whole-route replacement for all
redesigns. Rejected because it loses the user-visible route hierarchy and skips
the parent backward replay boundary for the decomposed node.

### Decision: Prompt/card hardening remains scoped to existing gates

PM route skeleton, PM node acceptance, Reviewer route/node-plan review, and
FlowGuard route-process cards will all say the same thing in their own role:
route plans are executable trees, recursive decomposition increases depth, and
complex flat plans are not acceptable by default.

Alternative considered: add a new "hierarchy auditor" role. Rejected because
Reviewer and FlowGuard already own this gate.

## Risks / Trade-offs

- Runtime validation could reject simple legitimate all-leaf routes ->
  mitigation: keep all-leaf quality rejection in Reviewer/FlowGuard prompts and
  limit Runtime hard rejection to inconsistent topology and active-node subtree
  redesigns.
- Prompt-only repair may not be enough -> mitigation: add focused runtime tests
  for mechanical shape and prompt-card tests for the role obligations.
- Existing route-plan fixtures may omit hierarchy fields -> mitigation: only
  require hierarchy fields when they are structurally necessary, and update
  focused fixtures that intentionally model complex parent/module routes.
- Later install evidence can stale tests -> mitigation: run source validation
  first, then sync the local installed skill, then run install audit/check
  serially.
