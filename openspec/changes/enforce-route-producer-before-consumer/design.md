## Context

FlowPilot already has a route-process gate that checks serial traversal, route
hierarchy, worker-ready leaves, repair return paths, stale evidence handling,
and terminal closure. The live SkillGuard run showed a missing route viability
class: an early public artifact can be placed before later implementation or
validation nodes that the artifact needs to cite or prove.

The repository constraint is to keep one current structured path per behavior.
This change therefore uses the existing route plan shape, existing PM
decisions, existing FlowGuard operator report outcomes, and existing Reviewer
blocker/recommendation fields.

## Goals / Non-Goals

**Goals:**

- Make route order correctness explicit: producers must precede consumers.
- Let PM prevent inverted dependencies while drafting routes.
- Let the FlowGuard operator treat inverted artifact dependencies as a
  route-process viability failure.
- Let Reviewer independently challenge the same ordering gap at route review
  and current-node entry.
- Add focused coverage without expanding the runtime schema.

**Non-Goals:**

- No new route-node fields, dependency ledgers, packet kinds, or compatibility
  aliases.
- No hardcoded README-only workflow.
- No requirement that public documentation must always be last.
- No demand for future-stage terminal evidence at early node-entry review.

## Decisions

1. **Use existing route text as the inspection surface.**
   The check reads node order plus existing `title`, `required_outputs`,
   `acceptance_criteria`, `deliverable_checks`, and `validation_checks`. This
   keeps the repair prompt/model-owned rather than schema-owned.

2. **Model the invariant as producer-before-consumer.**
   If node B consumes, cites, summarizes, validates, or promises output from
   node A, then A must be earlier than B, be the same current node's owned work,
   or be already available as external/current material. If B requires future
   A, the route is not viable as drafted.

3. **Keep repair choice with PM.**
   FlowGuard operator and Reviewer should block or recommend route repair when
   ordering is inverted, but they should not prescribe a single repair shape.
   PM may reorder, narrow, merge, split, defer, or add a later refresh when that
   is the smallest valid route correction.

4. **Separate route-order failure from early-stage evidence demands.**
   At node entry, Reviewer should reject plans that depend on future nodes, but
   should not require future-stage Worker, test, fixture, or release evidence
   merely because the current node is an early bounded slice.

## Risks / Trade-offs

- **Risk: Overblocking legitimate early docs.** -> The wording allows early
  current-boundary artifacts when they do not consume future outputs.
- **Risk: Prompt-only guidance drifts.** -> Add card instruction coverage and
  focused model/test cases that assert the new invariant is present.
- **Risk: FlowGuard operator becomes a second PM.** -> The operator reports the
  route-process failure and PM owns the corrected route shape.
