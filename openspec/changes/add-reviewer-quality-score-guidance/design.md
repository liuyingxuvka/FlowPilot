## Context

FlowPilot already has a small formal review result body with
`pm_visible_summary`, `findings`, `blockers`, and `pm_suggestion_items`. It also
has a single PM repair path for Reviewer blockers and a role-scoped repair
boundary that prevents Reviewer from directly modifying the artifact under
review.

The missing piece is a stable high-standard score interpretation that Reviewer,
PM, Worker, fake-AI rehearsals, and tests all share. The score must be visible
to PM and repair workers, but it must not become a second runtime schema or a
second authority path.

## Goals / Non-Goals

**Goals:**

- Make Reviewer score reports consistent and strict: `6/10` is the minimum
  user standard just met, `9/10` is the target, and `10/10` substantially
  exceeds user standards.
- Keep score text inside existing review body fields so Runtime does not need a
  new score column, field, or ledger.
- Make PM prompts understand the score scale when reading Reviewer reports.
- Make Worker repair prompts carry Reviewer score context when the repair packet
  includes authorized prior reports.
- Treat explicit quantitative requirements as hard gates when they are current
  and due.
- Extend fake-AI review-window coverage with score and quantitative profiles.

**Non-Goals:**

- Do not add new runtime fields such as `score`, `quality_score`, or
  `scorecard`.
- Do not let Reviewer force PM to optimize when hard gates pass.
- Do not let PM close a Reviewer hard blocker with prose instead of executable
  repair and Reviewer recheck.
- Do not replace existing review-window, PM repair, or packet-result contract
  surfaces.

## Decisions

1. **Text-only score placement.** Reviewer writes a compact score line in
   existing fields such as `pm_visible_summary`, `findings`, `blockers`, or
   `pm_suggestion_items`. This keeps Runtime mechanical validation small and
   avoids a parallel schema path.

2. **Strict scale.** `6/10` means the minimum user standard is just met.
   `7-8/10` means hard gates pass but quality should be considered for
   optimization. `9/10` is the normal FlowPilot target. `10/10` means
   substantially beyond the user's standard. Scores `1-5/10` normally fail the
   minimum hard gate unless the current contract explicitly allows a lower
   stage floor.

3. **Blockers remain hard-gate failures.** Reviewer blocks when the current
   minimum requirement fails, proof is missing, semantics downgrade, the
   acceptance surface is unverifiable, role boundaries fail, protocol is
   invalid, or explicit current quantitative requirements are under-delivered.
   A score below `9/10` with hard gates met is PM decision-support.

4. **PM owns optimization decisions.** PM sees the same scale and always has
   the option to optimize, continue, repair, waive, stop, or ask the user. This
   remains true whether or not Reviewer returned a blocker.

5. **Fake-AI matrix extension.** Existing review-window fake-AI profiles become
   the canonical rehearsal surface for score behavior. New profiles cover
   high-score pass, soft low-score pass, quantitative hard block, overblocking
   soft score, and recheck score context.

## Risks / Trade-offs

- **Risk: Score becomes a hidden schema.** Mitigation: tests assert score terms
  stay out of required runtime fields and required child fields.
- **Risk: Reviewer overblocks every sub-9 result.** Mitigation: prompt and
  fake-AI tests include the overblocking hazard and PM decision-support path.
- **Risk: PM ignores low scores.** Mitigation: PM prompt states that scores
  below `9/10` are normal optimization decision input even without blockers.
- **Risk: Worker receives only PM summary and misses Reviewer score context.**
  Mitigation: repair packets already carry authorized prior reports; prompt and
  runtime instruction text tell workers to read those reports and aim at the
  `9/10` target inside packet scope.
