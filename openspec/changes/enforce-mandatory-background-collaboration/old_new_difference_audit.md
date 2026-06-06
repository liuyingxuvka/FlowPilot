# Old/New FlowPilot Difference Audit

This audit is the working classification for the strict current-contract pass.
It separates current FlowPilot features that must be preserved from legacy
FlowPilot surfaces that must be removed, rejected, or kept only as historical
or negative evidence.

## Current-Required Surfaces

| Surface | Current meaning | Required action |
| --- | --- | --- |
| `background_collaboration_authorized` | Startup acknowledgement that FlowPilot may use required background or parallel role surfaces. It is not a product-mode selector. | Preserve. `true` is required before role assignment, lease commit, resume rehydration, role recovery, or accepted role output. `false` stops startup or blocks current role work. |
| `resolve-role-assignment` | Current runtime entry for opening, reusing, replacing, or blocking exactly the responsibility requested by the current packet. | Preserve and hard-gate on current startup acknowledgement. |
| `lease-agent` | Current runtime commit point for a resolved role assignment and packet lease. | Preserve and hard-gate on current startup acknowledgement. Require assignment id; no direct lease fallback. |
| On-demand responsibility roles | Runtime-requested `pm`, `worker`, `reviewer`, `flowguard_operator`, and other packet responsibilities. | Preserve. Do not restore a fixed role set at startup or resume. |
| Foreground duty and patrol refresh | Current nonterminal waiting/recovery mechanism. | Preserve. Do not replace with heartbeat authority. |
| `host_kind` menu | Caller declares the requested host surface kind (`live`, `fake`, `dry_run`). | Preserve as a value menu only. Do not treat `live` by itself as proof that a background surface exists. |

## Old-Only Surfaces

| Surface | Old behavior | Current disposition |
| --- | --- | --- |
| `start_role_slots` | Fixed startup role-slot prewarming, historically tied to six role slots. | Reject or remove from active runtime. May appear only in archived material or negative tests. |
| `create_heartbeat_automation` | Startup/resume heartbeat authority. | Reject or remove from active runtime. Current waiting is foreground duty/patrol. |
| `heartbeat_or_manual_resume_requested` | Legacy combined heartbeat/manual resume event. | Replace positive tests with current manual resume commands or negative legacy-event tests. |
| `host_records_heartbeat_binding` | Legacy host heartbeat-binding recovery gate. | Replace positive tests with current blocker/reissue or role assignment flow; retain only negative tests. |
| `runtime_role_assistances` / `runtime_role_assistance_authorized` | Old startup option that allowed `allow`, `single-agent`, or unknown runtime role assistance modes. | Remove as current input. Do not translate into `background_collaboration_authorized`. |
| `single-agent`, `single_agent_role_continuity_authorized`, `single_agent_user_selected` | Old fallback route where FlowPilot could continue without background/parallel roles. | Remove positive path. Convert to blocked/negative tests. |
| `fresh_six_runtime_role_bindings_opened` and six-role count requirements | Old fixed six-role startup evidence. | Replace with current on-demand role-assignment evidence. |
| `templates/flowpilot/heartbeats/*` | Historical heartbeat templates. | Remove from install/current templates unless explicitly preserved as archived reference outside current runtime. |

## Rename-Or-Uncertain Surfaces

| Surface | Risk | Current action |
| --- | --- | --- |
| `runtime_role_assistance_capability_status` | Name suggests optional old assistance; some current code uses it for host capability review. | Rename toward mandatory background/parallel role capability or convert to negative-only where it still allows fallback. |
| `runtime_role_assistance_decision_recorded` | Name suggests optional old decision. | Replace with required background collaboration acknowledgement/capability state in models. |
| `RUNTIME_ROLE_KEYS` in resume/recovery helpers | May still imply fixed role-set recovery. | Audit each use: current recovery may target only roles from the current packet/transaction; broad fixed-role restoration must become negative or blocked. |
| `background role assistance` wording | Can sound optional. | Reword active prompts/cards/specs to required background/parallel collaboration. |

## Historical-Only Surfaces

Archived OpenSpec changes, old planning documents, generated historical result
JSON, and preserved backups may continue to mention old terms when they are
clearly archival. They cannot be used as current runtime, prompt, model, test,
install, or completion evidence. Active checks must not count those mentions as
positive current coverage.

## Active Follow-Up Targets

| Target area | Required cleanup |
| --- | --- |
| Core new runtime | Done for startup import, role assignment, lease commit, and result mechanical blocking. |
| Startup UI and preview | Keep visible acknowledgement control; off state writes `blocked`; preview copy must match. |
| Router startup/resume/recovery | Keep `background_collaboration_authorized=true` hard gates; remove old fixed-role and heartbeat positive assertions. |
| Startup/PM review/meta/capability models | Replace optional role-assistance and single-agent paths with mandatory background capability or structured stop. |
| Fake-AI and synthetic packages | Add disabled/missing acknowledgement, old-field rejection, corrected-package acceptance, and protected-state non-advancement cases. |
| Active docs/specs/prompts/cards | Remove current positive heartbeat, fixed six-role, and single-agent fallback language. |
| Templates/install surfaces | Remove heartbeat and old startup option templates from current install payloads or move them to explicit historical quarantine. |
