## Why

Recent FlowPilot blocker audits showed that the control plane can still pass through shallow repair and terminal closure paths even when ordinary project materials are available, blocker obligations are not answered item-by-item, role ownership is blurred, or final replay proves only ledger cleanliness. This change hardens the existing current-contract workflow without adding a parallel authorization system or broad new runtime fields.

## What Changes

- Clarify role prompt boundaries so PM, Worker, Reviewer, and FlowGuard Operator may read all non-sealed files under the current project root and current run root, while sealed body files still require runtime authorization.
- Reframe `material_artifact_map` as a navigation and audit index, not a permission allowlist, and expand it to index important non-sealed work artifacts.
- Require PM repair packets, Worker repair results, FlowGuard work-order reports, and Reviewer rechecks to close blocker obligations item-by-item using existing report fields.
- Preserve FlowGuard Operator scope: it answers the current FlowGuard work order and requested check items, while Reviewer owns final quality and user-intent judgment.
- Require public user-intent artifacts, final artifact projection, FlowGuard terminal coverage, and final quality replay to be current before closure.
- Harden role identity, accepted-result ownership, stale/superseded projection, break-glass threshold, and terminal supplemental repair behavior with model and test coverage.
- Add declared finite-universe Cartesian/interaction test coverage for public material access, sealed-body denial, blocker repair, FlowGuard work-order depth, reviewer quality, identity, final projection, terminal coverage, and break-glass.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `flowpilot-artifact-authority`: Clarify default ordinary file readability and sealed body exception handling.
- `material-artifact-map`: Make the map a broad navigation/audit index instead of a role permission allowlist.
- `blocker-repair-policy`: Require blocker repair packets and downstream outputs to answer blocker obligations item-by-item.
- `formal-gate-review-standards`: Assign final quality/user-intent blocking to Reviewer and work-order/checklist closure to FlowGuard Operator.
- `terminal-ledger`: Require current final artifact projection, FlowGuard terminal coverage, public user-intent replay, and terminal quality closure.
- `dispatch-recipient-gate`: Harden current role/agent ownership and stale/superseded result rejection.
- `flowguard-test-obligation-ownership`: Add model-test alignment for the new material, repair, terminal, identity, and projection obligations.
- `synthetic-agent-coverage-matrix`: Add finite-universe Cartesian coverage across roles, material states, blockers, route states, repeat depth, and terminal outcomes.

## Impact

- Prompt cards under `skills/flowpilot/assets/runtime_kit/cards/roles`, `cards/phases`, and `cards/reviewer`.
- Runtime material map helpers, terminal replay target/ledger validation, identity/projection checks, and fake E2E scenario controls under `skills/flowpilot/assets/`.
- FlowGuard models and runners under `simulations/`.
- Unit and synthetic tests under `tests/`.
- Install/sync checks and repository topology evidence.
