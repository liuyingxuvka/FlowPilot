# FlowGuard Pre-Implementation Gate

## Risk Intent Brief

FlowGuard is used here to protect FlowPilot role authority while adding stronger
quality pressure to work packets. The change must prevent two opposite failure
modes:

- workers return "complete" without fixing defects that are inside their packet
  scope and evidence obligations;
- reviewers, officers, PM, Controller, or generic prompts receive blanket
  "fix bugs directly" wording that turns review, modeling, routing, or relay
  roles into silent executors.

Modeled side effects are prompt obligations, packet completion eligibility,
blocker/needs-PM exits, PM Suggestion Items, and reviewer/officer report
boundaries. The model is a process-contract check; runtime tests and prompt text
tests remain required after the model passes.

## Change Inventory

- Add executable worker in-scope repair guidance to current-node and repair
  packet authoring prompts.
- Add worker role reminders that completion requires self-check, in-scope
  defect repair, and re-verification before result return.
- Add evidence/report self-correction guidance to material-scan, research, and
  officer report/model prompts.
- Add explicit reviewer anti-repair guidance to reviewer role/review prompts.
- Add generic packet-template role-scoping so one template can reach workers,
  officers, reviewers, and PM without granting blanket repair authority.
- Add tests for required phrases and forbidden role drift.

## Risk Catalog And Coverage Matrix

| Planned change | Possible bug | Modeled state/events | Invariant or oracle | Known-bad hazard | Production-facing check |
|---|---|---|---|---|---|
| Worker in-scope repair prompt | Worker completes without fixing packet-scoped defect | `worker_packet_carries_in_scope_quality_repair` | `quality_repair_prompts_preserve_role_authority` | `worker_packet_missing_in_scope_repair` | card text tests and planning-quality check |
| Worker escalation boundary | Worker silently changes scope, acceptance, or other role work | `worker_packet_escalates_out_of_scope_defects` | same invariant | `worker_packet_repairs_out_of_scope` | worker/card text tests |
| Research/material evidence boundary | Research packet edits target artifact instead of reporting finding | `evidence_packet_self_corrects_only_own_output` | same invariant | `evidence_packet_repairs_target_artifact` | material/research prompt tests |
| Officer model boundary | Officer repairs implementation/route instead of reporting PM finding | `officer_packet_self_corrects_model_only` | same invariant | `officer_packet_repairs_target_artifact` | officer prompt tests |
| Reviewer anti-repair | Reviewer becomes worker and repairs reviewed artifact | `reviewer_prompt_forbids_direct_artifact_repair` | same invariant | `reviewer_prompt_grants_direct_repair` | reviewer prompt tests |
| Generic template role scope | Shared template injects direct-fix wording into all roles | `generic_packet_template_role_scoped` | same invariant | `generic_template_uses_blanket_repair` | generic packet template tests |

## Check Command

```powershell
python simulations/run_flowpilot_planning_quality_checks.py --json-out simulations/flowpilot_planning_quality_results.json
```
