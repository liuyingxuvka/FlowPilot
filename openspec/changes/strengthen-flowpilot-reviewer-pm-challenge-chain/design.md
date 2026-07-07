## Context

FlowPilot already separates mechanical runtime validation, FlowGuard process
review, Reviewer quality review, and PM route authority. The current Reviewer
result contract also already has compact fields that can carry substantive
challenge: `pm_visible_summary`, `findings`, `blockers`, and
`pm_suggestion_items`.

The observed weakness is not a missing role or missing output field. Strong
Reviewer cards exist, but review-window packets for several current flows still
share the generic `review.any_current_subject` result family and expose a weak
generic skeleton. That makes the model satisfy the mechanical shape while
underusing the stage-specific challenge mind-set.

## Goals / Non-Goals

**Goals:**

- Preserve one current review path per declared review flow.
- Make each `review_flow_id` project a fixed stage challenge focus into the
  existing review-window path.
- Replace weak example prose with concrete challenge examples.
- Require Reviewer suggestions to be PM-actionable without adding fields.
- Require PM to disposition actionable Reviewer suggestions through existing
  PM-owned dispositions.
- Extend tests so stage mapping, card guidance, and fake-AI Cartesian coverage
  all fail if the chain drifts back to generic pass prose.

**Non-Goals:**

- No new review result fields, packet kinds, ledgers, roles, or state families.
- No compatibility alias, legacy parser, fallback generic-review path, or
  "newest run" inference.
- No production natural-language specificity judge that mechanically blocks
  outputs by parsing prose.
- No project-specific Reviewer card for one application bug; examples must
  stay generally useful for async/state/evidence hazards.
- No change to PM as the owner of optimization, route mutation, waiver, and
  final continuation decisions.

## Decisions

1. Add a current-runtime mapping from `review_flow_id` to stage card and stage
   challenge focus.

   The mapping is deterministic data owned by `review_window_contracts.py`.
   Runtime uses it to build the existing `review_depth_rule` text. Tests use it
   to prove every declared review flow has a fixed stage focus. This is not a
   result-body field and not an AI-selected route.

2. Fill true coverage gaps with generic stage cards.

   Existing cards remain the owner for route, node-plan, worker-result, parent
   replay, and final replay review. New cards are allowed only where an
   existing declared review flow lacks a clear stage mind-set, such as
   preplanning contract/discovery/skill-standard review and PM FlowGuard
   absorption review. These cards attach to existing phases; they do not create
   a second review process.

3. Keep specificity enforcement in prompts and tests, not production schema.

   Production runtime should validate mechanical contract shape and current-run
   ownership. It should not parse English to decide whether a suggestion is
   "specific enough". Focused tests can reject weak built-in templates,
   examples, and fake-AI fixtures because those are repository-owned text.

4. Use existing PM suggestion surfaces.

   Reviewer outputs continue to use `pm_suggestion_items`. PM disposition
   continues through the existing PM suggestion ledger and PM decision bodies.
   Guidance is tightened so `defer_to_named_node` means an already named
   downstream node or gate with evidence responsibility, not vague postponement.

## Risks / Trade-offs

- [Risk] Adding stage cards could look like a new process.
  -> Mitigation: bind cards only from existing `review_flow_id` rows and test
  that the review result family remains the existing family.

- [Risk] Stronger text examples could become hidden schema requirements.
  -> Mitigation: tests check repository-owned prompts/fixtures only; production
  runtime still owns mechanical validity and does not inspect prose quality.

- [Risk] PM suggestion guidance could convert soft quality ideas into hard
  blockers.
  -> Mitigation: Reviewer and PM cards continue to say that soft sub-9/10
  quality opportunities are PM decision-support unless they expose a hard
  current-gate failure.

- [Risk] Full regression commands are slow.
  -> Mitigation: run focused tests foreground, use the repository background
  artifact contract for long meta/capability checks, and inspect final exit
  artifacts before claiming pass.
