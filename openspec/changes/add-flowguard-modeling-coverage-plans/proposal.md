## Why

FlowPilot currently has strong root product and process model gates, but the
default flow can still let PM, officers, or reviewers treat child-skill, UI,
validation, prompt, or release risks as one broad model or a manifest review.
This change makes model coverage explicit before product modeling starts, while
preserving the core order: product model first, process model second, route
execution third.

## What Changes

- Generate a run-scoped FlowGuard capability snapshot once from Router startup,
  using portable Codex/project skill roots and the active Python FlowGuard
  package/schema instead of a user-specific hardcoded path.
- Require PM to read that snapshot before product modeling and write a Product
  Modeling Plan that decides which product-side model families are independent,
  merged, or intentionally not modeled.
- Require Product FlowGuard Officer outputs to follow the PM plan as a product
  model family rather than assuming one product model is sufficient.
- Require PM to select ordinary child skills after product model acceptance and
  map their standards into the child-skill manifest.
- Require PM to write a Process Modeling Plan before process modeling, including
  route hierarchy, child-skill conformance, validation, and repair-return model
  families.
- Require Process FlowGuard Officer outputs to follow that process model family
  plan and prove the process can cover the accepted product model family.
- Add focused FlowGuard coverage and tests for missing snapshot, missing PM
  modeling plans, single-model overcollapse, stale child-skill-only evidence,
  and route activation before model families are accepted.

## Capabilities

### New Capabilities

- `flowguard-modeling-coverage`: Startup FlowGuard capability snapshot,
  PM-owned product/process modeling plans, Product/Process Officer model
  families, and final coverage closure.

### Modified Capabilities

- `role-child-skill-use`: Role-skill bindings for PM, reviewer, officer, and
  worker uses must reference the run's modeling coverage plan when FlowGuard or
  child-skill standards materially affect a formal model, gate, or route node.

## Impact

- Affected FlowPilot protocol artifacts: PM product architecture, Product
  Behavior Model, PM child-skill manifest, PM process route model decision,
  Process Route Model, final ledger, and officer request/report templates.
- Affected runtime/templates: new FlowGuard capability snapshot and modeling
  plan templates, cards that require PM plans, and install checks that verify
  the new artifacts exist.
- Affected verification: new focused FlowGuard model/check runner, OpenSpec
  validation, focused card/template tests, install sync/audit, and background
  Meta/Capability regressions using the repository log contract.
