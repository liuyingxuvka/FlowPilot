## Design

This change treats the diagnostic as the controlling backlog. Work proceeds in
three gates:

1. Contract gate: remove all `missing_test` gaps with source-audited ordinary
   tests bound to concrete code contracts.
2. Structure gate: split only modules whose external contract is already
   pinned by ordinary tests and whose split is safe under peer-agent and
   micro-module-explosion constraints; otherwise record an explicit
   StructureMesh deferral with follow-up split guidance.
3. Evidence gate: replace stale, failed, progress-only, or local-only
   background evidence with final artifacts or explicit non-release
   classification.

## External-Contract Test Strategy

Each remaining owner module is assigned to one focused contract suite by
domain. Tests must assert observable behavior: accepted inputs, returned JSON
or Python value shape, event names, written files, ledger rows, error classes,
idempotency, and public import/CLI behavior. Tests must not pass merely by
calling private helpers or inspecting internal implementation steps.

The source-contract plan in
`simulations/run_flowpilot_model_test_alignment_checks.py` remains the binding
layer. For each module batch, add:

- one or more model obligations;
- concrete code-contract rows that point at the owner function definitions;
- ordinary test-evidence rows with exact test ids;
- explicit `external_outputs=()` for write-only/error-only functions;
- explicit side-effect declarations for file writes, updates, queue writes,
  or background artifact generation.

## StructureMesh Strategy

Structure splits happen after contract tests for the touched runtime surface
are green. Compatibility facades must keep public import names stable. New
child modules should be grouped by model block, side-effect ownership, or
schema/ledger boundary, not by arbitrary line count.

Validation tooling splits such as `scripts/run_test_tier.py` and model-check
runners may proceed with TestMesh/StructureMesh parity evidence even when they
are not runtime owner modules. The old command-line entrypoints must remain
compatible. In this pass `scripts/run_test_tier.py` was the safe split; the
remaining model-check runners are deferred with child-module plans because
they require a dedicated runner StructureMesh target and proof-fingerprint
update before code movement.

## Stale Evidence Strategy

Background evidence is only accepted from final artifacts. Progress text is
liveness evidence, not proof. `public_release_check` must not be counted as
public release proof while URL checks are skipped. Legacy full model checks may
either be rerun to final status or explicitly downgraded as historical
non-current evidence so they no longer block current diagnostic convergence.
Current Meta/Capability release proof comes from valid layered full parent
proofs; failed or still-running legacy monolithic artifacts remain visible as
raw compatibility-oracle evidence.

## Coordination

Other agents may be active. The implementation must avoid staging pre-existing
dirty result files unless the current task intentionally refreshed them. Broad
formatters, lockfile edits, dependency installs, and unrelated cleanup are out
of scope.

## Validation

At minimum, each batch runs focused tests plus:

- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json`
- `python simulations/run_flowpilot_structure_maintenance_checks.py`
- `openspec validate complete-flowpilot-diagnostic-convergence --strict`

Final validation also runs the fast background tier, relevant router/release
background tiers, local install sync/audit, and a final git status review.
