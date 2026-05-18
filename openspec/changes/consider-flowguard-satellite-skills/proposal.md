## Why

FlowGuard now exposes more satellite skills, and FlowPilot should make them visible during PM child-skill selection without adding another routing system.

## What Changes

- Remind PM child-skill selection to consider FlowGuard satellite skills as process-support candidates.
- Keep existing selected-skill, role-skill binding, task-packet, and evidence rules as the authority for actual use.
- Avoid adding a trigger matrix, new gates, or broader role-core prompt obligations.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `role-child-skill-use`: PM child-skill selection explicitly considers FlowGuard satellite skills as process-support candidates.

## Impact

- `skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_selection.md`
- `templates/flowpilot/pm_child_skill_selection.template.json`
- Focused planning-quality, card-instruction, and capability-routing validation.
