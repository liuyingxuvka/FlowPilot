## Context

The diagnostic currently binds most router owner modules to the broad `router_runtime_architecture` model family, but several owner files still lack source-level external-contract evidence. The user asked to continue with "real external contract tests" before splitting additional large modules.

## Goals / Non-Goals

**Goals:**

- Cover a safe batch of router owner modules by directly calling their owner-boundary symbols in ordinary tests.
- Bind each tested symbol into the FlowGuard source-contract plan with `CodeContract` and `TestEvidence` rows.
- Preserve residual gap honesty for modules that remain missing, oversized, stale, or deferred.

**Non-Goals:**

- No public release, GitHub push, tag, or release artifact publication.
- No broad router refactor or stateful module split in this pass.
- No weakening of FlowGuard invariants or diagnostic thresholds.

## Decisions

- Use a new focused unittest module instead of folding all assertions into broad runtime tests. This keeps the contract proof easy to map from test name to owner module.
- Test observable shapes: return dictionaries, schema names, path outputs, idempotency keys, state mutations, persisted JSON records, and raised errors. Internal implementation paths are not enough.
- Add source-contract rows only for symbols actually called by the new tests. Mention-only or import-only coverage remains incomplete.
- Keep structure-split findings visible; external contract coverage is a prerequisite, not a substitute for later StructureMesh splits.

## Risks / Trade-offs

- [Risk] Router owner helpers may need facade globals during tests. Mitigation: use the real router facade or narrow fake routers only where the function already accepts a router object.
- [Risk] Tests could accidentally assert implementation details. Mitigation: assert only stable external outputs, persisted records, or explicit error contracts.
- [Risk] Concurrent agents may touch adjacent runtime files. Mitigation: edit only the new test file, alignment script, OpenSpec files, and adoption notes unless validation exposes a real bug.
