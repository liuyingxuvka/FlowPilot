## Context

FlowPilot already has runtime-projected result contracts, a
`ContractDrivenFakeAIResponder`, contract-exhaustion models, current-contract
Cartesian matrices, Reviewer cards, PM repair policy, and Controller
break-glass recovery. Recent real-run evidence showed that these layers are not
yet connected strongly enough: runtime can know and enforce a rule while the
first role packet does not expose that rule clearly enough for an AI to comply.

This change extends existing surfaces only. It does not introduce another
router, reviewer lane, fake runtime, or compatibility shim.

## Goals / Non-Goals

**Goals:**

- Make fake-AI rehearsals contract-driven at the responder layer, including
  malformed syntax, bad formats, hidden projection gaps, finite-option mistakes,
  partial repairs, corrected retries, repeated no-delta failures, and
  GlassBreak threshold behavior.
- Make AI-visible contract projection a first-class test target: if runtime
  validates a field, option, active id, projection, owner coverage, or stage
  boundary, the current packet contract must expose it before the first
  response.
- Keep Reviewer strong and independent without adding dual authority. Reviewer
  hard blockers flow to PM repair work, then back to Reviewer recheck. PM does
  not bypass Reviewer by declaring a quality blocker invalid.
- Put reviewer review-window metadata in runtime-checkable envelope/body
  fields, preferably reusing existing `packet_kind`, `route_scope`,
  `gate_kind`, `reviewer_review_scope`, `subject_stage_evidence_matrix`,
  `authorized_result_reads`, and `current_handoff_contract`.
- Keep GlassBreak as controlled control-plane recovery, not normal blocker
  handling or completion evidence.

**Non-Goals:**

- Do not add a second fake-AI framework.
- Do not add legacy aliases, missing-field defaults, wrapper compatibility, or
  prose parsing to accept old shapes.
- Do not let Controller read sealed bodies outside break-glass/recovery grants.
- Do not let PM directly pass a Reviewer-blocked gate without repair/recheck or
  terminal escalation.

## Decisions

1. **Extend `ContractDrivenFakeAIResponder` instead of hand-writing malformed
   fixtures.**

   The responder already derives legal and illegal payloads from
   `current_handoff_contract.required_report_contract`. Extending it keeps the
   test source of truth aligned with runtime contracts and prevents future
   fixtures from silently encoding stale assumptions.

2. **Add projection obligations beside runtime validators.**

   Runtime rejection tests prove that bad material is blocked. They do not prove
   that the role had enough information in the first packet. Each validator
   obligation that affects AI output must therefore have a matching
   AI-visible projection assertion.

3. **Represent reviewer scope as structured metadata, not only prose.**

   The reviewer card can explain the scope, but the runtime and tests need a
   checkable source. Existing structured fields are preferred. A small
   `review_window` field is allowed only where existing fields cannot express
   the window.

4. **Keep Reviewer blockers on the PM repair path.**

   PM organizes repair, creates repair nodes or scoped repair packets, and
   resubmits to Reviewer. Repeated irreconcilable or impossible repair loops
   escalate to user stop or GlassBreak. PM does not become an appeal court over
   Reviewer quality decisions.

5. **Treat format rejection and GlassBreak as separate test dimensions.**

   A malformed result must be clearly rejected and repairable before repeated
   failure is considered. One-to-four repeated same-family failures exercise
   reissue/retry behavior; the fifth same-family failure exercises the
   break-glass threshold.

## Risks / Trade-offs

- **Risk: Matrix explosion** -> Use generated cells and shard summaries from
  existing contract-exhaustion and current-contract matrices; focused unit
  tests cover representative concrete families, while FlowGuard models prove
  declared cell ownership.
- **Risk: Reviewer scope gets over-specified** -> Reuse existing structured
  fields first and add only one minimal review-window field if required.
- **Risk: Tests pass but fake AI does not model real syntax failures** -> Add
  raw-body mutation methods to the responder for invalid JSON object syntax,
  markdown-wrapped JSON, prose+JSON, arrays, empty bodies, and trailing commas.
- **Risk: GlassBreak becomes an ordinary path** -> Keep ordinary tests asserting
  no GlassBreak before threshold, and BreakGlass tests asserting sealed-body
  reads require recovery grants and do not approve gates.

## Migration Plan

1. Add OpenSpec requirements and tasks.
2. Extend the fake AI responder and coverage-cell generation.
3. Update runtime contract projection only for fields already enforced or newly
   required by the specs.
4. Add focused runtime tests and FlowGuard matrix checks.
5. Refresh generated result artifacts, topology, install sync, and local
   install audit.
6. If a broad regression fails in unrelated peer-agent work, preserve the
   failure evidence and avoid reverting unrelated edits.
