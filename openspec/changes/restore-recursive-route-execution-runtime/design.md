## Context

The current new FlowPilot runtime has a useful clean core: startup intake,
current-run ledger authority, sealed packets, dynamic leases, FlowGuard
work-order packets, review packets, validation packets, and closure packets.
The active live run showed the remaining gap. The PM produced a route plan for
a real UI project, but the runtime treated that PM planning result as the only
task and reached terminal closure after the PM/FlowGuard/review/validation/
closure packet chain.

Old FlowPilot's durable capability was different: PM route plans became route
nodes, an execution frontier selected the next node, every node ran through
bounded work and review, failures repaired or mutated the route, parent nodes
were replayed after children, and final closure rebuilt a route-wide ledger
from the current route.

## Goals / Non-Goals

**Goals:**

- Materialize PM route plans into structured route nodes and a current
  execution frontier.
- Reuse the existing symmetric packet lifecycle as a node execution primitive.
- Require node acceptance before frontier advancement.
- Require PM disposition after reviewed task results.
- Support repair, route mutation, stale evidence, and late-output quarantine.
- Require final closure to prove all effective route nodes, FlowGuard targets,
  reviews, validation rows, and route-wide ledger entries are complete.
- Extend fake-agent rehearsal so a green test proves multi-node traversal, not
  only the five-packet foundation chain.

**Non-Goals:**

- Do not revive old router state as authority.
- Do not reintroduce fixed six-agent topology as a runtime invariant.
- Do not build or redesign the Cockpit UI in this change.
- Do not push, publish, tag, deploy, or handle secrets.
- Do not claim live-host semantic quality from fake-agent rehearsals alone.

## Decisions

### Decision: Route nodes are current-run ledger objects

The active route keeps an ordered node list with `node_id`, parent/child links,
node kind, responsibility, modeled target, acceptance criteria, and status.
The execution frontier records the active route version, current node, completed
nodes, blocked node, pending route mutation, and finalization status.

Alternative considered: keep route steps as strings and infer node progress
from packet order. That repeats the observed miss because PM planning text can
look complete without becoming executable work.

### Decision: Packet chains execute one node at a time

The existing packet kinds stay intact. A node work packet is a `task` packet
bound to `route_node_id`. Valid node task results issue FlowGuard, review,
validation, and closure-like node evidence packets for that node. The node
closes only after PM disposition accepts the reviewed result.

Alternative considered: add separate bespoke commands for node acceptance.
That would break the symmetric packet lifecycle that just proved valuable.

### Decision: PM planning packets create route materialization packets

The first PM packet result can be accepted as a planning artifact, but it
cannot close the project. Its side effect is `route_materialized`: a route
draft becomes route nodes and an execution frontier. The next router action is
the first node work packet unless route materialization is blocked.

Alternative considered: require PM to output strict JSON in every live run
before any progress. The implementation will support structured route plans but
also provide a conservative fallback node plan for current live PM prose so
older real runs can continue without trusting the prose as closure evidence.

### Decision: Final closure consumes a route-wide ledger

Final closure is legal only after every effective node is accepted or explicitly
superseded, every active packet is accepted or quarantined after mutation, every
required FlowGuard target has a current passing report, validation is fresh,
and the final route-wide ledger has zero unresolved items.

Alternative considered: keep closure based on accepted packets only. That is
exactly the overclaim that closed the PM planning packet as if it were the whole
project.

### Decision: FlowGuard target selection is node-owned

Each node records its `modeled_target`. UI nodes can use `ui_interaction_flow`,
implementation nodes can use `development_process` or `code_structure_plan`,
test nodes can use `test_and_evidence_hierarchy`, and repair misses can use
`model_miss`. A passing report for the wrong target cannot satisfy the node.

### Decision: Fake rehearsal becomes route-shaped

The fake project rehearsal must open/start through the public CLI, complete a
multi-node route, observe expected repair and mutation branches, and prove that
missing node acceptance blocks final closure.

## Risks / Trade-offs

- Broad old-flow parity can sprawl -> implement the minimum route/node/frontier
  kernel first, then verify exact old-flow obligations with focused tests and
  FlowGuard models.
- PM prose may not be structured enough -> accept explicit structured route
  JSON when available and fall back to a small conservative route plan while
  recording that fallback as generated route materialization.
- Closure evidence can become expensive -> keep final ledger machine-readable
  and derived from current ledger state; make public status a projection only.
- Existing tests may assume single-chain terminal closure -> update them so
  the old single-chain behavior is still allowed only for `route_scope:
  project_foundation`, not for full project execution.
- Background regressions can produce progress-only logs -> use the repository's
  stable background artifact contract and inspect exit/proof files before broad
  claims.

## Migration Plan

1. Add the OpenSpec contract and focused FlowGuard model for recursive route
   execution.
2. Extend the runtime ledger schema with route nodes, frontier, PM disposition,
   route-wide ledger, and node closure records.
3. Update router next-action logic to issue node packets before project closure.
4. Update run shell materialization and public status projection.
5. Expand fake-agent rehearsal and focused tests.
6. Run OpenSpec, FlowGuard, unit, fake rehearsal, install, and background model
   checks.
7. Sync local installed FlowPilot and record version/git evidence.

Rollback strategy: keep old runtime files and completed prior changes as
diagnostic reference. If recursive checks fail, the new runtime remains scoped
and cannot be reported as old-flow equivalent.

## Open Questions

- Whether future live-host runs should require structured PM JSON route output
  or allow the fallback route materializer permanently.
- How much of the old parent/module topology should be promoted into the
  minimal black-box runtime versus delegated to the older router until a later
  cleanup pass.
