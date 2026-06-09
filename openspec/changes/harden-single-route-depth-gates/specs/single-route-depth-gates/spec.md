## ADDED Requirements

### Requirement: PM route planning uses one canonical executable route tree

FlowPilot SHALL require PM route planning to author one canonical executable
route tree. The PM-authored route SHALL use current route-node fields for
parent/child structure, executable leaves, acceptance criteria, outputs, and
validation checks. PM route planning MUST NOT require a separate PM-authored
display plan as route authority.

#### Scenario: Complex work is represented as parent and leaf nodes

- **WHEN** the accepted user outcome requires multiple ordered work stages
- **THEN** the PM route includes parent/module nodes for composition scopes and
  leaf nodes for worker-executable scopes
- **AND** leaf acceptance criteria, required outputs, or validation checks show
  a single bounded worker outcome.

#### Scenario: Display is not a second PM route

- **WHEN** FlowPilot needs a user-visible or UI-visible route display
- **THEN** the display is generated from the canonical route and frontier
- **AND** PM is not required to maintain a second display route artifact.

### Requirement: Runtime blocks worker dispatch for non-leaf route scopes

FlowPilot SHALL reject worker task-packet creation for any active route node
whose existing route shape is a parent/module scope or has effective children.
This gate SHALL use existing route-node fields and SHALL NOT require a new
route-node schema family.

#### Scenario: Parent node cannot receive a worker task packet

- **WHEN** the active route node has `node_kind` equal to `parent` or `module`
- **THEN** FlowPilot refuses to create a worker task packet for that node
- **AND** the route remains at a planning, child-subtree, or parent-replay
  boundary instead.

#### Scenario: Child-bearing node cannot receive a worker task packet

- **WHEN** the active route node has one or more `child_node_ids`
- **THEN** FlowPilot refuses to create a worker task packet for that node
- **AND** FlowPilot does not treat an accepted node acceptance plan alone as
  permission to dispatch that parent scope.

### Requirement: Route process review simulates depth and coverage

FlowPilot SHALL require the FlowGuard operator route-process check to inspect
whether the canonical route can reach completion through effective ordered
parent/module/leaf traversal, worker-ready leaves, child-skill projection,
parent backward replay, and final evidence closure. The hard pass/fail outcome
SHALL remain the existing `process_viability_verdict`.

#### Scenario: Broad leaf blocks route viability

- **WHEN** a route leaf hides multiple ordered work packages or requires the
  worker to decide decomposition
- **THEN** the FlowGuard operator returns a repair-required or blocked
  process viability verdict
- **AND** PM must split, merge, or explicitly scope the route before activation.

#### Scenario: Route process pass uses existing hard verdict

- **WHEN** the route process model passes
- **THEN** the FlowGuard operator returns `process_viability_verdict: "pass"`
- **AND** no additional persistent process-trace ledger is required for the
  route to activate.

### Requirement: Reviewer blocks under-decomposed executable leaves

FlowPilot SHALL require Reviewer route and node-plan gates to block a current
gate when an executable leaf is too broad, parent-shaped, or dependent on
worker replanning. Reviewer findings MAY use PM-decision recommendations for
nonblocking quality improvements, but hard under-decomposition remains a gate
blocker.

#### Scenario: Worker replanning leaf is rejected

- **WHEN** a leaf node cannot be executed from the packet and node context
  without worker-side route decomposition
- **THEN** Reviewer blocks the route or node plan
- **AND** the recommended resolution returns to PM route split, node-plan
  repair, or route mutation rather than worker execution.

### Requirement: Field additions are last-resort and local

FlowPilot SHALL prefer existing route and node-context fields for route-depth
proof. A new persistent field MAY be added only when focused tests show that
existing fields, prompt checks, FlowGuard operator review, and Reviewer gates
cannot prevent broad-leaf or parent-dispatch failure.

#### Scenario: Existing fields are sufficient

- **WHEN** tests prove broad leaves and parent dispatch are rejected using
  existing route fields and node-context package content
- **THEN** FlowPilot does not add new route-node fields for explanatory
  rationale or process traces.

#### Scenario: Minimal nested fallback is needed

- **WHEN** a focused bad-case rehearsal remains incorrectly green without a
  leaf-readiness field
- **THEN** FlowPilot may add only a minimal
  `node_context_package.leaf_readiness_gate`
- **AND** the field remains local to node-entry acceptance planning rather than
  becoming a route-node top-level field.
