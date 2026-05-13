---
schema_version: flowpilot.result_body.v1
packet_id: <packet-id>
run_id: <run-id>
route_id: <route-id>
node_id: <node-id>
completed_by_role: <same-as-result-envelope-completed_by_role>
completed_by_agent_id: <agent-id-or-single-agent-role-continuity-id>
result_body_hash_algorithm: sha256
controller_may_read: false
recipient_must_verify_controller_relay_before_opening: true
---

---
FLOWPILOT_RESULT_IDENTITY_BOUNDARY_V1: true
completed_by_role: <completed_by_role>
recipient_role: <same-as-result-envelope-next_recipient>
recipient_identity: I completed this as `<completed_by_role>` for this packet result only; the next recipient must read it only as the result envelope recipient.
allowed_scope: Read and review only this result body, its result envelope, and the source packet evidence after verifying Controller relay and completed_by_role identity.
forbidden_scope: I did not approve gates unless my role is the approver; do not act as another role, bypass Router, hide unresolved issues, or relabel this result.
required_return: If this is the current active-holder packet result, submit completion directly to Router through the active-holder lease. Later review, PM decision, officer response, blocker, or reissue/repair mail follows the Router-directed FlowPilot packet path.
---

# Result Body

This file contains the detailed result for the packet. The controller must not
read, summarize, repair, execute, or complete this result body. The controller
only relays the result envelope to the next recipient after Router tells it to.
Current active-holder packet completion is submitted to Router first, not to
Controller.

Before reading this file, reviewer, PM, or officer must verify that
`result_envelope.json#controller_relay` was delivered by Controller, targets the
reader role, matches the result envelope hash, and declares that Controller did
not read or execute this body. If the check fails, do not read this body; return
the unopened envelope for PM reissue or repair.

## Status

<completed|blocked|needs_pm>

## Commands Or Probes Run

- <command-or-probe>

## Files Or Artifacts Changed

- <path-and-summary>

## Artifact Handoff

- artifact_refs: <formal-output-or-evidence-paths-and-hashes-or-none>
- changed_paths: <created-or-edited-paths-or-none>
- output_contract_id: <packet-envelope-output_contract.contract_id>
- inspection_notes: <what-PM-reviewer-or-officer-should-inspect-directly>
- pm_suggestion_items: <candidate-items-or-empty-list>
- consultation_note: <bounded-advice-only-or-not-applicable>

## Evidence

- <evidence-path-screenshot-log-model-result-or-output>

## Proof of Depth

When the source packet includes a `Low-Quality Success Guard`, explain how the
work proved the named hard part instead of only producing existence-only
evidence. Use `not applicable` only when the source packet explicitly says the
guard classification is `none`.

- hard_part_addressed: <hard-part-or-not-applicable>
- thin_success_shortcut_avoided: <what-was-not-done-casually-or-not-applicable>
- depth_evidence_refs: <paths-commands-screenshots-direct-review-or-not-applicable>
- why_existence_only_evidence_is_not_the_claim: <brief-explanation-or-not-applicable>

## Findings

- <finding-or-observation>

## Open Issues

- <issue-or-none>

## PM Note

For worker or FlowGuard officer packet results, include a short PM-facing note.
This note is decision-support, not gate approval and not permission to expand
scope. For other result types, write `not applicable`.

- In-scope quality choice: <simpler-or-higher-quality-choice-used-inside-this-packet-boundary-or-none>
- PM consideration: <out-of-scope-better-idea-route-risk-or-simplification-opportunity-for-PM-or-none>

## PM Suggestion Items

Use `none` when there are no PM suggestion candidates. Otherwise list candidate
`flowpilot.pm_suggestion_item.v1` entries for PM disposition in
`pm_suggestion_ledger.jsonl`. Include source role, source output reference,
summary, classification, authority basis, and evidence references. Do not copy
sealed body content into the suggestion item. Worker-origin items are advisory
only and must not use `current_gate_blocker`. FlowGuard officer items may use
`current_gate_blocker` only for formal model-gate findings inside the
PM-requested model boundary.

## Skill Standard Result Matrix

For every inherited child-skill standard id declared in the source packet,
include one row. Use `none` only when the source packet's `Inherited Skill
Standards` section says no child-skill standards apply.

| standard_id | status | evidence_path | waiver_reason | note |
| --- | --- | --- | --- | --- |
| <standard-id-or-none> | <done|not_applicable|waived|blocked> | <path-or-null> | <reason-or-null> | <short-note> |

## Child Skill Use Evidence

For every active child-skill binding declared in the source packet, include one
row proving that the source skill or required reference was opened and the
current-node slice was applied. If an applicable child-skill standard was
stricter than the PM packet, record that the stricter standard was followed or
cite the explicit PM waiver. Use `none` only when the source packet's `Active
Child Skill Bindings` section says no active child-skill bindings apply.

| binding_id | source_skill_path_opened | referenced_paths_opened | node_slice_scope_used | stricter_standard_applied_or_waived | evidence_path | note |
| --- | --- | --- | --- | --- | --- | --- |
| <binding-id-or-none> | <path-or-none> | <paths-or-none> | <scope-or-none> | <applied|waived|not_applicable> | <path-or-null> | <short-note> |

## Contract Self-Check

- source_output_contract_id: <packet-envelope-output_contract.contract_id>
- required_sections_present: <true|false>
- evidence_matches_contract: <true|false>
- unmet_contract_items: <items-or-none>
- self_check_decision: <satisfied|blocked|needs_pm>

## Requested Next Recipient

<human_like_reviewer|project_manager|process_flowguard_officer|product_flowguard_officer>
