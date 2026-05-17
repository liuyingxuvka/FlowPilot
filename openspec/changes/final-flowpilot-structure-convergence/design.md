## Context

The repository is on local `main` and has already completed the main Python
structure simplification pass. Remaining hotspots are concentrated in a few
large surfaces:

- `skills/flowpilot/assets/flowpilot_router.py` is still a 35k-line facade with
  long event/action functions.
- `tests/test_flowpilot_router_runtime.py` still stores the 304 aggregate test
  implementations, while domain entrypoints currently select tests by name.
- `skills/flowpilot/assets/role_output_runtime.py` and the remaining
  `packet_runtime.py` CLI/audit bodies are still multi-responsibility runtime
  files.
- Several child FlowGuard models still combine state, transition, hazard,
  invariant, and audit concerns in one file.
- Existing OpenSpec changes are complete, but the final convergence work needs
  its own scope and validation matrix.

## Decisions

1. Keep compatibility facades until a later explicit compatibility-removal
   change.

   Rationale: runtime cards, scripts, tests, and installed skills reference the
   existing module names. Moving bodies behind facades reduces maintenance risk
   without changing caller contracts.

2. Split test implementations before making further broad router behavior
   changes.

   Rationale: router regressions are already domain-grouped, but debugging is
   still slow because the actual implementations live in one large class.
   Moving implementations first gives future router edits smaller validation
   surfaces.

3. Split high-risk router functions only behind existing entrypoints.

   Rationale: event names, persisted state, wait reconciliation, and packet
   authority are behavior-sensitive. New helpers must preserve the existing
   public functions and final state shape.

4. Keep child-model splits local to each model family.

   Rationale: child FlowGuard models are living design artifacts. Splitting
   them should make risks and hazards easier to see, not introduce a generic
   abstraction layer that hides model-specific language.

5. Use layered Meta/Capability `--full` as the release-grade parent check.

   Rationale: previous maintenance established this as the current supported
   parent evidence path. `--legacy-full` is too slow for routine work and is not
   part of this change unless explicitly requested.

6. Treat validation evidence as part of the structure.

   Rationale: future agents should not rediscover which slow tests need larger
   timeouts or which model checks own which boundary. A verification matrix is
   required output, not optional documentation.

## Risk Catalog

- Router event/action drift: helper extraction can change ordering, side
  effects, durable writes, or error paths.
- Test migration loss: moving implementations can silently drop or duplicate
  tests.
- Model semantics drift: splitting child models can weaken hazards or change
  accepted/rejected scenarios.
- CLI/install drift: runtime facade splits can change command output, parse
  behavior, or installed skill freshness.
- Evidence overclaim: background progress or old monolithic model artifacts can
  be mistaken for current completion evidence.

## Validation Strategy

- Run import and CLI smoke checks for each facade split.
- Keep AST coverage checks for router runtime domain tests: aggregate and
  domain suites must cover the same named tests exactly once.
- Run the focused domain tests for touched router boundaries. Slow domains such
  as `route_mutation` and `packets` must use generous background timeouts and
  exit artifacts.
- Run focused child model checks after each model split.
- Run `run_flowpilot_model_hierarchy_checks.py` after model evidence or parent
  proof inputs change.
- Run layered `run_meta_checks.py --full` and
  `run_capability_checks.py --full` through the background artifact contract
  before final completion.
- Run install sync/check/audit after any `skills/flowpilot` source change.

## Non-Goals

- No release, remote push, deployment, binary build, or package publication.
- No removal of compatibility facades.
- No broad formatter or unrelated style cleanup.
- No protocol or persisted JSON shape redesign.
