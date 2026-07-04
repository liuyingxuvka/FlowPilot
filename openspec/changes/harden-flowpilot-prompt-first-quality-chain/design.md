## Context

FlowPilot already has a single staged route with PM product architecture, root
contract, child-skill selection, node acceptance plans, worker execution,
reviewer gates, evidence quality, final ledger, and terminal backward replay.
The observed failure is a prompt-governance/model-miss issue inside that route:
concrete startup intent can be collapsed into generic acceptance wording, and
later reviews can pass process evidence without rechecking the actual delivered
artifact against the original user request.

The current repository explicitly separates ownership:

- Runtime/router owns mechanical validity and current-run authority.
- PM owns source-intent preservation, route decisions, repair decisions, and
  final closure decisions.
- Reviewer owns semantic quality review, evidence credibility, user-intent
  preservation, and pass/block decisions.
- FlowGuard operator owns process/model/state evidence, not final product
  quality by itself.

This change therefore uses prompt-card repairs and focused prompt/model tests
instead of a new runtime semantic validator or per-domain workflow.

## Goals / Non-Goals

**Goals:**

- Keep one universal FlowPilot route for software, writing, UI, data, research,
  release, and mixed work.
- Make PM preserve user intent as concrete acceptance rows before route and
  node work.
- Make Reviewer block generic acceptance, semantic dilution, child-skill
  standard loss, existence-only evidence, and final-artifact drift.
- Make selected child skills operate as standards lenses inside the current
  route.
- Make final ledger and terminal replay start from the delivered product and
  trace back to source requirements.
- Add focused tests/checks that catch the same failure class without
  overfitting to novels or software.

**Non-Goals:**

- Do not create software-specific, story-specific, report-specific, or
  UI-specific routes.
- Do not add broad new fields, ledgers, packet kinds, role types, or state
  families.
- Do not make runtime decide whether prompt text is semantically vague.
- Do not weaken existing packet/result contracts or role boundaries.
- Do not revert unrelated peer-agent changes.

## Decisions

### Decision: Prompt-first repair, not runtime semantic repair

The repair will update role cards and phase/reviewer cards so PM and Reviewer
must explicitly preserve source intent and challenge generic acceptance. Runtime
will only continue to enforce mechanical contract shape, current packet/result
identity, authorized review windows, and ledger presence.

Alternative considered: add a runtime check that blocks phrases such as
"complete the user's goal." Rejected because semantic vagueness is a reviewer
judgment; runtime text heuristics would be brittle and would violate the
repository's role-boundary discipline.

### Decision: Use existing acceptance and review surfaces

The repair will use existing `requirement_trace`,
`acceptance_item_registry_seed`, `acceptance_item_projection`,
`skill_standard_projection`, `active_child_skill_bindings`,
`pm_suggestion_items`, blockers, final ledger rows, and terminal backward replay
segments. Prompt text will say how these existing surfaces must be used.

Alternative considered: add `artifact_realization_profile` and new evidence
fields. Rejected for this iteration because the user asked for a lighter
upgrade and the existing surfaces can carry the behavior if roles are stricter.

### Decision: Child skills are standards lenses, not route branches

PM child-skill selection will remain candidate-based and minimum-complexity
aware. When a child skill is selected, PM must explain what standard it brings,
which role uses it, what evidence proves it was used, and where the standard is
projected into current route/node/review artifacts. This keeps one FlowPilot
route while allowing domain standards to affect pass/fail.

Alternative considered: introduce per-artifact-family subflows. Rejected
because it would fragment FlowPilot and create task-type special cases.

### Decision: Final replay starts from delivered output

Final ledger and terminal backward replay prompts will require the PM/Reviewer
to begin with the actual delivered artifact/system/output and trace backward to
source requirements and active acceptance items. Process evidence can support
freshness and route coverage, but cannot close a user-facing quality claim by
itself.

Alternative considered: leave final replay as ledger consistency only.
Rejected because ledger-only replay is the observed failure class.

## Risks / Trade-offs

- Prompt-only repairs can be ignored by weak agents -> Add focused prompt-card
  tests and FlowGuard model checks for omitted source-intent and existence-only
  evidence hazards.
- Stronger Reviewer wording may over-block nonessential improvements -> Keep
  existing PM suggestion guidance: only unmet hard requirements, semantic
  downgrades, missing proof, or unverifiable acceptance block current gates.
- Child-skill standards may bloat simple tasks -> Keep minimum sufficient
  complexity and require selected-skill reasons, rejected/deferred reasons, and
  role-scoped evidence.
- Existing peer edits may stale validation evidence -> Use
  DevelopmentProcessFlow execution-freshness review, rerun focused checks after
  edits, and treat background liveness as incomplete until exit artifacts exist.
