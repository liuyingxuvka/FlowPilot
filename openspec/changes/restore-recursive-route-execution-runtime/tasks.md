## 1. OpenSpec And FlowGuard Modeling

- [x] 1.1 Validate the new OpenSpec change strictly before implementation.
- [x] 1.2 Add a focused FlowGuard model and runner for recursive route execution.
- [x] 1.3 Cover known-bad states: PM-plan terminal completion, missing node closure, wrong FlowGuard target, stale node evidence, dead lease, and route mutation without frontier rewrite.

## 2. Runtime Route And Frontier State

- [x] 2.1 Extend the current-run ledger with structured route nodes, execution frontier, node results, PM dispositions, route-wide ledger, and node closure state.
- [x] 2.2 Materialize PM planning results into executable route nodes and conservative fallback nodes when PM output is prose.
- [x] 2.3 Materialize route/frontier/node artifacts under the active run root and include public projection rows without sealed bodies.

## 3. Recursive Node Packet Loop

- [x] 3.1 Update router next-action selection so planning closure issues first-node work instead of terminal completion.
- [x] 3.2 Issue node-scoped task packets with route node id, responsibility, modeled target, and acceptance criteria.
- [x] 3.3 Require FlowGuard, review, validation, and PM disposition before node acceptance.
- [x] 3.4 Advance the frontier across effective nodes and attempt final route-wide closure only after all nodes are resolved.

## 4. Repair, Mutation, And Closure

- [x] 4.1 Add PM disposition actions for accept, repair, mutate_route, block, and stop.
- [x] 4.2 Add route mutation records that supersede affected node evidence, quarantine late old-route outputs, and rewrite the frontier.
- [x] 4.3 Build final route-wide gate ledger and closure blockers for missing nodes, wrong target, stale validation, unresolved resources, residual risks, and stale evidence.

## 5. Rehearsal And Tests

- [x] 5.1 Expand deterministic fake-project rehearsal to traverse a multi-node route through the public CLI.
- [x] 5.2 Add fake bad-case rows for missing node, wrong target, dead lease, stale evidence, route mutation, and retired side commands.
- [x] 5.3 Add focused unit tests for route materialization, node packet loop, PM disposition, route mutation, closure blockers, and public status projection.
- [x] 5.4 Update existing tests that previously expected terminal completion after a single PM packet chain.

## 6. Validation, Sync, And Completion Evidence

- [x] 6.1 Run OpenSpec strict validation, focused FlowGuard model checks, focused pytest, fake-project rehearsal, install checks, and relevant existing runtime checks.
- [x] 6.2 Run heavier Meta/Capability regressions in background artifacts and inspect exit/proof artifacts before broad confidence.
- [x] 6.3 Update version, changelog, FlowGuard adoption log, and any install inventory needed by the changed runtime.
- [x] 6.4 Sync the local installed FlowPilot skill and run install audit/check.
- [x] 6.5 Review git status, preserve unrelated peer changes, commit the completed local result, and record KB postflight.
