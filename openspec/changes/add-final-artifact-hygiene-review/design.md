## Context

The current FlowPilot closure path is already strong on requirement evidence:
PM builds an evidence quality package, PM builds the final route-wide ledger,
Reviewer performs terminal backward replay, and PM closes only after the ledger
and replay pass. Terminal supplemental repair already adds an append-only
contract for terminal gaps while keeping the original frozen contract intact.

The new requirement is not to add a separate cleanup workflow. The requirement
is to make the terminal Reviewer check the final artifact itself for whether it
should be left cleaner, more complete, and more maintainable before completion.
If that check finds work required for clean delivery, PM converts it into the
existing supplemental repair path.

## Goals / Non-Goals

**Goals:**

- Make final artifact hygiene a required terminal review surface.
- Keep PM as the owner of disposition, repair strategy, waiver, and stop
  decisions.
- Reuse terminal supplemental repair contracts and repair nodes for required
  hygiene work.
- Distinguish required cleanup from optional improvements and true future work.
- Keep the original frozen contract immutable.
- Preserve the existing mainline closure path and repair cap.

**Non-Goals:**

- No always-on cleanup execution node.
- No second WorkflowPilot tail, role family, or parallel closure loop.
- No broad repository cleanup unrelated to the current user goal and current
  run artifacts.
- No legacy field aliases, prose parsers, missing-field defaults, or historical
  run migration.

## Decisions

1. Reviewer owns the terminal hygiene inspection.

   Terminal Reviewer reports include `final_artifact_hygiene_review`. The
   Reviewer classifies findings as:

   - `current_goal_required_repair`
   - `clean_delivery_required_repair`
   - `pm_decision_support`
   - `future_contract_candidate`

   The first two classifications block terminal pass until PM repairs, waives
   with authority, stops, or records a valid route mutation.

2. PM owns the final artifact hygiene inventory and closure.

   PM evidence quality package records an inventory of artifact families and
   surfaces that may need cleanup. PM final ledger records
   `final_artifact_hygiene_closure` rows and unresolved counts. PM closure is
   blocked while required rows remain unresolved.

3. Supplemental repair is the only execution tail.

   Required hygiene findings become terminal supplemental repair items with
   `gap_kind: "final_artifact_hygiene_gap"` and a `hygiene_category` such as
   `code_maintainability`, `test_coverage`, `model_coverage`,
   `document_cleanup`, `ui_polish`, `artifact_lineage`,
   `process_ledger_cleanup`, or `other`.

4. Terminal replay map carries a hygiene segment.

   PM maps a `final_artifact_hygiene` segment so Reviewer has an explicit
   target. Runtime-issued segment ids remain exact; missing or unexpected
   segments still block terminal replay.

5. Optional improvements do not become surprise blockers.

   `pm_decision_support` findings go to PM suggestion disposition.
   `future_contract_candidate` findings are not required for current closure
   unless PM explicitly imports them into the current supplemental contract.

## Risks / Trade-offs

- [Risk] The hygiene review becomes a broad cleanup mandate.
  -> Mitigation: required findings must link to the current user goal, current
  final artifact, or clean delivery of the current run. Broad unrelated debt is
  a future contract candidate.

- [Risk] Reviewer makes PM decisions.
  -> Mitigation: Reviewer reports classifications and evidence; PM decides
  repair, waiver, route mutation, stop, or future disposition.

- [Risk] Runtime treats optional suggestions as blockers.
  -> Mitigation: only `current_goal_required_repair` and
  `clean_delivery_required_repair` block terminal pass.

- [Risk] Existing terminal supplemental repair gets a second taxonomy.
  -> Mitigation: add one new `gap_kind` plus one `hygiene_category`, and reuse
  all existing supplemental repair projection, ledger, replay, and round-cap
  rules.

## Validation Plan

- Strict OpenSpec validation for this change.
- Focused runtime tests for terminal replay hygiene report validation,
  supplemental contract gap validation, final ledger unresolved hygiene
  closure, and terminal closure blockers.
- FlowGuard terminal supplemental repair model scenarios for missing hygiene
  contract, omitted final ledger closure, omitted replay segment, and optional
  suggestions not blocking.
- Acceptance testmesh ownership rows for final artifact hygiene coverage.
- Install sync and local install audit after focused validation passes.
