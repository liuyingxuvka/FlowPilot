## Context

The current FlowPilot runtime already carries current input authority through
`current_handoff_contract`, `authorized_result_reads`, runtime body-open
receipts, semantic blockers, and route mutation records. The observed failure
is that different layers checked different slices:

1. A route-redesign FlowGuard check proved the v28 two-node handoff bridge was
   structurally valid.
2. A packet-local FlowGuard check proved the worker handoff result was valid.
3. Final return preflight still scanned old repair blockers directly and did
   not reuse the existing "current effective blocker" logic.

The repair should keep one current-contract path. Historical packets remain
audit evidence only; they are not translated into current authority.

## Goals

- Collapse noncurrent old repair-chain blockers before final return claims.
- Preserve current authorized-read mechanics for material handoff consumption.
- Keep Reviewer as semantic decomposition and quality gate.
- Keep FlowGuard as lifecycle and bad-case model evidence.
- Avoid new global material ledgers, new packet families, compatibility
  aliases, or broad route-node field additions.

## Non-Goals

- Do not modify ProjectRadar run history directly.
- Do not make packet-local FlowGuard evidence imply downstream PM
  authorization or final completion.
- Do not add a second PM-authored display plan.
- Do not loosen final return preflight for genuinely current blockers.
- Do not revive legacy repair or heartbeat authority paths.

## Design

1. **Use one current blocker filter.**

   Final return preflight should rely on the same effective-current predicate
   used by status projection. A blocker whose route node is noncurrent, whose
   repair packet is accepted/quarantined/superseded, or whose repair packet is
   stale for the active route must not be reported as a current final blocker.

2. **Supersede same-family repair blockers during route replacement.**

   Route mutation already supersedes explicitly affected repair packets. Extend
   that cleanup narrowly: when a mutation supersedes a missing-information
   repair path, older open blockers with the same blocker class, same route
   scope, and the same repair target family are marked
   `superseded_by_route_mutation` if their repair packets are already
   noncurrent. This is cleanup of obsolete currentness, not acceptance of old
   evidence.

3. **Model the full material handoff lifecycle.**

   Existing packet-local handoff checks stay valid but scoped. Add an enclosing
   lifecycle obligation:

   `producer result -> runtime authorized_result_reads -> downstream PM
   open-packet authorized input -> PM material-read authorization -> Reviewer
   review -> final preflight`.

   Bad cases include summary-only handoff, workspace path only, packet-id-only
   coupling, downstream PM not opening the required authorized read, and final
   preflight still seeing superseded blockers.

4. **Prompt only at decision points.**

   PM review-repair guidance should say repeated missing authorized material
   failures require route redesign into a handoff bridge or same-family
   supersession, not repeated same-shape repair packets. FlowGuard Operator
   route/process checks should simulate downstream handoff consumption when a
   route introduces such a bridge. Reviewer should block if the route relies on
   a worker or PM to infer material authority from summaries or stale paths.

5. **Validation before completion.**

   The implementation must prove the abstract model catches the old state,
   then prove runtime final-preflight behavior matches it. Model-test alignment
   and topology must be refreshed because model, test, card, and runtime
   surfaces change together.

## Validation

- OpenSpec strict validation for this change.
- Real FlowGuard package import and project audit.
- Focused FlowGuard blocker-repair and project-control information-flow model
  checks.
- Focused unit tests for final-preflight currentness and same-family route
  mutation cleanup.
- Model-test-alignment check.
- Card instruction coverage check.
- Topology build/check.
- Installed skill sync and install audits.
