## ADDED Requirements

### Requirement: PM node acceptance produces a context package

FlowPilot SHALL require every accepted node acceptance plan to produce a
current PM-authored node context package for the same route node and repair
generation.

#### Scenario: Accepted node plan includes context

- **WHEN** PM submits a node acceptance plan result
- **THEN** runtime MUST record a `node_context_package` with node identity,
  repair generation, purpose, acceptance criteria, relevant references,
  evidence targets, inspection targets, known risks, FlowGuard/model targets,
  and reviewer starting points.
- **AND** runtime MUST attach the context package id to the route node.

#### Scenario: Thin node plan is rejected as missing context

- **WHEN** PM submits a node acceptance plan result without the required context
  package fields
- **THEN** runtime MUST NOT accept the node acceptance plan
- **AND** runtime MUST NOT issue pre-work FlowGuard, worker, post-result
  FlowGuard, or Reviewer packets for that node.

### Requirement: Downstream packets carry the current context package

FlowPilot SHALL attach the current node context package to every formal packet
in the node execution chain.

#### Scenario: Pre-work FlowGuard starts from PM context

- **WHEN** runtime issues the node pre-work FlowGuard packet
- **THEN** the packet body MUST include the current node context package
- **AND** the packet MUST state that the package is the minimum starting point,
  not a limit on FlowGuard route selection or risk modeling.

#### Scenario: Worker receives the same context baseline

- **WHEN** runtime issues the worker node packet after pre-work FlowGuard passes
- **THEN** the packet body MUST include the current node context package
- **AND** the packet MUST preserve the node acceptance criteria and evidence
  targets from that package.

#### Scenario: Post-result FlowGuard and Reviewer receive the same baseline

- **WHEN** runtime issues post-result FlowGuard or Reviewer packets for a worker
  result
- **THEN** the packet body MUST include the current node context package, the
  subject packet id, and the target result id
- **AND** Reviewer instructions MUST state that the package is a starting
  context, not the review boundary.

### Requirement: Context freshness follows node repair generation

FlowPilot SHALL invalidate node context packages when the route node repair
generation changes.

#### Scenario: Repair makes old context stale

- **WHEN** PM records same-node repair or route mutation replacement for a node
- **THEN** runtime MUST clear or mark the previous node context package stale
- **AND** runtime MUST require a fresh PM node acceptance plan and context
  package before issuing any new pre-work FlowGuard or worker packet.

### Requirement: Reviewer and FlowGuard remain independently active

FlowPilot SHALL preserve independent challenge even when PM supplies the context
package.

#### Scenario: Reviewer checks beyond package pointers

- **WHEN** Reviewer receives a review packet with a node context package
- **THEN** Reviewer MUST inspect the subject result, node contract, FlowGuard
  evidence, relevant artifacts, and task-specific direct evidence inside the
  authorized scope
- **AND** Reviewer MUST NOT pass solely because the PM context package exists.
