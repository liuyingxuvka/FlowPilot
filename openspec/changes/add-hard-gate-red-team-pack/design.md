## Context

FlowPilot accepts AI-produced work through Router events, role-output envelopes, packet/result envelopes, Controller receipts, background proof artifacts, and terminal closure decisions. Existing synthetic replay coverage proves many normal and exceptional paths, but the remaining confidence gap is whether each AI-facing entrypoint is a hard gate: bad inputs must be rejected or converted into a blocker without advancing protected state.

The existing model map points to the current owners:

- role-output event authority: `role_output_runtime_schema_authority.py`;
- artifact and packet envelope validation: `flowpilot_router_artifact_validation.py` and packet runtime helpers;
- external event intake and dispatch: `flowpilot_router_controller_runtime.py` and event dispatcher helpers;
- terminal closure: router runtime closure/terminal ledgers;
- evidence freshness: synthetic coverage matrix and model-test alignment diagnostics.

## Goals / Non-Goals

**Goals:**

- Add a hard-gate red-team matrix that names entrypoints, attack package classes, expected rejection/blocker outcomes, state invariants, and test evidence.
- Add runtime tests that submit bad AI-style packages through real public/runtime helpers where practical.
- Prove that rejected packages do not mutate protected state such as pending actions, active blockers, ledgers, terminal status, or current run authority.
- Preserve a clear recovery route: blocker, PM repair, human confirmation, or no-op rejection.
- Refresh model-test and install evidence after implementation.

**Non-Goals:**

- Do not build another normal happy-path fake AI driver.
- Do not change release/publication state, push to GitHub, tag, or deploy.
- Do not weaken hard invariants to make bad packages pass.
- Do not claim mathematical no-bug certainty; the claim remains scoped to the enumerated hard-gate cells.

## Decisions

1. Use a new matrix instead of overloading the existing synthetic coverage matrix.
   - Rationale: hard-gate tests are rejection/non-mutation boundary checks, while synthetic replay rows are broader workflow stories. Keeping them separate makes missing hard-gate cells visible.
   - Alternative considered: add more columns to the synthetic matrix. Rejected because it would mix story coverage with entrypoint boundary conformance.

2. Treat each cell as `EntryPoint x BadPackageClass x StateInvariant`.
   - Rationale: a rejected error is insufficient if protected state changed first. The invariant is part of the pass condition.
   - Alternative considered: only checking exception messages. Rejected because prior misses involved stale state and progress overclaims.

3. Use runtime tests first, model rows second.
   - Rationale: the user's concern is real bugs in running flows. Matrix rows must point to executable test evidence, not just design intent.
   - Alternative considered: modeling only. Rejected because prose/model confidence cannot prove real Router behavior.

4. Count stale or progress-only background evidence as rejected input.
   - Rationale: background regressions frequently produce partial logs. The hard gate must distinguish liveness from completion.
   - Alternative considered: leave this only in process docs. Rejected because the same mistake can appear as an AI-submitted proof package.

## Risks / Trade-offs

- [Risk] Red-team tests become too broad and slow. -> Mitigation: focus on finite entrypoint cells and use the fast tier plus targeted child suites for final validation.
- [Risk] Tests depend on private helper details. -> Mitigation: prefer public runtime/event helpers; use private helpers only to construct otherwise hard-to-reach setup state and keep assertions on public state artifacts.
- [Risk] Another AI changes overlapping runtime files. -> Mitigation: inspect git status before edits, keep touched files scoped, and re-run current validation after final writes.
- [Risk] A bad package is rejected but still writes audit-only records. -> Mitigation: the matrix must name protected state; audit-only records are allowed only when explicitly part of the expected outcome.
