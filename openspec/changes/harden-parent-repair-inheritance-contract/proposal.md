## Why

The June 14 FlowPilot run exposed a control-plane loop where
`repair_parent_scope` created an empty replacement parent/module node, PM prose
described child work that was not present in machine-readable route fields, and
the runtime kept rotating through new repair nodes instead of blocking the
control-plane defect.

This change is needed now because the existing canonical no-in-place-repair
rule is correct, but parent-scope repair did not define how old children are
inherited and how new repair children become the current executable subtree.

## What Changes

- Harden `repair_parent_scope` so it still creates a replacement parent repair
  node, but the node must have a nonempty set of new active repair child nodes.
- Preserve old child nodes and accepted child results as inherited read-only
  history/context on the replacement parent; do not let inherited children
  regain current routing authority.
- Require PM parent-scope repair output to include a structured parent repair
  contract with repair child specs; prose-only child routing is invalid.
- Require runtime validation to reject replacement parent/module repair nodes
  whose active `child_node_ids` are empty.
- Require node acceptance plan and reviewer prompts to block parent/module
  repair plans that mention child leaves in prose without current route-node
  child ids.
- Require parent backward replay to consume current repair child results plus
  inherited accepted evidence, and to block when no current repair child result
  exists.
- Harden FlowGuard report acceptance so contradictory evidence artifacts
  (`missing_code_contract`, blocker findings, missing obligations, stale or
  progress-only evidence) cannot pass only because the top-level report says
  `passed: true`.
- Harden break-glass counting so a same problem repeated through
  `node-repair-vN` lineage counts as one repair loop even when old physical
  nodes are superseded.
- Add observed and same-class regression tests, fake AI rehearsals, FlowGuard
  model cases, and install-sync validation for the repaired parent-scope path.

## Capabilities

### New Capabilities

None. This is a current-contract hardening of existing repair, parent-entry,
FlowGuard alignment, and fake-rehearsal capabilities.

### Modified Capabilities

- `route-repair-replacement-policy`: define replacement parent repair node
  inheritance and active repair child requirements.
- `recursive-route-parent-entry`: require parent/module replay to distinguish
  inherited historical children from current active repair children.
- `blocker-repair-policy`: make same-lineage repair loops trigger break-glass
  instead of being hidden by superseded physical node ids.
- `flowguard-boundary-test-alignment`: require FlowGuard pass acceptance to
  inspect subject-bound evidence artifacts, not only result shape.
- `multiround-fake-ai-control-rehearsal`: cover bad PM, reviewer, and
  FlowGuard outputs that previously allowed empty parent repair loops.

## Impact

- Runtime mechanics in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Runtime packet/result contracts in
  `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`
  when parent repair contract fields are surfaced.
- PM, Reviewer, and FlowGuard operator cards under
  `skills/flowpilot/assets/runtime_kit/cards/`.
- Focused FlowGuard models and result artifacts in `simulations/`, especially
  canonical repair scope rotation and blocker repair information flow.
- Router/runtime unit tests, route-mutation parent-backward tests, card
  instruction coverage tests, fake project rehearsal tests, and install sync
  checks.
- Installed local FlowPilot skill under the local Codex skills directory
  through the repository install-sync scripts after validation.
