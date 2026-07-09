## Why

FlowPilot already has a stronger prompt-first quality chain, but the current
contract can still leave the most important standard implicit: PM may produce a
workable plan instead of a rich, high-standard product plan, and downstream
roles may receive only the local work packet instead of the user's original
standard plus PM's full execution intent. That makes "complete enough" easier
than "best reasonable product under the requested scope."

This change hardens the existing flow without adding UI, fallback behavior, or
new semantic runtime gates. PM must write the high-standard plan up front using
existing contract fields, Worker/Reviewer/FlowGuard prompts must explicitly use
the same current global standard references, and runtime/test coverage must
prove that required existing fields are projected into fake-AI and Cartesian
contract checks.

## What Changes

- Strengthen PM planning cards so PM must convert the user's original request
  into a rich, concrete, high-standard implementation intent before execution:
  requirements, acceptance rows, route nodes, node acceptance criteria,
  material sources, skill standards, risks, verification, and final deliverable
  expectations.
- Strengthen node-acceptance-plan guidance so each node package carries current
  global standard references using existing fields, especially root/user
  contract, product architecture, high-standard contract, acceptance item
  registry, route node, relevant material, risks, and verification intent.
- Strengthen Worker, Reviewer, and FlowGuard role cards so every backstage role
  is expected to consult the current user/PM standard in scope, make permitted
  high-quality improvements inside its authority, and escalate only real scope,
  acceptance, route, or authority changes.
- Align runtime contract projection with existing required fields only: if an
  existing field is already part of the current packet/result contract, fake-AI
  generation and runtime rejection must cover missing, empty, wrong-type,
  forbidden-alias, and finite-value cases. Runtime remains mechanical and does
  not decide whether a plan is semantically ambitious enough.
- Expand focused tests and FlowGuard models for Cartesian fake-AI coverage,
  current-field requiredness, PM plan detail, global-context propagation, and
  reviewer blocking of local-only or low-standard packages.
- Preserve current-contract discipline: no compatibility aliases, missing-field
  defaults, old-router fallback, extra UI, or new fields unless a later blocker
  proves existing packet/result/gate fields cannot represent the requirement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: prompt/card boundaries must require the
  current global standard references to travel through existing fields instead
  of hidden chat memory or local-only packet text.
- `role-scoped-quality-repair-prompts`: Worker/Reviewer/FlowGuard prompts must
  allow and expect in-scope high-quality completion while preserving role
  authority and PM escalation boundaries.
- `formal-gate-review-standards`: Reviewer gates must block local-only,
  low-detail, or source-intent-diluted packages when the existing referenced
  artifacts cannot recover the user/PM standard.
- `synthetic-agent-coverage-matrix`: contract projection coverage must include
  every existing required field family and Cartesian fake-AI package family for
  high-standard planning and node-context packets.
- `end-to-end-synthetic-agent-chaos-replay`: fake-AI replays must include
  missing global context, empty existing fields, low-standard plan packages,
  and corrected retries through the legal current-runtime path.

## Impact

- Affected prompt cards:
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/worker.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md`
- Affected runtime/test/model surfaces:
  - `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`
  - FlowPilot prompt/card coverage tests
  - AI contract projection and contract-exhaustion fake-AI tests
  - planning-quality and fake-AI runtime replay FlowGuard simulations
  - topology, install-sync, and local audit checks after implementation
