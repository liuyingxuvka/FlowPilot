## Context

FlowPilot already has current-contract rules for packet/result mechanics,
repair blockers, break-glass, final closure, and synthetic agent coverage.
The DataBank run nevertheless completed with a dirty ledger because several
adjacent rules did not meet at the same commit points:

- `pm_flowguard_acceptance` results were formally accepted before the Reviewer
  and system validation gate finished.
- `packet.accepted_result_id` could remain after the target result was later
  marked `review_blocked`.
- `repair_accepted_packet_assignment` trusted a dirty accepted pointer and
  restored the packet to `accepted`.
- PM FlowGuard acceptance and review packets derived from a repair gate lost
  `repair_blocker_id`.
- final closure used current-target filtering and did not consume stale active
  blockers, open break-glass incidents, or pending permanent-fix patches.
- final/backward replay Reviewer packets were ordinary node packets with no
  authorized result-body reads.

The repair must stay in the current runtime shape: existing packet, result,
review, gate, blocker, authorization, and break-glass fields are enough. The
runtime must enforce mechanical invariants; Reviewer and FlowGuard remain the
semantic/process judges.

## Goals / Non-Goals

**Goals:**

- Prevent PM FlowGuard absorption from becoming formal packet acceptance before
  review and validation.
- Make every accepted-result pointer mechanically provable at each consumer.
- Reject assignment repair when the accepted result is missing, not accepted,
  review-blocked, rejected, or validation-failed.
- Keep repair blocker identity stable across all existing repair-chain derived
  packets.
- Block closure and terminal return when whole-ledger hygiene is dirty, even if
  the dirty object is not current-target-effective.
- Give final/backward Reviewer packets authorized evidence bundles through the
  existing `authorized_result_reads` channel.
- Prove the miss with observed regressions, same-class fake-AI/D-card
  Cartesian cases, and FlowGuard model alignment.

**Non-Goals:**

- No new persistent fields, packet kinds, roles, ledgers, UI, or compatibility
  aliases.
- No runtime semantic judging of Reviewer quality, PM ambition, or broad task
  meaning.
- No fallback that translates old or malformed packages into current packages.
- No weakening of repair identity checks, Reviewer blockers, or FlowGuard
  blockers.

## Decisions

1. Delay formal acceptance for `pm_flowguard_acceptance`.

   PM `decision=accept` means "submit this absorption to Reviewer"; it is not
   final acceptance. The runtime should record the result and gate association,
   issue the Reviewer packet, and leave `accepted_result_id` empty until the
   existing review/system path commits acceptance.

   Alternative considered: accept first and clear later on review block.
   Rejected because the bug came from the early accepted label itself.

2. Add a read-side accepted pointer invariant.

   A small internal helper will validate that `accepted_result_id` points to an
   existing result with `status=accepted` and `accepted=true`, with no failed
   formal review or failed validation for that result. Consumers that use the
   pointer for repair, closure, route evidence, or terminal return must fail
   closed when the invariant is broken.

   Alternative considered: only patch `review_result`. Rejected because dirty
   pointers can also arrive from interrupted runs, manual patching, or
   assignment-repair races.

3. Preserve repair identity at the derivation point.

   `_ensure_pm_flowguard_acceptance_packet_for_gate` must pass
   `repair_blocker_id=gate.blocker_id`. Downstream review/recheck packets then
   inherit the same current-contract identity through existing packet/envelope
   wiring. Binding checks stay strict.

   Alternative considered: allow later rebinding when the packet lacks the id.
   Rejected because that recreates guessing and caused the observed conflict.

4. Split terminal hygiene from current-target scheduling.

   `_blocker_current_effective` remains useful for ordinary "what do we do
   next?" scheduling. Final closure and terminal return require a stricter
   whole-ledger hygiene pass that scans active blockers, accepted pointers,
   review/validation contradictions, break-glass incidents, and pending
   permanent-fix patches without current-target filtering.

   Alternative considered: broaden `_blocker_current_effective` globally.
   Rejected because normal scheduling still needs current-target focus.

5. Use existing authorization rows for final Reviewer evidence.

   Final and backward replay packets should carry result-body access through
   `authorized_result_reads`, using existing result hashes and role
   restrictions. Project files remain ordinary filesystem evidence; sealed
   result bodies stay authorized explicitly.

   Alternative considered: instruct Reviewer to read sibling bodies manually.
   Rejected because it violates sealed-body authority.

6. Treat the observed run as a model miss and coverage seed.

   The observed `packet-0205/result-0209/event-5616`, missing
   `repair_blocker_id`, open `blocker-0006` break-glass incident, stale
   `blocker-0007`, and empty `packet-0238` authorization become regression
   seeds. ContractExhaustionMesh/fake-AI coverage expands them into finite
   Cartesian axes rather than hand-picked examples.

## Risks / Trade-offs

- [Risk] Existing tests may rely on early acceptance for PM FlowGuard
  absorption. -> Mitigation: move dependent flow to "submitted awaiting review"
  and add focused tests for the intended review path.
- [Risk] Whole-ledger hygiene might block legitimate stopped/quarantined
  histories. -> Mitigation: classify only active/open/pending/failed states as
  blockers and allow explicit closed/quarantined dispositions when the current
  break-glass contract says they are terminal.
- [Risk] Reviewer authorization bundles can become too broad. -> Mitigation:
  build from existing result ids and hashes, deduplicate, and keep file access
  outside sealed-body authorization.
- [Risk] Cartesian coverage becomes too large for quick validation. ->
  Mitigation: keep the finite axes model-owned, produce a coverage receipt, and
  run focused fake-AI/model checks before release-wide suites.

## Migration Plan

No data migration or compatibility path is added. New runs must follow the
hardened current contract. Historical dirty runs remain historical evidence and
may be used only as regression fixtures, not as valid current completion
evidence.

## Open Questions

None. If implementation shows an existing field cannot express a required
state, the task must pause and update this design before adding a field.
