## Context

The repository already has a read-only coverage sweep runner at
`scripts/run_flowguard_coverage_sweep.py`, plus a model-test alignment runner
at `simulations/run_flowpilot_model_test_alignment_checks.py`. These are useful
but answer different questions:

- Coverage sweep: which FlowGuard check runners exist, whether their current
  result artifacts are parseable, and what findings/skips they report.
- Model-test alignment: whether selected model obligations are tied to ordinary
  test evidence and source-audited code contracts.

The full inventory must combine these views without claiming that every model
boundary is fully tested.

## Goals / Non-Goals

**Goals:**

- Enumerate all FlowGuard check entrypoints and classify their evidence status.
- Identify runners that have no ordinary test reference, no persisted result,
  skipped checks, stale/progress-only evidence, or only abstract model evidence.
- Preserve remaining uncertainty as explicit gap classes.
- Produce a report that can drive future focused test additions.

**Non-Goals:**

- No bulk test generation.
- No production runtime edits.
- No branch pruning or structure splitting.
- No release-level confidence claim.

## Decisions

- Reuse the existing coverage sweep runner as the base inventory input.
  Rationale: it already knows how to avoid mutating runner result files and how
  to read persisted results when a runner writes by default.
- Add a narrower full-model inventory artifact if needed to make the output
  easier to consume for model-test planning. Rationale: the sweep is runner
  focused, while this task needs model/test gap grouping.
- Treat `ok=true` as "the inventory ran", not "every model boundary has a
  test." Rationale: passing abstract model checks and source-audit checks are
  different evidence levels.

## Risks / Trade-offs

- Some runners are intentionally release-only or heavyweight. Mitigation:
  record them as release/heavyweight evidence instead of running everything
  blindly.
- Test references can be approximate when detected by text scan. Mitigation:
  mark those as weak coverage and keep source-audited evidence distinct.
- Existing dirty worktree contains other agents' or prior changes. Mitigation:
  keep edits scoped to inventory artifacts and do not revert unrelated files.
