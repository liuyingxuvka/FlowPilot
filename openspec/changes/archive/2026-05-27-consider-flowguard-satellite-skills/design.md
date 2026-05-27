## Context

FlowPilot already has child-skill selection, role-skill bindings, skill-standard contracts, task-packet projection, and evidence checks. The missing piece is only awareness: PM should remember that FlowGuard satellite skills are valid process-support candidates during selection.

## Goals / Non-Goals

**Goals:**

- Add a short PM-facing reminder during child-skill selection.
- Reflect the same reminder in the PM child-skill selection template.
- Preserve existing authority and evidence mechanics.

**Non-Goals:**

- No FlowGuard satellite trigger matrix.
- No new route gates or runtime state.
- No broad changes to officer, reviewer, worker, or Controller core prompts.

## Decisions

- Put the reminder in the PM child-skill selection phase because that is where local skills are intentionally classified.
- Keep wording short so long FlowPilot runs do not accumulate noisy role-core instructions.
- Use the existing `process_support` dimension instead of adding a new field or schema branch.

## Risks / Trade-offs

- Prompt-only awareness may not force every useful FlowGuard satellite skill to be selected. Mitigation: selected usage already becomes enforceable through existing role-skill bindings, and unselected usage can still be recommended through PM suggestions when evidence shows a gap.
