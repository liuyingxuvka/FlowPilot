# FlowPilot ACK-After-Receipt Optimization Plan

Date: 2026-05-13

## Risk Intent

This change protects FlowPilot's prompt-isolated card and packet runtime from
confusing a mechanical receipt ACK with the actual semantic work output. The
model must catch cases where a role opens a card or packet, submits ACK, and
then stops even though the card or packet was the authority to begin work. It
must also catch the opposite error: a role card ACK causing task work to begin
without a phase card, event card, packet, or Router-authorized role-output
contract.

The optimization is intentionally minimal. It should clarify the post-ACK
rule at the check-in instruction, system-card identity boundary, packet body
template, and packet identity boundary without changing Router event names,
role authority, packet sealing, or remote GitHub state.

## Card And Packet Taxonomy

| Type | Examples | Current problem to guard | Minimal intended rule |
| --- | --- | --- | --- |
| Role cards / identity cards | `controller.core`, `pm.core`, `reviewer.core`, `worker_a.core`, `worker_b.core`, `process_officer.core`, `product_officer.core` | ACK may be misunderstood as permission to start task work from the role card alone. | ACK means "I received my role rules." After ACK, absorb the role rules and wait for a phase card, event card, work packet, active-holder lease, or Router-authorized output contract before task work. |
| Phase, duty, resume, reviewer-gate, officer-gate, and startup-gate system cards | `pm.product_architecture`, `pm.current_node_loop`, `reviewer.worker_result_review`, `product_officer.product_architecture_modelability`, `controller.resume_reentry` | The short check-in prompt tells the role to ACK, but may not remind it that ACK is not completion and the card work should continue. | ACK means receipt only. After ACK, continue the work assigned by that card and submit the formal output or blocker through the card's Router-directed runtime path. |
| Event cards | `pm.event.reviewer_report`, `pm.event.reviewer_blocked`, `pm.event.node_started` | ACK may be treated as the event disposition, or the PM may invent the next event from the card wording. | ACK means event-card receipt only. After ACK, process the event through the paired PM card path or an explicitly Router-authorized output event. If no authorized next event exists, return a protocol blocker. |
| Work packets / result packets | `templates/flowpilot/packets/packet_body.template.md`, `result_body.template.md`, runtime-generated packet bodies | Active-holder ACK may look like the whole task, especially when Controller is visibly waiting. | Packet ACK means "I hold the packet." After ACK, execute the packet body, write the sealed result body/envelope, and submit completion to Router through the active-holder lease when present. |
| Same-role card bundles | A role receives several cards together and runs `receive-card-bundle` | Bundle ACK may be treated as one combined role output or may hide member-specific work. | Bundle ACK signs only for receipt of all members. After ACK, apply each member's rule separately: role cards update identity only, task cards execute work, event cards process Router-authorized event handling. |

## Optimization Order

| Step | Optimization item | Files likely touched | Model gate before/after |
| --- | --- | --- | --- |
| 1 | Extend the card/packet instruction coverage model with explicit post-ACK facts by card type and packet prompt surface. | `simulations/card_instruction_coverage_model.py`, `simulations/run_card_instruction_coverage_checks.py`, tests | Known-bad hazard cards/packet prompts must be rejected before production prompt edits are trusted. |
| 2 | Add a CLI output option so the strengthened model can be run without overwriting another agent's existing result file. | `simulations/run_card_instruction_coverage_checks.py` | Targeted run writes to a temp result path first. |
| 3 | Strengthen Router's short card check-in instruction so the most visible instruction says ACK is receipt only and points to the card body's post-ACK rule. | `skills/flowpilot/assets/flowpilot_router.py` | Model must confirm Router source contains the generic post-ACK check-in guard. |
| 4 | Strengthen runtime card identity text by card type. | `skills/flowpilot/assets/runtime_kit/cards/**/*.md` | Model must confirm role cards, task cards, and event cards each carry the correct post-ACK rule. |
| 5 | Strengthen packet body/template and runtime packet identity text. | `templates/flowpilot/packets/packet_body.template.md`, `skills/flowpilot/assets/packet_runtime.py` | Model must confirm packet ACK is receipt-only and execution/result submission remains required. |
| 6 | Run targeted model/tests, then install/audit local skill sync. | targeted simulation, unittest, install/audit scripts | Do not update remote GitHub. Do not stage unrelated existing files. |

## Bug Classes The Model Must Catch

| Bug id | Possible regression | Required model capture |
| --- | --- | --- |
| B1 | A role card says or implies "ACK, then begin task work" without a phase/event/packet authority. | Role-card hazard with missing role-card wait rule is rejected. |
| B2 | A task, reviewer-gate, officer-gate, resume, duty, or startup card tells the role to ACK but lacks "ACK is not completion; continue assigned work." | Task-card hazard with missing post-ACK work rule is rejected. |
| B3 | An event card lets ACK stand in for event disposition or omits Router-authorized event handling. | Event-card hazard with missing event post-ACK rule is rejected. |
| B4 | A same-role card bundle implies the bundle ACK is a combined role output. | Existing bundle command refinement coverage remains green; Router check-in text must explicitly name per-member post-ACK rules. |
| B5 | A packet body or packet runtime identity tells the role to ACK the lease but does not require executing the packet and returning a sealed result. | Packet prompt hazard with missing post-ACK packet execution/result rule is rejected. |
| B6 | Prompt wording sends ACK or packet completion to Controller instead of Router. | Existing stale Controller ACK hazards remain rejected. |
| B7 | Prompt wording tells an officer/worker to invent or reuse a non-authorized event after ACK. | Card text must keep Router wait authority and PM packet/output-contract boundaries; existing event-contract and prompt-coverage checks remain relevant. |
| B8 | Strengthened wording exposes sealed body contents or formal findings in chat/status updates. | Existing envelope-only and chat body suppression checks remain required for every card and packet prompt. |

## Success Criteria

1. The upgraded model rejects all listed post-ACK hazard cases.
2. The actual runtime card and packet prompt surfaces pass the upgraded model.
3. Existing event-contract coverage still catches direct ACK replacing semantic
   waits.
4. Targeted unit tests pass.
5. Local install sync succeeds and audit confirms the installed skill matches
   the local repository copy.
6. Local git records only this task's intentional files; pre-existing unrelated
   changes stay unmodified and unstaged.
