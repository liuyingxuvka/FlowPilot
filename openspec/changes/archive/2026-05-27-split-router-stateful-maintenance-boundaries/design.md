## Context

`flowpilot_router.py` remains the compatibility facade for CLI commands, tests,
install checks, and local skill installation. The first modularization pass
already extracted constants, IO/path helpers, card-settlement identity helpers,
Controller boundary constants, and protocol tables. It deliberately kept
write-bearing Controller reconciliation, ACK wait finalizers, startup/daemon
runtime progression, packet dispatch, and terminal closure inside the router
where the behavior-preserving seam was still unclear.

This pass continues from that baseline. The risk is not that helper extraction
is technically difficult; the risk is moving a state write, scheduler
projection, or authority decision into a module boundary without preserving the
same order and completion evidence. The design therefore favors small pure
helper modules, facade compatibility, and focused tests over a broad rewrite.

## Goals / Non-Goals

**Goals:**

- Reduce the remaining router/test monolith enough that future stateful fixes
  can target smaller files.
- Preserve current CLI behavior, runtime artifact schemas, packet schemas, role
  authority, ACK semantics, and terminal completion semantics.
- Split the large runtime test suite into boundary entrypoints that can be run
  independently while still reusing the existing test fixture.
- Extract only pure, table-driven, or low-side-effect helper boundaries in this
  pass unless existing tests and FlowGuard models directly cover the stateful
  move.
- Synchronize the installed local skill only after repository validation passes.

**Non-Goals:**

- Do not redesign Controller scheduler settlement, packet orchestration,
  startup lifecycle, daemon ownership, or terminal closure behavior.
- Do not rename or remove `flowpilot_router.py` as the public facade.
- Do not replace existing FlowGuard models with prose-only reasoning.
- Do not perform release, publish, remote push, dependency, or stack changes.

## Decisions

- Keep `flowpilot_router.py` as the write-bearing owner for high-coupling
  runtime flows.
  - Alternative rejected: move full finalizers now. Several finalizers update
    multiple runtime artifacts and derived views in one order-sensitive block;
    moving them would make this pass a behavior change unless the model and
    tests are first strengthened around that exact transaction.

- Add focused runtime suite entrypoints that select existing test methods.
  - Alternative rejected: copy test bodies into new files. Copying would create
    drift and make future behavior changes harder to audit.

- Extract pure helpers by boundary, not by arbitrary utility categories.
  - Controller, return-settlement, startup/daemon, dispatch gate, and terminal
    helper modules mirror the runtime responsibility boundaries that future
    fixes are likely to touch.

- Treat FlowGuard checks as evidence gates, not as ceremonial output.
  - Focused model checks run for touched boundaries. Meta and Capability checks
    run through the repository background artifact contract and are reported
    only after completion artifacts are inspected.

- Update install self-checks when new repo-owned skill files are introduced.
  - The installed skill audit should fail if a new helper module is forgotten
    during sync.

## Risks / Trade-offs

- [Risk] A helper move changes import-time availability from the router facade.
  -> Mitigation: preserve facade imports and run compile/import/check-install
  checks before claiming completion.

- [Risk] A test split masks failures by selecting the wrong methods.
  -> Mitigation: new focused suites use explicit method lists and the original
  runtime suite remains available as a facade integration suite.

- [Risk] ACK/return helpers blur ACK wait settlement with output completion.
  -> Mitigation: keep write-bearing settlement in the router unless the helper
  is pure and covered by ACK-only versus output-bearing tests.

- [Risk] Startup/daemon or terminal extraction crosses a lifecycle ownership
  boundary.
  -> Mitigation: extract only constants, predicates, payload builders, and
  status classifiers in this pass; stop if a helper needs to own lifecycle
  progression.

- [Risk] Broad model checks take longer than the code change.
  -> Mitigation: launch them with the established background artifact contract
  and inspect exit/meta/proof evidence before finalizing.

## Migration Plan

1. Create local backup snapshots under `tmp/` for comparison only.
2. Create focused runtime test entrypoints first so later checks can target the
   affected boundary.
3. Extract helper modules in small slices, preserving facade compatibility.
4. Run focused unit/model checks after each meaningful slice when practical.
5. Run install checks, smoke checks, OpenSpec validation, and broad FlowGuard
   regressions.
6. Sync the installed local FlowPilot skill from the repository and verify the
   installed copy matches.
7. Commit the completed local maintenance pass.

## Open Questions

- None that block implementation. If a seam requires changing runtime behavior
  rather than moving pure helper logic, leave it in the router and document the
  residual boundary for a future behavior-specific OpenSpec change.
