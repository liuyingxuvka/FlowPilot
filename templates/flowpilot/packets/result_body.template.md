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
forbidden_scope: I did not approve gates unless my role is the approver; do not act as another role, bypass Controller, hide unresolved issues, or relabel this result.
required_return: Return the role-appropriate review, PM decision, officer response, blocker, or reissue/repair request through the current FlowPilot packet path.
---

# Result Body

This file contains the detailed result for the packet. The controller must not
read, summarize, repair, execute, or complete this result body. The controller
only relays the result envelope to the next recipient.

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

## Evidence

- <evidence-path-screenshot-log-model-result-or-output>

## Findings

- <finding-or-observation>

## Open Issues

- <issue-or-none>

## Requested Next Recipient

<human_like_reviewer|project_manager|process_flowguard_officer|product_flowguard_officer>
