## Context

The current FlowPilot direction is already specified by `adopt-runtime-requested-role-bindings`, `clean-flowpilot-runtime-language-surfaces`, and `add-new-flowpilot-lifecycle-guard`: bind only the responsibility requested by the new runtime, use lifecycle guard foreground duty, reject stale prior-run authority, and keep old Router surfaces out of fresh-run authority. The remaining issue is drift across active artifacts that still encode the older fixed topology.

## Goals

- Make every active user-facing or role-facing prompt describe requested responsibilities rather than fixed people, fixed workers, fixed runtime roles, or six-role recovery.
- Remove Process/Product-scope FlowGuard operator split names from current runtime responsibility menus, tests, and model obligations. Use only the explicit `flowguard_operator` responsibility for FlowGuard work.
- Keep system validation and system closure as ledger/runtime outcomes rather than dispatched Validator or Closure Officer roles.
- Keep `flowpilot_new.py` as the fresh formal entrypoint and lifecycle guard source. `flowpilot_router.py` wording may remain only where it is clearly legacy/diagnostic or in historical archived material.
- Avoid compatibility aliases and old-field preservation. If a current runtime/test path still accepts old responsibility names, remove or rename it.
- Synchronize installed skill content after repository validation.

## Non-Goals

- Do not archive or rewrite historical OpenSpec archives merely because they contain old wording.
- Do not weaken sealed-body isolation, current-run identity, ACK/result evidence, PM authority, reviewer independence, FlowGuard validation strength, or final-preflight requirements.
- Do not push, tag, publish, deploy, or package a release.
- Do not merge unrelated Cockpit or effective-outcome work into this cleanup.

## Decisions

### Decision: Requested Responsibilities Are The Runtime Vocabulary

The new runtime speaks in concrete requested responsibility keys. Current startup, resume, role recovery, packets, and docs must avoid "all runtime roles", fixed worker A/B requirements, fixed role binding recycle, and runtime roles-ledger language.

### Decision: FlowGuard Work Uses The Single Operator

Process/Product-scope FlowGuard operators are old topology. Current FlowGuard work should be addressed to the single `flowguard_operator` responsibility for development, process, route, evidence, product-function, and modelability obligations.

### Decision: Validation And Closure Are System Outcomes

The old Validator and Closure Officer packet chain is not retained. Current validation and closure are router/system/PM-ledger outcomes after accepted evidence, not separate role bindings.

### Decision: No Compatibility Layer

Old responsibility names, fixed topology fields, and legacy prompt paths are removed or renamed rather than preserved behind aliases. Tests must expect rejection or absence of old names.

### Decision: Evidence Is Regenerated Only For Touched Boundaries

Focused checks run first. Broader meta/capability checks may run in the repository background log contract, then topology is rebuilt/checked after generated model/test artifacts settle.

## Risks

- Broad terminology cleanup can stale model-test alignment and project topology artifacts. Mitigation: rerun focused model/test checks and rebuild topology before final install sync.
- Runtime API renaming can expose hidden tests that still use `flowguard_operator`. Mitigation: update public tests and search remaining current-authority surfaces before commit.
- Installed skill drift can leave local use broken even after source cleanup. Mitigation: run explicit install sync and freshness check at the end.
