# Packet-Gated Control Plane

This reference captures the experimental FlowPilot control-plane revision for
preventing controller/worker over-execution.

## Roles

- Controller: main assistant. Relays packets, records live status, waits for
  role decisions, and keeps the loop moving. It is not the implementation
  worker.
- PM: owns global route, frozen acceptance floor, node packet creation, repair,
  route mutation, and completion decisions.
- Reviewer: owns dispatch approval and result review. Reviewer `block` is a
  hard stop for PM advancement.
- Workers: execute only the current packet body addressed to their role and
  return a result envelope/body pair.
- Simulators/officers: stress-test process and product models; they do not
  close implementation or review gates unless explicitly assigned as approver
  for that gate.

## Loop

```text
Controller bootstraps only user-approved startup options
-> Controller writes USER_INTAKE envelope/body and relays envelope to PM
-> PM asks Reviewer for startup-readiness review through Controller
-> PM issues PACKET_ENVELOPE + PACKET_BODY after startup gate opens
-> Controller signs relay and sends only the envelope to the target role
-> Recipient verifies controller relay signature before opening the body
-> Worker reads and executes exactly its packet body
-> Worker returns RESULT_ENVELOPE + RESULT_BODY and waits
-> Controller signs relay and sends only the result envelope to Reviewer
-> Reviewer audits mail chain, role origin, hashes, and evidence
-> Controller relays review envelope to PM
-> PM issues next packet, repair packet, route mutation, user block, or complete
-> Controller continues internally unless PM says stop_for_user: true
```

## Evidence Rule

Only evidence from the role authorized for the current packet can close that
packet's gate. Controller-origin implementation, review, PM approval, route
completion, screenshot, generated data, or dependency-install evidence is
invalid unless the PM packet explicitly assigned that administrative action to
the controller and the reviewer approved dispatch.

Packets and results use an envelope/body split. The controller may read only
`packet_envelope` and `result_envelope`, update holder/status, relay envelopes,
display required Mermaid route signs, wait for role returns, and ask PM for the
next decision. The controller must not read or execute `packet_body` or
`result_body`, generate worker artifacts, run product validation, approve
gates, close nodes, rewrite hashes, or relabel wrong-role completion.

All formal mail goes through Controller. PM, reviewer, worker, and officer
roles must not privately pass packet/result bodies or formal review/decision
mail. Each Controller relay writes `controller_relay` on the envelope with
`delivered_via_controller: true`, `controller_agent_id`, `received_from_role`,
`relayed_to_role`, holder before/after, `envelope_hash`,
`body_was_read_by_controller: false`, and `body_was_executed_by_controller:
false`. The recipient verifies this signature before opening any body. Missing
signatures, wrong recipients, hash mismatch, private delivery, or missing
no-read/no-execute declarations block body open and force sender reissue via PM.

If Controller discovers it has opened or executed a sealed internal body, it
must not continue relaying that mail. It records a contaminated
return-to-sender entry and asks PM to obtain a fresh sender-issued replacement.
The old packet cannot become valid by post-hoc signing, relabeling, cosigning,
or hash rewriting.

The split must be physical in real runs. Use
`skills/flowpilot/assets/packet_runtime.py` in the installed skill or
`scripts/flowpilot_packets.py` in this repository to write
`.flowpilot/runs/<run-id>/packets/<packet-id>/packet_envelope.json`,
`packet_body.md`, `result_envelope.json`, and `result_body.md`. The runtime
computes hashes from those files and builds controller handoffs from envelope
fields only. Missing physical files or body text in controller context blocks
dispatch before review content inspection.

The reviewer checks role origin and body integrity on every packet, not only
when a mismatch is obvious. The audit compares the PM packet envelope,
reviewer dispatch, `packet_envelope.to_role`, packet body hash, assigned
worker or authorized role, result envelope, `completed_by_role`,
`completed_by_agent_id`, result body hash, and actual result author. A pass is
allowed only when the actual result author matches the assigned role, the
agent id belongs to that role, and the referenced bodies match their hashes and
are not stale after route mutation. If the result came from Controller, from
an unknown actor, or from a different role, the reviewer must block, issue the
controller-boundary warning, and require PM to reissue or repair the packet
through the assigned role. Wrong-role completion cannot be cosigned,
relabelled, or accepted as "good enough."

At every subnode and every major-node closure, reviewer also audits the full
mail chain for that node: controller relay signatures, recipient pre-open
checks, holder continuity, no private mail, and replacement coverage for
contaminated, rejected, missing, or unopened mail. If any required letter was
not opened when needed, reviewer sends the chain audit to PM. PM chooses
`restart_node`, `create_repair_node`, or `request_sender_reissue`.

Reviewer decisions for role-origin mismatch:

```text
REVIEW_DECISION:
  decision: block_invalid_role_origin
  can_pm_advance: false
  blocking_issues:
    - Artifact was produced by Controller instead of authorized worker/role.
```

PM responses:

- discard invalid evidence;
- issue a repair packet to an authorized worker;
- quarantine or restart if contamination affects route trust;
- never advance using invalid role-origin evidence.
- include `controller_reminder` in every PM response to the controller:
  `Controller: relay and coordinate only. Do not implement, install, edit,
  test, approve, or advance from your own evidence.`
- require every sub-agent response to repeat a controller-boundary reminder
  and its own role boundary.
