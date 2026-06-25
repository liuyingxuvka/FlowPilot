## Context

FlowPilot already has the pieces needed for this change:

- PM FlowGuard operator Work Order / Report loops;
- PM evidence quality packages;
- PM final route-wide gate ledgers;
- Reviewer terminal backward replay;
- PM supplemental repair contracts;
- PM terminal closure.

The gap is not missing workflow machinery. The gap is that terminal completion
does not require one current, PM-accepted FlowGuard project coverage report
after ordinary node and parent backward replay have settled. Node-level
FlowGuard evidence can be present but still leave the project-level question
unanswered: did FlowGuard cover every boundary that mattered for this run?

## Goals / Non-Goals

**Goals:**

- Reuse the existing PM, FlowGuard operator, Reviewer, and supplemental repair
  roles.
- Add a mandatory terminal coverage Work Order boundary after route/node
  backward replay and before final PM closure.
- Make the PM final ledger and terminal Reviewer replay block on missing,
  stale, progress-only, unaccepted, or blocking terminal FlowGuard coverage.
- Preserve exact ownership: FlowGuard operator diagnoses and reports, PM
  decides and repairs, Reviewer audits terminal evidence, workers repair target
  project gaps when PM creates repair nodes.
- Add focused model and test evidence, including fake-role/cartesian coverage.

**Non-Goals:**

- Do not create a new scheduler, reviewer role, or side ledger that bypasses
  PM final ledger authority.
- Do not let the FlowGuard operator mutate routes, repair target project code,
  approve Reviewer gates, or close the run.
- Do not change the frozen acceptance contract or public release process.

## Decisions

### Terminal FlowGuard coverage is a Work Order subtype

The PM will request `terminal_flowguard_coverage_review` through the existing
FlowGuard operator request/report loop. This keeps request identity, report
identity, freshness, role ownership, PM absorption, and suggestion disposition
inside the lifecycle already used by FlowPilot.

Alternative considered: add a standalone terminal coverage ledger. That was
rejected because it would be easy to attach but hard to enforce, and it would
duplicate PM final ledger authority.

### The report is a runtime output contract

Add a `flowguard_terminal_coverage_report` contract instead of overloading the
generic model report. The report still belongs to the existing FlowGuard
operator output root, but the terminal contract can require terminal-specific
fields: coverage matrix reference, freshness, PM acceptance state, blockers,
suggestions, waivers, model/test alignment gaps, and repair routing.

Alternative considered: reuse the generic `flowguard_operator.model_report`
shape only. That would preserve compatibility but would not make missing
terminal coverage details mechanically detectable.

### Final ledger owns pass/fail closure

The final ledger gets a `flowguard_terminal_coverage_closure` row. PM closure
and terminal backward replay read that row. The row is not a second approval
system; it is the ledger projection of the PM-accepted operator report.

### Reviewer checks governance, not the model itself

Reviewer terminal replay adds a `flowguard-coverage-governance` segment. The
Reviewer checks whether the report exists, is current, is PM-accepted, has no
unresolved blockers, and has all PM suggestions dispositioned. The Reviewer
does not re-run FlowGuard modeling or replace the operator.

### Repair uses the existing supplemental loop

Missing or failing terminal coverage becomes `flowguard_coverage_gap` in the
existing supplemental repair contract. PM selects the owner:

- FlowGuard operator for missing/stale/report/model coverage gaps;
- worker/test owner for actual target project or validation repairs;
- PM for route/ledger/suggestion-disposition gaps.

The existing same-terminal-gap repair cap remains authoritative.

### Fake-role/cartesian tests are required evidence

The regression set must include synthetic role-output/fake-response scenarios
covering report presence, freshness, PM acceptance, blocker disposition,
suggestion disposition, reviewer segment pass/fail, and supplemental repair
routing. Cartesian coverage is model-scoped: finite axes are declared in the
focused FlowGuard model, then projected into runtime tests.

## Risks / Trade-offs

- Over-strict closure on older/minimal runs -> terminal coverage is required
  for non-trivial FlowGuard-backed runs; minimal legacy fixture behavior must
  either produce explicit scoped-out evidence or remain visibly incomplete.
- Duplicate operator identities -> reuse the existing operator role naming and
  output roots rather than introducing a new role.
- Long regressions slow the implementation loop -> run heavyweight Meta and
  Capability checks through the repository's background log contract, and treat
  progress-only logs as incomplete until exit artifacts exist.
- Parallel agent edits may stale evidence -> inspect `git status` before
  integration and do not overwrite unrelated modified files.

## Migration Plan

1. Add OpenSpec specs and tasks for this change.
2. Add focused FlowGuard model evidence for terminal coverage ordering and
   cartesian fake-response hazards.
3. Update cards, contracts, quality packs, and runtime checks.
4. Add/update tests and result artifacts.
5. Run focused foreground checks, then background heavyweight checks.
6. Sync the installed FlowPilot skill from repo-owned source and audit
   freshness.
7. Update version/changelog/handoff and create local git evidence.

