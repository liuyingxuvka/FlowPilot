# Dependency Map

This experimental skill is now standalone for the concept-led UI redesign
front half. Product inspection, functional framing, display element review,
information architecture, concept search, selected concept review, divergence
review, FlowGuard UI structure gate routing, platform screenshot discipline,
and app/software icon gating live in this skill's own `references/` and
`scripts/` files.

Do not require or load the old `concept-led-ui-redesign` skill.

## Built-In Concept-Led Assets

- `references/functional-framing.md`
  - Role: product job, user task, required data/actions/states, non-goals,
    display element draft/review, FlowGuard UI model inputs, information
    architecture, presentation mode, content pressure, duplicate information
    and control review, and QA implications.
- `references/concept-brief.md`
  - Role: imagegen concept prompt contract, visual anchors, color/effect
    contract, functional zones, content/localization constraints, app icon
    direction, and selected concept three-layer review/refinement.
- `references/design-search.md`
  - Role: first-round candidate sets, concept diagnosis, scoring matrix,
    second-round synthesis, readiness checks, final concept evaluation package,
    final concept selection, and app icon pairing.
- `references/visual-qa-loop.md`
  - Role: rendered screenshot trust, functional walkthrough, pointer
    reachability, post-interaction evidence, content/localization, app icon,
    in-UI icon, motion/light/depth, and final visual QA.
- `references/divergence-review.md`
  - Role: classify concept-vs-implementation differences as accepted, UI fix,
    concept revision, or regeneration, using the final concept evaluation
    package during screenshot comparison.
- `references/platform-notes.md`
  - Role: desktop, high-DPI Windows, canvas/custom drawing, slide, and other
    non-standard rendering guidance.
- `scripts/app_icon_asset_check.py`
  - Role: mechanical checks for transparent raster app icon masters and optional
    Windows `.ico` export. It supports but does not replace visual judgment.

## Companion Skill Dependencies

- `flowguard-ui-flow-structure`
  - Expected path:
    `$CODEX_HOME/skills/flowguard-ui-flow-structure/SKILL.md`
    or `~/.codex/skills/flowguard-ui-flow-structure/SKILL.md`
  - Source used for this install:
    `https://github.com/liuyingxuvka/FlowGuard`
  - Role: conditional model-first UI interaction structure gate before concept
    search, imagegen, Figma translation, or frontend implementation. It owns
    UI interaction modeling, parent/child topology, stable regions, menu
    levels, control/event/display ownership, overlays, duplicate information,
    duplicate same-level controls, and structure-contract propagation.
- `imagegen`
  - Role: generated bitmap concept images and app/software icon candidates.
  - Host source: Codex built-in/system skill in this environment. Treat this as
    a host capability; another host may provide an equivalent image generation
    tool.
- `frontend-design`
  - Expected path: `$CODEX_HOME/skills/frontend-design/SKILL.md`
    or `~/.codex/skills/frontend-design/SKILL.md`
  - Source used for this install:
    `https://github.com/anthropics/skills/tree/main/skills/frontend-design`
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

- Missing `flowguard-ui-flow-structure`: continue only for visual-only
  `minor_ui_fix` work that has no workflow, state, hierarchy, control,
  overlay, navigation, or display-ownership risk. For substantial redesigns or
  explicit FlowGuard requests, mark the run `blocked` or `partial`; do not
  replace FlowGuard with prose-only modeling.
- Missing `frontend-design`: stop as `blocked`; implementation skill is
  required.
- Missing `design-iterator`: continue with manual bounded iteration and mark
  the dependency gap.
- Missing `design-implementation-reviewer`: continue with manual deviation
  review and mark the dependency gap.
- Missing `imagegen`: skip concept bitmap generation only if the user did not
  explicitly require concept images and the route can use a written visual
  contract or authoritative reference; otherwise mark `partial` or `blocked`.
- Final integrated acceptance cannot be replaced by any single companion skill.
  Reviewer output, FlowGuard output, visual QA, or geometry evidence can each
  satisfy its own ledger row, but none can by itself prove the whole run. A
  missing companion skill may use a manual equivalent only when that equivalent
  records the same evidence, freshness, skip/deviation rationale, and
  final-verdict impact; otherwise the final run is `partial` or `blocked`.

The built-in concept-led references are part of this skill. If one of them is
missing from the installed skill, treat the installed skill as stale or broken
rather than falling back to the old `concept-led-ui-redesign` dependency.

If FlowGuard is present but the real `flowguard` package cannot be imported,
do not claim a FlowGuard pass. Record the exact import failure, skip only when
the route is visual-only, and otherwise mark the run `partial` or `blocked`.

## Non-Interactive Override

If a companion skill suggests asking the user for optional preferences, the
orchestrator must convert that question into a conservative default and record
the assumption. Only true blockers may stop the run.
