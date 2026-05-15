## Context

Controller already receives role cards and a generated
`runtime/controller_action_ledger.json`. Long-running foreground waits can
outlive the role card's attention window, so the ledger itself needs a compact
reminder at the point Controller is repeatedly reading for work.

The current two-table scheduler already exposes `continuous_controller_standby`
when the Router daemon is live and no ordinary Controller row is ready. This
change hardens the ledger-local guidance around row order, foreground
attachment, and standby re-entry when new Controller work appears.

## Goals / Non-Goals

**Goals:**

- Put a short English prompt directly in the generated Controller action ledger
  before the action rows.
- Make the action ledger read like a top-to-bottom work board.
- State the simple foreground rule: if FlowPilot is still running, Controller
  keeps the foreground Controller work attached.
- Make `continuous_controller_standby` a persistent monitoring duty that wakes
  back into ordinary row processing when Router exposes new Controller work.
- Preserve Controller authority limits: metadata/ledger reads only, no sealed
  body reads, no route invention, no worker implementation, no gate approval.

**Non-Goals:**

- Do not add a user-facing prompt to `display_plan.json`.
- Do not add a large duplicated role card inside the ledger.
- Do not change PM, reviewer, worker, or officer authority.
- Do not run heavyweight meta or capability model regressions for this narrow
  prompt and standby semantics change.

## Decisions

1. **Ledger prompt location**

   Add a top-level `controller_table_prompt` object to
   `runtime/controller_action_ledger.json`, emitted before `actions`.

   Rationale: Controller repeatedly reads this file as its work board. Keeping
   the reminder in the ledger avoids depending only on the role card while
   keeping user display data clean.

   Alternative considered: prepend the prompt to `display_plan.json`. Rejected
   because `display_plan.json` is a user-facing projection, not the Controller
   authority/work-board source.

2. **Prompt size**

   Keep the prompt compact and English-only. It names row order, receipt/mark
   complete behavior, foreground attachment while FlowPilot is running, standby
   as continuous monitoring, and authority limits.

   Rationale: A long copied role card would make the ledger noisy and easier to
   drift from source cards.

3. **Standby row semantics**

   Keep `continuous_controller_standby` as the final fallback row, but update
   its generated payload and plan sync text so it says the row is continuous,
   remains `in_progress`, watches Router status and the action ledger, and
   returns Controller to top-to-bottom row processing when new Controller work
   appears.

   Rationale: This matches the user's desired mental model: standby is a watch
   post, not a final checkmark.

4. **Focused verification**

   Extend the existing two-table scheduler model/runtime/install checks. Skip
   `run_meta_checks.py` and `run_capability_checks.py` by explicit user
   direction because this change is narrower than full route/capability
   regression.

## Risks / Trade-offs

- [Risk] A future prompt edit weakens the foreground rule. -> Mitigation: add
  install/runtime assertions for the ledger prompt terms and standby wording.
- [Risk] Controller interprets standby as completion after one poll. ->
  Mitigation: keep `plan_status` as `in_progress`, keep do-not-complete cases,
  and assert the text says standby is continuous monitoring.
- [Risk] The ledger prompt becomes a second full role card and drifts. ->
  Mitigation: keep it compact and anchored to table-local duties only.
- [Risk] Existing generated run files lack the new prompt. -> Mitigation:
  change the generator and local installation; old runs may pick it up when the
  ledger is rebuilt, while new runs get it immediately.
