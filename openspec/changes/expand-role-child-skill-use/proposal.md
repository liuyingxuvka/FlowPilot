## Why

FlowPilot already treats child skills as PM-selected resources, but the current wording is too easy to read as "skills are selected only for delivered product work and mainly used by workers." This can make PMs miss local planning, specification, review, or modeling skills that would improve the FlowPilot process itself.

## What Changes

- Expand child-skill selection so PM must consider both deliverable-support skills and process-support skills.
- Allow selected child skills to be bound to PM, reviewer, process FlowGuard officer, product FlowGuard officer, worker A, or worker B, depending on the stage and purpose.
- Require role-scoped skill-use evidence whenever a selected skill materially affects planning, acceptance, route design, execution, review, modeling, or validation.
- Extend reviewer checks so a pass can verify PM/officer/reviewer skill use when that role was assigned a selected skill, not only worker skill use.
- Preserve the existing boundary that raw local skill availability is candidate-only and never authorizes use by itself.
- Preserve existing worker `Child Skill Use Evidence`; add a role-general evidence concept rather than replacing the worker path.

## Capabilities

### New Capabilities
- `role-child-skill-use`: Selected child skills may support product work or FlowPilot process work, may be assigned to any formal role, and require role-scoped usage evidence plus reviewer-checkable obligations.

### Modified Capabilities
- None.

## Impact

- Runtime prompt cards for PM child-skill selection, child-skill gate manifest extraction, node acceptance planning, reviewer plan review, reviewer result review, and role guidance.
- FlowPilot templates for child-skill selection, child-skill gate manifests, node acceptance plans, packet bodies, and result bodies.
- Planning-quality and output-contract tests that verify role-skill bindings and role-skill evidence wording exist.
- FlowGuard capability/meta models or a focused model covering hazards where process-support skills are ignored, role-skill bindings are missing, or PM/reviewer/officer skill use is self-attested without evidence.
- Installed local FlowPilot skill must be synchronized after repository validation.
