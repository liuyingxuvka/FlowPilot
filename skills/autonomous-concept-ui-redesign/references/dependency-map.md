# Dependency Map

This experimental skill composes existing skills rather than duplicating their
full instructions.

## Local Skill Dependencies

- `concept-led-ui-redesign`
  - Expected path: `$CODEX_HOME/skills/concept-led-ui-redesign/SKILL.md`
    or `~/.codex/skills/concept-led-ui-redesign/SKILL.md`
  - Role: product framing, display element review, information architecture,
    concept search, design target, and final acceptance discipline.
- `imagegen`
  - Role: generated bitmap concept images and icon candidates.
- `frontend-design`
  - Expected path: `$CODEX_HOME/skills/frontend-design/SKILL.md`
    or `~/.codex/skills/frontend-design/SKILL.md`
  - Role: implementation and first rendered visual sanity check.
- `design-iterator`
  - Expected path: `$CODEX_HOME/skills/design-iterator/SKILL.md`
    or `~/.codex/skills/design-iterator/SKILL.md`
  - Source used for this install:
    `https://github.com/ratacat/claude-skills/tree/main/skills/design-iterator`
  - Role: bounded screenshot-analyze-fix loops.
- `design-implementation-reviewer`
  - Expected path:
    `$CODEX_HOME/skills/design-implementation-reviewer/SKILL.md`
    or `~/.codex/skills/design-implementation-reviewer/SKILL.md`
  - Source used for this install:
    `https://github.com/ratacat/claude-skills/tree/main/skills/design-implementation-reviewer`
  - Role: implementation-vs-baseline review, especially Figma-backed review.

## Missing Dependency Behavior

- Missing `frontend-design`: stop as `blocked`; implementation skill is required.
- Missing `concept-led-ui-redesign`: for `concept_redesign`, stop as `blocked`;
  for minor fixes, continue with compact contract.
- Missing `design-iterator`: continue with manual bounded iteration and mark the
  dependency gap.
- Missing `design-implementation-reviewer`: continue with manual deviation
  review and mark the dependency gap.
- Missing `imagegen`: skip concept bitmap generation only if the user did not
  explicitly require concept images; otherwise mark `partial` or `blocked`.

## Non-Interactive Override

If a dependency skill suggests asking the user for optional preferences, the
orchestrator must convert that question into a conservative default and record
the assumption. Only true blockers may stop the run.
