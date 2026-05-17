## Why

`router_route_mutation_core` is still the slowest router child suite. The last
background run completed successfully, but the single 22-test module took about
1901 seconds. That makes routine failure diagnosis poor: a timeout or failure
does not immediately identify whether the issue is draft activation,
model-miss triage, node acceptance repair, route-mutation preconditions,
topology mutation, sibling replacement, or parent backward replay.

The previous change already created fast parent route-mutation contract tests.
This change keeps those parent contracts intact and splits only the remaining
full runtime oracle into semantically owned child suites.

## What Changes

- Split `tests.router_runtime.route_mutation` into focused runtime oracle
  modules.
- Keep `tests.router_runtime.route_mutation` as a compatibility aggregate for
  explicit full-oracle runs.
- Replace the routine `router_route_mutation_core` tier command with focused
  child commands.
- Update FlowGuard TestMesh/StructureMesh evidence so each child suite has its
  own owner, command, result artifact, and stale-evidence boundary.
- Update model-test alignment and verification docs so route-mutation coverage
  does not overclaim one monolithic child command.

## Impact

- Production behavior: none.
- Test behavior: route-mutation runtime oracle evidence becomes smaller and
  parallelizable.
- Install sync: validation registry and local installed FlowPilot skill must be
  refreshed after the repo-owned skill/docs are updated.
