## Why

FlowPilot terminal review already checks final ledger coverage, requirement
evidence, supplemental repair contracts, and backward replay from the delivered
output. The remaining gap is final cleanliness: a run can satisfy the explicit
goal while leaving code, documents, models, tests, generated artifacts, or UI
surfaces in a state that is hard to maintain or not clean enough for high
quality delivery.

Reviewer can currently raise quality concerns, and PM final ledger already
tracks some structure debt, but there is no mandatory terminal review surface
that asks the Reviewer to inspect the final artifact itself for cleanup,
maintainability, model/test/document completion, and other delivery hygiene.

## What Changes

- Add a mandatory `final_artifact_hygiene_review` section to terminal Reviewer
  replay reports and the generic human-review template.
- Require PM evidence quality and final ledger work to inventory final artifact
  hygiene surfaces before terminal closure.
- Add a terminal replay segment for final artifact hygiene so Reviewer cannot
  pass completion without checking it.
- Classify hygiene findings as current-goal required repair, clean-delivery
  required repair, PM decision support, or future contract candidates.
- Route required hygiene findings through the existing terminal supplemental
  repair contract and repair-node flow. No second workflow or always-on cleanup
  node is introduced.
- Extend supplemental repair gap kinds with `final_artifact_hygiene_gap` and a
  bounded `hygiene_category` for reporting and closure.

## Capabilities

### New Capabilities

- `flowpilot-final-artifact-hygiene-review`: terminal Reviewer-owned final
  artifact cleanliness and maintainability review, PM disposition, final ledger
  closure, and supplemental repair handoff.

### Modified Capabilities

- `terminal-ledger`: final ledgers and terminal replay maps must include final
  artifact hygiene closure rows and replay segments.
- `flowpilot-closure-kernel`: terminal closure must block while required final
  artifact hygiene findings remain unresolved.
- `flowpilot-terminal-supplemental-repair`: supplemental repair items can close
  final artifact hygiene gaps while preserving the frozen original contract.
- `hard-gate-coverage-matrix`: model/test evidence must include hygiene gap
  coverage and negative scenarios.

## Impact

- Reviewer, PM evidence quality, final ledger, closure, and repair cards.
- Human review, terminal replay map, final route-wide ledger, node acceptance,
  and packet body templates.
- Runtime supplemental repair gap classification, terminal replay validation,
  final ledger closure, closure blockers, and branch shapes.
- FlowGuard terminal supplemental repair model, acceptance testmesh coverage,
  focused runtime tests, fake rehearsal evidence, install sync, and local
  validation artifacts.
