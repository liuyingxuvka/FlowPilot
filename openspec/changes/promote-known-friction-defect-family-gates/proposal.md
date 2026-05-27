## Why

FlowPilot already has a known-friction regression matrix for six historical
control-plane failure classes, but those rows are still local matrix records.
After the FlowGuard upgrade, recurring same-class model misses should be
promoted into FlowGuard-owned defect-family gates and then consumed by the
final risk ledger.

This keeps FlowPilot from treating repeated dirty families as another product
reminder or local checklist item. The higher-level gate must live in the
FlowGuard evidence chain.

## What Changes

- Promote each accepted known-friction row into a recurring defect-family gate.
- Require every promoted family to carry a model obligation, authority
  boundary, observed historical failure, same-class generalized case,
  historical holdout, and current external proof.
- Feed the defect-family gate decisions into Risk Evidence Ledger rows so
  final confidence is blocked, scoped, or full from FlowGuard evidence.
- Add known-bad cases proving missing promotion, progress-only proof, stale
  proof, and internal-only proof are rejected.
- Update defect-governance guidance so future FlowPilot defects know when a
  single bug becomes a higher-level dirty family.

## Impact

- Affected model/check surface:
  `simulations/flowpilot_known_friction_regression_matrix.py`.
- Affected tests:
  `tests/test_flowpilot_known_friction_regression_matrix.py`.
- Affected docs:
  `docs/defect_governance_flowguard_risk_intent.md`.
- No Router runtime behavior is changed by this proposal; it upgrades the
  model/evidence gate that decides whether the existing fixes can support a
  full confidence claim.
