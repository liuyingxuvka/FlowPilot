## Why

FlowPilot already asks PM and Reviewer to preserve source intent, but a real miss showed a route can still downgrade a user's concrete deliverable into a reachable-only inventory or honest missing-status report. This must be hardened generically so any core deliverable, evidence, quantity, quality, or source requirement cannot be silently replaced by "what was reachable" or "what was honestly missing."

## What Changes

- Strengthen PM cards so root contracts, route skeletons, node acceptance plans, material/research packages, child-skill bindings, final ledgers, and closure decisions preserve the user's concrete deliverable rather than rewriting it into a weaker status, inventory, or report-only objective.
- Strengthen Reviewer cards so reviews compare PM and Worker outputs to the original user intent, actively challenge reachable-only or honest-missing substitutions, run or add review-side checks when appropriate, and block rather than pass when a missing deliverable is only explained.
- Strengthen FlowGuard operator guidance and model obligations so process/product route models reject paths where the original target is claimed complete after PM or Reviewer accepted a downgraded substitute.
- Extend synthetic and contract-driven fake-AI coverage with generic non-downgrade bad cases across deliverable domains, not image-specific wording.
- Keep runtime/router responsibilities mechanical only: no semantic string matching, no new fields, no new flow, no compatibility/fallback surface.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: prompt cards must include generic core-deliverable non-downgrade guidance while preserving current role boundaries and runtime mechanical ownership.
- `formal-gate-review-standards`: formal review standards must block PM or Reviewer acceptance when concrete user requirements are replaced by reachable-only, status-only, report-only, or honest-missing substitutes.
- `flowpilot-packet-review-flow`: PM package-result disposition and Reviewer package review must not convert an incomplete/missing deliverable explanation into acceptance evidence.
- `role-child-skill-use`: child-skill standards and outputs must inherit the parent user-intent standard and must not lower the parent deliverable into a weaker child-skill output.
- `synthetic-agent-coverage-matrix`: synthetic coverage must include generic PM/Reviewer/Worker downgrade branches across finite deliverable classes.
- `flowguard-boundary-test-alignment`: model-test alignment must bind the new non-downgrade obligations to prompt/card, fake-AI, synthetic replay, and FlowGuard model evidence.

## Impact

- Prompt assets under `skills/flowpilot/assets/runtime_kit/cards/`.
- FlowGuard model surfaces under `simulations/`, especially meta/capability process models, contract-driven fake-AI profiles, synthetic agent coverage, and model-test alignment artifacts.
- Tests under `tests/` that validate card instruction coverage, fake-AI profiles, synthetic replay, blocker routing, and model-test alignment.
- Install and synchronization scripts are not redesigned, but final validation must run install sync/check commands because prompt and model assets are packaged skill surfaces.
