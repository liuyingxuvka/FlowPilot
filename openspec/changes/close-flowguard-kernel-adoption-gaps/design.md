## Context

The repository already has real FlowGuard available and the installed
FlowPilot skill is currently fresh, but the full model-test-code diagnostic
still reports runtime-owner surfaces that are tested without a source-level
external contract binding. The active `finish-flowpilot-maintenance-convergence-v2`
OpenSpec change is being advanced by a peer agent, so this work must stay in a
separate adoption-closure lane and treat peer changes as shared workspace state.

## Goals / Non-Goals

**Goals:**

- Bind the current full diagnostic runtime-owner gaps to explicit
  model-test-alignment `CodeContract` and ordinary test evidence rows.
- Preserve legacy-data compatibility and old-logic dispositions through existing
  compatibility and diagnostic checks before claiming cleanup.
- Re-run focused tests, FlowGuard model-test alignment, OpenSpec validation,
  background FlowGuard regressions, and install freshness checks after edits.
- Keep final local-git evidence honest by separating this change's files from
  pre-existing or peer-owned dirty files.

**Non-Goals:**

- Do not complete, mark, or rewrite peer-owned OpenSpec tasks.
- Do not remove legacy compatibility paths unless the existing specs and tests
  prove they are retired.
- Do not publish remotely, tag a release, or perform destructive cleanup.

## Decisions

- Use a dedicated OpenSpec change for this adoption closure.
  - Rationale: the user asked this work to use OpenSpec, while the existing v2
    maintenance change is active and peer-owned.
  - Alternative considered: update the v2 change directly. Rejected because it
    would blur ownership and risk overwriting peer progress.

- Treat FlowGuard model-test alignment as the primary technical repair route.
  - Rationale: the observed gap is not that FlowGuard is missing, but that two
    externally relevant runtime surfaces are only proven by internal tests.
  - Alternative considered: rewrite runtime logic. Rejected unless diagnostics
    or focused tests expose a behavioral defect.

- Prefer evidence declaration and focused test repair before broad cleanup.
  - Rationale: old-data and old-logic cleanup should be driven by executable
    evidence, not by deleting historical compatibility code by inspection.
  - Alternative considered: broad legacy cleanup first. Rejected because peer
    changes and compatibility paths are active risk surfaces.

## Risks / Trade-offs

- Peer-agent writes may stale validation evidence -> record the dirty baseline
  and rerun required checks after this change's final edits.
- Full diagnostic can pass while broad regressions are still pending -> inspect
  background log artifacts and exit files before claiming completion.
- Legacy references may be compatibility evidence rather than dead code ->
  classify through existing specs and checks before removing or isolating them.
- Local install sync can overwrite installed skill state -> use repository-owned
  install scripts and freshness audits rather than manual copying.
