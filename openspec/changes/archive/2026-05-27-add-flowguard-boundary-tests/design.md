## Context

The upgraded FlowGuard Model-Test Alignment runner is green at the broad family
level, but its full diagnostic still reports two runtime-contract coverage
gaps:

- `controller_process_aside.py` has ordinary test mentions but no
  source-audited external contract binding.
- `flowpilot_material_artifact_map.py` has runtime tests in the material flow,
  but no source-audited contract row tying that behavior to the model-test
  coverage ledger.

Both surfaces are boundary helpers. They should be tested as contracts, not as
structure-splitting targets.

## Goals / Non-Goals

**Goals:**

- Add ordinary tests that directly exercise the two external boundary surfaces.
- Add FlowGuard source obligation, code contract, and test evidence rows for
  those surfaces.
- Run the model-test alignment check and the focused tests after edits.
- Fix implementation bugs only if the new boundary tests expose one.

**Non-Goals:**

- No branch pruning or file splitting.
- No public behavior change.
- No release, tag, push, or publication.
- No edits to active `.flowpilot/runs/` state.

## Decisions

- Use source-audited Model-Test Alignment rows rather than only relying on the
  full diagnostic text scan. Rationale: the updated FlowGuard route cares about
  whether a test is tied to a model obligation and code contract, not just
  whether a filename appears in the test corpus.
- Put the tests in a focused runtime-contract test module. Rationale: these
  tests describe stable external boundaries and should not depend on the larger
  router material-flow fixture unless necessary.
- Preserve existing material-flow runtime tests. Rationale: they remain useful
  integration evidence, while the new tests provide direct boundary coverage.

## Risks / Trade-offs

- Direct boundary tests can become too shallow if they only assert constants.
  Mitigation: assert the negative authority semantics that matter to FlowPilot:
  Controller asides cannot authorize progress or create events, and material
  maps cannot include sealed body text.
- Material artifact map tests may accidentally read sealed body files.
  Mitigation: construct metadata references and assert only safe paths, hashes,
  and body-reference boundaries.
- FlowGuard alignment could be overclaimed if evidence rows do not call the
  declared symbols. Mitigation: use source-audited code contract rows and run
  `run_flowpilot_model_test_alignment_checks.py` after edits.
