## Context

FlowPilot already has the right control structure for this change. PM owns node
acceptance planning and route redesign; Reviewer owns semantic plan review;
Controller owns user-facing status projection; Runtime owns mechanical fields
and progress-fraction calculation. The current cards already block
producer-before-consumer inversions and already expose
`progress_fraction.display`, but PM node plans can still pass with vague
checker wording and Controller status updates can omit the existing node
fraction too often.

This is a prompt/process tightening, not a runtime contract expansion.

## Goals / Non-Goals

**Goals:**

- Make PM ask whether a worker-ready node is concrete enough to name current
  artifacts, check surfaces, status vocabulary, and expected failure shapes.
- Route unclear current check surfaces through the existing PM node-boundary
  self-check, especially under-decomposition and `redesign_route`.
- Make Reviewer block abstract node plans before worker dispatch without
  demanding future worker evidence at plan time.
- Make Controller include runtime-owned node-fraction progress more reliably
  during legitimate user-facing status updates.
- Cover the prompt changes with existing card/model checks and sync the
  installed FlowPilot skill after validation.

**Non-Goals:**

- Do not add node plan fields, route fields, progress fields, ledgers, packet
  kinds, compatibility aliases, fallback parsing, or a README/document-specific
  freshness rule.
- Do not change child skills. Existing child-skill fidelity rules already make
  PM preserve selected skill standards and Reviewer check them.
- Do not change progress-fraction calculation. Runtime already owns it.
- Do not make Controller report every ACK, receipt, patrol, or internal ledger
  cleanup to the user.

## Decisions

1. **Prompt-only PM tightening.** Add guidance to the existing PM node
   acceptance card instead of changing `node_context_package`. PM can write the
   details in existing plan text, `acceptance_criteria`, `known_risks`,
   supporting notes, and acceptance-item projection.

2. **Node-boundary framing for unclear checks.** Avoid a hard phrase such as
   "if PM cannot say it, do not send Worker." The intended behavior is more
   precise: unclear executable checks are evidence that the node might be too
   broad, mixed, or under-split, so PM must consider existing route redesign
   with a replacement parent/module and ordered children.

3. **Reviewer blocks plan vagueness, not missing future results.** Reviewer
   guidance stays in the plan-stage boundary: Worker artifacts and fresh
   result-stage checks do not have to exist yet. Reviewer blocks only when the
   plan leaves current check surfaces, status vocabulary, expected failure
   shape, acceptance boundary, or worker outcome undefined.

4. **Progress display remains runtime-owned and quiet by default.** Controller
   guidance should say that when status is already user-facing, the exact
   `progress_fraction.display` should normally be included if present. A short
   status line is appropriate when the node fraction or active node visibly
   changes. Internal patrol/noise remains silent.

## Risks / Trade-offs

- **Risk: PM guidance becomes another hidden schema.** Mitigation: explicitly
  forbid new fields and keep examples in existing prose/criteria surfaces.
- **Risk: Reviewer starts demanding future Worker evidence.** Mitigation: keep
  the plan-stage boundary text adjacent to the new concrete-plan checks.
- **Risk: Controller becomes noisy.** Mitigation: limit new reporting to status
  updates that are already user-facing or node-fraction changes, and preserve
  quiet patrol defaults.
- **Risk: Prompt-only changes are under-tested.** Mitigation: add focused card
  coverage and run the existing planning-quality, prework/order, and controller
  patrol model checks.
