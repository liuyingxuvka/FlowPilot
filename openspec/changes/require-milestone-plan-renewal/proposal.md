## Why

FlowPilot currently activates an initial route and normally advances through its
remaining node order after each accepted node. That makes the original plan
retain too much authority even after execution has produced better evidence,
new constraints, and visible deviations.

Modern long-running agents can use each completed major milestone as fresh
planning evidence. FlowPilot should therefore make plan renewal a simple,
unconditional control-loop invariant instead of adding risk tiers, optional
replanning heuristics, or an experimental old/new mode.

## What Changes

- **BREAKING** Treat every accepted top-level route node as a major milestone
  whose PM disposition cannot advance the frontier until a current milestone
  audit and a complete remaining route plan have passed the existing
  FlowGuard, PM-absorption, Reviewer, and system-validation chain.
- Define a major milestone mechanically from route topology
  (`parent_node_id == ""`). Nested execution children keep their local closure
  path and trigger the global renewal only when their top-level parent closes.
- Require the milestone audit to account explicitly for completed outcomes and
  evidence, deviations from prior expectations, remaining goal gaps, the prior
  plan's current fitness, and the rationale for the newly submitted plan.
- Require the remaining plan to span the current state through the final user
  goal. The next milestone must be execution-ready; later milestones may remain
  progressively coarser but may not be omitted.
- Permit a freshly justified plan to be identical to the prior remaining plan.
  It still passes through the hard gate, but exact equality does not create a
  gratuitous route version.
- When the plan changes, replace only the unfinished route suffix and preserve
  accepted milestones, their evidence, and their history.
- Permit an empty remaining plan only at a genuine terminal milestone after all
  current hard obligations are closed.
- Reject automatic continuation from the old remaining plan, missing audit
  fields, uncovered remaining obligations, premature empty plans, stale plan
  results, and Reviewer-blocked plan activation.
- Keep one current behavior. Do not add L0-L4 classification, a feature flag, a
  compatibility reader, a fallback route, or an A/B experiment.

## Capabilities

### New Capabilities

- `milestone-plan-renewal`: Defines the top-level milestone hard gate, current
  audit and remaining-plan contract, independent challenge chain, unchanged-plan
  handling, changed-suffix activation, recovery, and terminal empty-plan rule.

### Modified Capabilities

- `complete-ai-workstream-orchestration`: Strengthens PM's long-project duty so
  every completed major milestone renews the complete remaining plan from
  current evidence.
- `flowpilot-packet-review-flow`: Makes milestone PM disposition a staged,
  independently reviewed plan-renewal transaction before frontier advance.

## Impact

- Core runtime PM-disposition validation, staged effects, review-window
  contracts, route-version activation, frontier recovery, status projection,
  and packet instructions.
- FlowGuard route-replanning and development-process models plus their
  executable conformance checks.
- Focused runtime, contract, recovery, review-window, route-mutation, and
  final-closure tests.
- FlowPilot skill guidance and runtime cards as projections of the core runtime
  contract.
- SkillGuard contract-source/check-manifest refresh and installed consumer
  projection after source validation.
