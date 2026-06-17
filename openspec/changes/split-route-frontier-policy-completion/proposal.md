# Split Route Frontier Policy Completion

## Why

The latest FlowGuard Model-Test Alignment and synthetic-agent coverage matrix both
report one remaining `needs_structure_split` finding for
`skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py`.
The module is a public route-frontier facade surface with 602 lines, above the
320-line public-facade diagnostic threshold.

## What Changes

- Keep the original `flowpilot_router_route_frontier_policy_completion` module as
  the public facade.
- Move route-authority rejection helpers, legal-action/child-entry helpers, and
  node-completion ledger helpers into focused child owner modules.
- Preserve the original exported symbol set and router binding behavior.
- Register the completed split in the existing model-test-code diagnostic repair
  plan and add focused facade/child parity tests.

## Impact

- No new FlowPilot runtime protocol, state family, compatibility path, fallback
  alias, or field migration is introduced.
- The public import path remains stable for existing router code.
- The regenerated MTA and synthetic-agent matrix should no longer report a
  `needs_structure_split` gap for this surface.
