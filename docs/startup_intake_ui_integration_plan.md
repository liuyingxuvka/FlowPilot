# Startup Intake UI Integration Plan

## Scope

This change replaces the current chat-based three-question FlowPilot startup
boundary with the native startup intake UI. The UI is a bootloader surface, not
a Controller surface.

The current bootloader sequence starts with:

| Current order | Existing action | Replacement intent |
| --- | --- | --- |
| 1 | `ask_startup_questions` | Replace with `open_startup_intake_ui` |
| 2 | `write_startup_awaiting_answers_state` | Coalesced by UI confirm/cancel result |
| 3 | `stop_for_startup_answers` | Coalesced by modal UI wait boundary |
| 4 | `record_startup_answers` | Coalesced by UI result validation |
| 5+ | `emit_startup_banner` and later boot actions | Reused after UI confirm |

The post-answer startup sequence should continue to reuse the existing
bootloader flow: startup banner, run shell, current pointer, index, runtime kit,
mailbox, user intake packet, role slots, and Controller core.

## Implementation Checklist

| Step | Change | Files expected | Done when |
| --- | --- | --- | --- |
| 1 | Add a focused FlowGuard model for UI startup intake replacement before production edits. | `simulations/flowpilot_startup_intake_ui_model.py`, runner, results | Safe path passes and known-bad mutations fail. |
| 2 | Promote the WPF preview into a repo-owned startup intake UI asset. | `skills/flowpilot/assets/ui/startup_intake/` | UI writes receipt, envelope, body, and result files without printing body text. |
| 3 | Replace the first bootloader wait boundary. | `skills/flowpilot/assets/flowpilot_router.py` | Router returns `open_startup_intake_ui` instead of chat three-question prompt. |
| 4 | Validate UI result as the source of startup answers. | `flowpilot_router.py` | Confirm maps toggles to existing startup answer enums; cancel terminates startup. |
| 5 | Preserve startup answer compatibility. | `flowpilot_router.py`, tests | Existing post-answer boot actions still see `startup_answers` and skip old chat wait actions. |
| 6 | Seal the user request body before Controller starts. | `flowpilot_router.py`, `packet_runtime.py` | Controller-visible state stores body path/hash only, not body text. |
| 7 | Make reviewer startup fact-check and live review use UI records. | reviewer startup card, startup model/tests | Reviewer checks UI result/receipt/envelope/hash and no longer searches chat for answers. |
| 8 | Update prompt and install checks. | `SKILL.md`, `scripts/check_install.py`, tests | Local install self-check covers the UI startup path. |
| 9 | Sync local install after tests. | install script / installed skill path | Local installed FlowPilot matches repository source. |

## Hazard Checklist

| Hazard id | Possible regression | FlowGuard/model expectation |
| --- | --- | --- |
| H1 | Controller starts before UI confirm/cancel. | Fail if Controller core loads before confirmed UI result. |
| H2 | User closes UI and FlowPilot still creates a run or starts roles. | Fail if cancel path reaches run shell, Controller, roles, heartbeat, or Cockpit. |
| H3 | Router or Controller-visible envelope leaks user body text. | Fail if body text appears in bootstrap state, startup answers, user request envelope, or Controller handoff. |
| H4 | UI result is accepted without receipt, envelope, body path, or matching body hash. | Fail if any required artifact or hash check is missing. |
| H5 | Toggle values drift from existing startup answer enums. | Fail if toggle mapping is missing or produces non-enum values. |
| H6 | Background agents or heartbeat are started against UI OFF choices. | Fail if `single-agent` still spawns live roles or `manual` still creates heartbeat. |
| H7 | Cockpit UI is assumed open when UI choice is chat or Cockpit launch fails. | Fail if display status ignores UI choice or lacks fallback. |
| H8 | Reviewer startup or live review relies on chat text instead of UI result/receipt/envelope evidence. | Fail if reviewer pass does not reference UI record, receipt, and hash evidence. |
| H9 | Existing old three-question payload path remains the only legal startup path. | Fail if UI-confirmed startup cannot advance through reused post-answer boot actions. |
| H10 | Long-running model/test work overwrites peer-agent changes or unrelated dirty files. | Verification plan avoids broad formatters and only touches scoped files. |

## Model-First Acceptance

Before production code edits, the new FlowGuard model must show:

- the approved UI-confirmed path reaches post-startup work without Controller
  body access;
- the cancelled UI path terminates before any run, role, heartbeat, or
  Controller start;
- every hazard above has a corresponding known-bad mutation that fails;
- the model preserves the existing old-flow compatibility boundary where
  startup answers gate the later bootloader actions.

## Verification Plan

Run focused checks after each slice:

1. `python simulations/run_flowpilot_startup_intake_ui_checks.py`
2. Router unit tests covering confirm, cancel, body leak, hash mismatch, and
   enum mapping.
3. Existing startup/prompt checks:
   - `python simulations/run_flowpilot_startup_control_checks.py`
   - `python simulations/run_prompt_isolation_checks.py`
   - `python simulations/run_startup_pm_review_checks.py`
4. Existing broader checks only after focused checks pass:
   - `python simulations/run_meta_checks.py`
   - `python simulations/run_capability_checks.py`
   - `python scripts/check_install.py`