- require the controller to include a `ROLE_REMINDER` whenever it sends a
  packet or review request to PM, reviewer, worker, simulator/officer, or
  verifier.

## Packet Schema

```text
PACKET_ENVELOPE:
  packet_id:
  packet_type:
  from_role:
  to_role:
  node_id:
  is_current_node:
  body_path:
  body_hash:
  body_visibility:
  controller_relay:
  replacement_for:
  supersedes:
  return_to:
  next_holder:
  controller_allowed_actions:
  controller_forbidden_actions:
```

```text
PACKET_BODY:
  objective:
  inputs:
  allowed_read_paths:
  allowed_write_paths:
  allowed_commands_or_side_effects:
  forbidden_actions:
  acceptance_slice:
  verification_required:
```

```text
RESULT_ENVELOPE:
  packet_id:
  packet_type:
  completed_by_role:
  completed_by_agent_id:
  node_id:
  result_body_path:
  result_body_hash:
  controller_relay:
  next_recipient:
```

```text
RESULT_BODY:
  status: completed | blocked | needs_pm
  changed_files:
  commands_run:
  evidence:
  author_evidence:
  open_issues:
```

```text
REVIEW_DECISION:
  packet_id:
  decision: pass | block | needs_repair | needs_user | block_invalid_role_origin
  can_pm_advance: true | false
  role_origin_audit:
    packet_controller_relay_signature_checked:
    result_controller_relay_signature_checked:
    controller_signed_body_unread_and_unexecuted:
    recipient_pre_open_relay_check_verified:
    private_role_to_role_delivery_absent:
    contaminated_or_rejected_packets_have_sender_replacements:
    unopened_or_missing_mail_sent_to_pm:
    pm_packet_author_verified:
    reviewer_dispatch_authority_checked:
    packet_envelope_to_role_checked:
    packet_body_hash_checked:
    result_envelope_completed_by_role_checked:
    result_envelope_completed_by_agent_id_checked:
    result_body_hash_checked:
    expected_executor_role:
    actual_result_author_role:
    completed_by_agent_id:
    completed_agent_id_belongs_to_role:
    author_matches_assignment:
    body_hash_mismatch_detected:
    stale_body_reuse_detected:
    wrong_role_cosign_or_relabel_forbidden:
    controller_boundary_warning_issued:
    rework_required_by_assigned_role:
  blocking_issues:
```

```text
PM_DECISION:
  decision: issue_next_packet | repair_current | mutate_route | block_user | complete
  next_packet:
  stop_for_user: true | false
  controller_reminder:
```

If `controller_reminder` is missing, the controller must not dispatch work and
must request a corrected PM decision.

Every controller-to-sub-agent message must include:

```text
ROLE_REMINDER:
  controller_boundary:
  recipient_role:
  recipient_allowed_actions:
  recipient_forbidden_actions:
  return_to_controller_only: true
```

Every sub-agent-to-controller response must include:

```text
ROLE_ECHO:
  controller_boundary_confirmed: true
  own_role:
  own_allowed_actions:
  own_forbidden_actions:
  result_returns_to_controller_only: true
```

Missing reminders are dispatch/review blockers, not cosmetic formatting gaps.

## Heartbeat And Manual Resume

Heartbeat and manual resume use the same packet control plane. The waking
assistant is Controller only. It first resolves `.flowpilot/current.json`,
loads the active run state/frontier/route, crew ledger, role memory, latest
heartbeat or manual-resume evidence, `packet_ledger.json`, and controller
relay history, then restores or replaces the six roles before asking PM for the
current decision. It must not open `packet_body.md` or `result_body.md`.

The heartbeat prompt is a stable launcher. It must not carry route-specific
next-step instructions and must not be rewritten just because the route or PM
runway changed. Current work comes from persisted state and PM decisions.

Resume rules:

- If no current packet exists, ask PM for `PM_DECISION`.
- Before normal continuation, audit the packet ledger for missing relay
  signatures, private role-to-role mail, controller contamination, unopened
  bodies, holder-chain breaks, and invalid stale/replacement chains. If any are
  present, ask PM for restart, repair node, or sender reissue instead of
  continuing.
- If PM issues or reissues `PACKET_ENVELOPE` and `PACKET_BODY`, require
  `controller_reminder`, sign the controller relay, then send only the envelope
  to the target role or reviewer dispatch path before any worker sees the body.
- If the packet is already with a worker, resume that exact packet only when
  controller relay signature, recipient body-open record, reviewer dispatch,
  and worker identity are clear.
- If a worker result envelope exists, send the `RESULT_ENVELOPE` to reviewer.
  Reviewer and PM may read the result body from their authorized review or
  decision position. Reviewer pass goes to PM; reviewer block goes to PM for
  repair, mutation, user block, or stop.
- If holder, worker identity, reviewer dispatch, or worker-result state is
  ambiguous, block and ask PM for recovery/reissue/reassignment. Controller
  must not infer missing worker work or finish the packet.
- If PM says `stop_for_user: false`, the controller continues the internal
  loop. A worker stopping after `RESULT_ENVELOPE` does not stop the route by
  itself.

## Live Status

The controller should report packet location and next expected event:

```text
Flow Status:
  run_id:
  active_node:
  packet_id:
  holder: PM | Reviewer | WorkerA | WorkerB | Controller | User
  pm_authorization:
  reviewer_dispatch:
  worker_status:
  reviewer_result:
  next_expected_event:
  controller_allowed_action:
```
