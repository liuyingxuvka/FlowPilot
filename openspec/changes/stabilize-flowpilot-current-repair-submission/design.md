## Context

FlowPilot already has the current mechanical contract for blocker repair:
runtime derives `repair_evidence_obligations`, PM must return
`repair_obligation_disposition`, and required blocker/target/upstream bodies
are delivered through the existing `authorized_result_reads` and
`current_handoff_contract` path.

The failure is not a missing runtime protocol. The role-facing repair packet
still includes a short `decision`/`reason` example, `open-packet` returns the
raw sealed body without a top-level submission checklist, and focused tests
still use the short form as a positive repair result in several paths.

## Goals / Non-Goals

**Goals:**

- Make the current PM repair submission contract visible as a role-facing
  checklist and skeleton.
- Remove fixed short examples that conflict with obligation-bearing PM repair
  packets.
- Keep authorized evidence delivery inside the existing `open-packet`
  current-run, role-scoped path.
- Update focused tests so valid paths submit the complete current shape while
  reason-only repair remains rejected.
- Refresh FlowGuard/model-test/install evidence after changing runtime,
  prompt-card, and test surfaces.

**Non-Goals:**

- No lower standard for PM repair decisions.
- No compatibility alias, fallback parser, old-field translation, or missing
  field default.
- No new packet kind, new role, new ledger, new gate, or parallel repair
  decision surface.
- No change to Controller sealed-body visibility.
- No promotion of secondary coverage matrices into FlowPilot runtime protocol.

## Decisions

1. **Project existing packet body fields instead of adding fields.**

   `required_result_body_fields`, `conditional_required_fields`, and
   `minimal_valid_shape` already exist in PM repair packet bodies. `open-packet`
   should project them into a top-level `submission_checklist` for role
   usability. This avoids a new source of truth.

2. **Use packet skeletons instead of fixed examples.**

   PM repair instructions should say that the current packet's
   `minimal_valid_shape` is the example. A fixed `decision`/`reason` object is
   misleading whenever obligations, route plans, waiver authority, parent
   repair contracts, or terminal supplemental repair contracts are required.

3. **Keep runtime as the mechanical validator.**

   Role cards and handoff text make the checklist visible, but runtime remains
   the owner of missing-field rejection, authorized-read receipts, branch
   skeletons, and reissue/block behavior.

4. **Use tests to preserve strictness, not loosen it.**

   Positive tests should build PM repair results from the current packet
   skeleton. Negative tests should continue proving that `decision`/`reason`
   alone is rejected when `repair_evidence_obligations` exist.

5. **Use FlowGuard as evidence, not as a new normal-path protocol.**

   Model-Test Alignment, lifecycle guard, model mesh, and topology checks
   should verify the repair submission path and evidence freshness. They should
   not introduce new runtime fields for this change.

## Risks / Trade-offs

- **Risk:** The checklist becomes another stale copy of the packet body.
  **Mitigation:** derive it directly from the sealed packet body at
  `open-packet` time.
- **Risk:** Prompt text still buries the obligation rule.
  **Mitigation:** move the PM repair pre-submit rule to the top of the PM role
  and PM repair phase guidance.
- **Risk:** Tests pass by using helper internals instead of exercising the
  runtime packet contract.
  **Mitigation:** test helpers should read the actual PM repair packet body and
  complete the returned skeleton.
- **Risk:** Parallel agent edits touch nearby runtime or tests.
  **Mitigation:** keep diffs narrow, inspect current files before each edit,
  and do not revert unrelated modifications.

