## ADDED Requirements

### Requirement: Reviewer-Gated Route Decomposition Quality

FlowPilot SHALL prevent a PM planning result from materializing into executable
route nodes until Reviewer has semantically accepted that the proposed route is
decomposed into small, single-purpose, non-overlapping, worker-ready leaves.

#### Scenario: Reviewer blocks broad planning leaves before materialization

- **GIVEN** a PM planning result has passed the mechanical current-contract
  route-plan shape
- **AND** FlowGuard Operator has produced matching post-result route-process
  evidence
- **WHEN** Reviewer determines that one or more proposed leaves are broad
  stages, overlap siblings, contain multiple ordered deliverables, or would
  require a Worker to invent subtasks or child ordering
- **THEN** FlowPilot SHALL keep the planning subject blocked
- **AND** SHALL NOT materialize route nodes from that planning result
- **AND** SHALL open the existing PM repair/recheck path with Reviewer's split
  recommendation available through the blocker evidence.

#### Scenario: PM repairs route depth through existing current-scope loop

- **GIVEN** Reviewer blocked planning because route decomposition was too coarse
- **WHEN** PM chooses current-scope repair and submits a deeper route plan
- **AND** the repaired plan passes FlowGuard Operator and Reviewer checks
- **THEN** FlowPilot SHALL materialize only the repaired accepted route plan
- **AND** SHALL continue with the normal node acceptance plan flow.

#### Scenario: Field surface stays conservative

- **GIVEN** PM writes a route plan under the strict route-plan contract
- **WHEN** FlowPilot validates the plan mechanically
- **THEN** FlowPilot SHALL NOT require broad new per-node explanation fields for
  decomposition quality
- **AND** SHALL leave semantic granularity to FlowGuard Operator evidence and
  Reviewer challenge.

### Requirement: FlowGuard Operator Worker-Decision Leakage Check

FlowGuard Operator SHALL check route-process viability by identifying whether
the route can reach closure without letting a Worker decide hidden route
decomposition.

#### Scenario: Worker has to invent missing child route

- **GIVEN** a proposed route leaf contains multiple ordered phases or deliverable
  families
- **WHEN** the route would only be executable if a Worker chooses subtasks,
  order, dependencies, or acceptance boundaries
- **THEN** FlowGuard Operator SHALL report that the process leaks planning
  decisions into Worker execution
- **AND** SHALL recommend route deepening before Worker dispatch.

### Requirement: Node Entry Broad-Leaf Fallback

FlowPilot SHALL treat broad-leaf discovery at node acceptance planning as a
fallback repair gate before Worker dispatch, not as ordinary Worker work.

#### Scenario: Apparent leaf is still too broad at node entry

- **GIVEN** a materialized leaf reaches node acceptance planning
- **WHEN** PM, FlowGuard Operator, or Reviewer finds that the leaf still hides
  child ordering or multiple separate work packages
- **THEN** Reviewer SHALL block the node acceptance plan or route gate
- **AND** PM SHALL deepen or mutate the route before any Worker packet is
  dispatched for that leaf.
