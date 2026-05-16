## Why

The `meta` and `capability` FlowGuard models are still release-scale parent
graphs, so routine validation depends on proof reuse or long background runs
even though the repository now has an explicit model hierarchy and many focused
child models. This change turns that hierarchy into the default validation path
by making the heavy parents thin evidence aggregators while preserving full
legacy regressions for forced and release-level checks.

## What Changes

- Convert the default Meta and Capability parent checks from monolithic graph
  exploration to thin parent evidence checks over child model results, proofs,
  partitions, freshness, skipped-check visibility, and escalation obligations.
- Preserve full Meta and Capability regressions as legacy forced/background
  checks until equivalence and release gates prove they can be retired or kept
  only as periodic deep regressions.
- Add or update a machine-readable partition/invariant ledger that maps parent
  responsibilities to child models, shared kernels, parent-only checks, or
  explicit out-of-scope reasons.
- Add executable equivalence and stale-evidence hazards so thin parents reject
  missing child results, stale proofs, hidden skips, uncovered partitions,
  sibling overlap, and overclaimed release confidence.
- Update validation and sync surfaces so foreground checks use thin parents and
  hierarchy evidence, while heavyweight regressions run through the standard
  background log contract.
- Keep peer-agent work intact and include compatible concurrent changes in the
  final git submission instead of reverting unrelated work.

## Capabilities

### New Capabilities

- `flowguard-thin-parent-models`: Defines how FlowPilot Meta and Capability
  parent models become lightweight evidence aggregators over child model
  partitions while retaining full-regression escalation rules.

### Modified Capabilities

- `flowguard-model-hierarchy`: Extends the existing hierarchy contract from
  classification and partition coverage into default thin-parent validation,
  equivalence tracking, and foreground/background regression routing.

## Impact

- Affected code includes `simulations/meta_model.py`,
  `simulations/capability_model.py`, their runners, hierarchy and mesh model
  inputs, result/proof artifacts, validation scripts, install/sync scripts, and
  FlowGuard adoption documentation.
- The FlowPilot runtime protocol should not change unless implementation
  exposes a narrow validation hook needed to surface thin-parent evidence.
- Full Meta and Capability regressions remain available for `--force`,
  release-level validation, or background regression evidence; skipped,
  incomplete, or progress-only heavyweight runs must remain visible.
