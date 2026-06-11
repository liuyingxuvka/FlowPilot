## Why

A live ProjectRadar FlowPilot run exposed a model miss after the
`node_prework_flowguard` removal. The old pre-worker FlowGuard packet was
correctly rejected by the new runtime, but the repair path then surfaced a
separate stage-boundary problem: Reviewer blocked a PM `node_acceptance_plan`
repair because it expected Worker artifacts, per-candidate evidence, and fresh
checker output before Worker dispatch.

FlowPilot already has the intended current trunk:

`PM node plan -> Reviewer node-plan review -> Worker -> post-result FlowGuard -> Reviewer result review`.

The failure means the model, prompts, and fake-AI coverage did not sufficiently
separate "review the PM node plan" from "review the Worker result". The fix
should use the existing trunk and repair flow rather than adding a new review
lane, compatibility path, fallback, or legacy packet family.

## What Changes

- Treat this as a FlowGuard model miss, not a one-off prompt typo.
- Extend the current-node trunk model so Reviewer stage ownership is explicit:
  node-plan Reviewer checks PM plan quality, while result Reviewer checks real
  Worker artifacts and evidence.
- Add hazards for Reviewer requiring Worker artifacts during PM
  `node_acceptance_plan` review and for Reviewer accepting Worker results
  without artifacts or post-result FlowGuard evidence.
- Update existing Reviewer guidance and review-packet instructions so ordinary
  `node_acceptance_plan` review never invents pre-worker artifact or
  FlowGuard requirements.
- Add focused fake-AI/runtime/card tests that prove PM node-plan review and
  Worker-result review use different evidence standards.
- Keep the new-only rule: old `node_prework_flowguard` packets remain
  unsupported and are not translated into current evidence.

## Impact

- `simulations/flowpilot_prework_flowguard_gate_model.py`
- `simulations/run_flowpilot_prework_flowguard_gate_checks.py`
- `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md`
- `skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md`
- Focused FlowPilot runtime, fake-AI, card coverage, FlowGuard, install-sync,
  and topology validation.
