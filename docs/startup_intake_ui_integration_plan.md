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

## BOM Compatibility Repair Checklist

This is a targeted follow-up to the startup intake UI integration. The issue is
control-plane compatibility: Windows PowerShell 5 writes `Set-Content
-Encoding UTF8` files with a UTF-8 BOM, while Python `json.loads` on text read
with `encoding="utf-8"` rejects a leading BOM.

| Step | Optimization point | Concrete change | Files expected | Done when |
| --- | --- | --- | --- | --- |
| 1 | Model the encoding boundary before production edits. | Add BOM fields and known-bad encoding states to the startup intake UI FlowGuard model. | `simulations/flowpilot_startup_intake_ui_model.py`, runner results | The safe plan passes and BOM hazard mutations fail. |
| 2 | Fix UI source output. | Replace PowerShell `Set-Content -Encoding UTF8` for startup UI artifacts with a no-BOM UTF-8 writer. | `skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1` | Headless UI output starts with `{` for JSON files, not `EF BB BF`. |
| 3 | Keep Router compatible with old UI artifacts. | Read JSON with a BOM-tolerant codec while still writing canonical no-BOM JSON. | `skills/flowpilot/assets/flowpilot_router.py` | A legacy BOM JSON result parses without manual byte editing. |
| 4 | Avoid body marker leakage into PM packet text. | Strip a leading UTF-8 BOM when reading the sealed body into PM-bound packet body text. | `skills/flowpilot/assets/flowpilot_router.py` | Old BOM body files do not inject `\ufeff` into the PM packet text. |
| 5 | Add focused regressions. | Test UI headless output bytes and Router BOM JSON fallback. | `tests/test_flowpilot_router_runtime.py` | Tests fail before the repair and pass after it. |
| 6 | Sync installation and local git only. | Run install sync/check and commit scoped repair. | local install, local git | Installed FlowPilot matches repo; no GitHub push. |

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
| H11 | UI JSON result/receipt/envelope is written with a UTF-8 BOM and Router rejects it before startup answers can be recorded. | Fail if confirmed UI artifacts are not Router-readable without a manual byte rewrite. |
| H12 | Only one JSON artifact is fixed, while receipt or envelope still has BOM and fails later in validation. | Fail unless result, receipt, and envelope share the no-BOM/BOM-compatible contract. |
| H13 | Router relies only on a UI source fix and cannot read older already-generated BOM artifacts. | Fail if legacy BOM JSON artifacts cannot be parsed by the Router compatibility reader. |
| H14 | A UTF-8 BOM from the body file becomes a visible `\ufeff` character in the PM-bound packet text. | Fail if PM packet body construction can leak a leading encoding marker. |
| H15 | Encoding repair normalizes or rewrites the user's request semantics instead of only handling the BOM marker. | Fail if body hash verification is bypassed or if body text becomes Controller-visible. |

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
