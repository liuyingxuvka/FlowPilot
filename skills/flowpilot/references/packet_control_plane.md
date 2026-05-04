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
- Workers: execute only the current `NODE_PACKET` and return `NODE_RESULT`.
- Simulators/officers: stress-test process and product models; they do not
  close implementation or review gates unless explicitly assigned as approver
  for that gate.

## Loop

```text
PM issues NODE_PACKET
-> Reviewer approves or blocks dispatch
-> Controller relays approved packet to worker
-> Worker executes exactly the packet
-> Worker returns NODE_RESULT and waits
-> Controller relays result to Reviewer
-> Reviewer passes, blocks, or requests repair
-> Controller relays review to PM
-> PM issues next packet, repair packet, route mutation, user block, or complete
-> Controller continues internally unless PM says stop_for_user: true
```

## Evidence Rule

Only evidence from the role authorized for the current packet can close that
packet's gate. Controller-origin implementation, review, PM approval, route
completion, screenshot, generated data, or dependency-install evidence is
invalid unless the PM packet explicitly assigned that administrative action to
the controller and the reviewer approved dispatch.

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
NODE_PACKET:
  packet_id:
  node_id:
  objective:
  inputs:
  allowed_read_paths:
  allowed_write_paths:
  allowed_commands_or_side_effects:
  forbidden_actions:
  acceptance_slice:
  verification_required:
  return_format:
  stop_after_result: true
```

```text
NODE_RESULT:
  packet_id:
  node_id:
  status: completed | blocked | needs_pm
  changed_files:
  commands_run:
  evidence:
  open_issues:
  request_next_packet: true
```

```text
REVIEW_DECISION:
  packet_id:
  decision: pass | block | needs_repair | needs_user | block_invalid_role_origin
  can_pm_advance: true | false
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
heartbeat or manual-resume evidence, and `packet_ledger.json`, then restores
or replaces the six roles before asking PM for the current decision.

The heartbeat prompt is a stable launcher. It must not carry route-specific
next-step instructions and must not be rewritten just because the route or PM
runway changed. Current work comes from persisted state and PM decisions.

Resume rules:

- If no current packet exists, ask PM for `PM_DECISION`.
- If PM issues or reissues `NODE_PACKET`, require `controller_reminder`, then
  send it to the reviewer for dispatch approval before any worker sees it.
- If the packet is already with a worker, resume that exact packet only when
  reviewer dispatch and worker identity are clear.
- If a worker result exists, send `NODE_RESULT` to reviewer. Reviewer pass goes
  to PM; reviewer block goes to PM for repair, mutation, user block, or stop.
- If holder, worker identity, reviewer dispatch, or worker-result state is
  ambiguous, block and ask PM for recovery/reissue/reassignment. Controller
  must not infer missing worker work or finish the packet.
- If PM says `stop_for_user: false`, the controller continues the internal
  loop. A worker stopping after `NODE_RESULT` does not stop the route by
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
