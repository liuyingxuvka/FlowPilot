## Why

Recent FlowPilot review runs show that Reviewer can produce strong, concrete
challenge when a clear blocker is visible, but ordinary pass reviews still drift
toward mechanical checklist confirmation. The existing design already has
Reviewer challenge intent and PM suggestion disposition surfaces; the weak link
is that current review-window projection and skeleton wording do not reliably
carry stage-specific challenge expectations into every review packet.

## What Changes

- Bind every declared `review_flow_id` to one fixed Reviewer stage card or
  stage challenge focus inside the existing review-window path.
- Add generic stage cards only for declared review flows that currently have no
  dedicated stage mind-set; these cards attach to existing review flows and do
  not create a second review process.
- Strengthen `review_depth_rule`, packet templates, role handoff wording, and
  Reviewer examples so skeletons are treated as mechanical field checklists, not
  answer prose.
- Replace weak "mechanically complete" and generic "consider 9/10
  optimization" samples with task-specific challenge samples that name the
  reviewed object, weakest evidence, failure hypothesis, and PM-actionable
  adopt/reject rationale.
- Tighten PM suggestion disposition guidance so actionable Reviewer suggestions
  are accepted, rejected with reason, repaired/reissued, routed through the
  current route-mutation path, waived with authority, stopped for the user, or
  bound to an already named downstream node/gate. "Later maybe" deferral is not
  a valid disposition.
- Extend fake-AI review-window profiles and tests to cover generic low-quality
  review responses, stage-specific challenge responses, and full Cartesian
  `review_flow_id x profile x material state x retry class` coverage.
- Preserve current-contract boundaries: no new review result fields, no legacy
  aliases, no fallback review path, no production natural-language judge for
  suggestion specificity, and no project-specific Reviewer card tied to one
  observed application bug.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-gate-review-standards`: Reviewer packets must receive fixed
  stage-specific challenge expectations through the existing review-window
  path, and Reviewer output samples must require concrete challenge and PM
  decision-support content in existing fields.
- `role-scoped-quality-repair-prompts`: PM guidance must disposition actionable
  Reviewer suggestions through existing PM-owned dispositions without treating
  soft optimization as Reviewer authority or vague deferral.
- `synthetic-agent-coverage-matrix`: fake-AI reviewer profiles must include
  specific and low-quality/generic responses across the declared review-window
  Cartesian matrix.
- `tiered-flowpilot-test-validation`: focused tests and model checks must prove
  the stage-card mapping, prompt/card coverage, fake-AI coverage, install sync,
  and topology freshness before this change can support broad confidence.

## Impact

- Affected code: review-window contract projection, runtime review-window
  handoff text, packet/result skeletons, contract-driven fake AI, and focused
  tests.
- Affected prompt/card files: Reviewer core card, stage Reviewer cards, PM core
  and PM event/repair guidance, role handoff text, and packet body template.
- Affected validation: OpenSpec verification, FlowGuard project audit/upgrade,
  focused unit tests, fake-AI Cartesian tests, card instruction coverage,
  topology build/check, install sync audit, and meta/capability model
  regressions.
