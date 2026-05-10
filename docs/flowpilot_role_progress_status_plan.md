# FlowPilot Role Progress Status Plan

## Optimization Checklist

| Step | Change | Files | Done When |
| --- | --- | --- | --- |
| 1 | Reuse the existing packet `controller_status_packet.json` as the Controller-visible progress surface. | `skills/flowpilot/assets/packet_runtime.py` | The status payload can carry optional numeric `progress` without adding a new heartbeat file. |
| 2 | Add a packet-runtime `progress` command so roles update status through the runtime instead of hand-editing JSON. | `skills/flowpilot/assets/packet_runtime.py` | The command updates only `status`, `progress`, `message`, `updated_at`, holder, and runtime-visible metadata. |
| 3 | Add a packet-body reminder so PM-authored task packets tell target roles to update progress after meaningful work chunks. | `skills/flowpilot/assets/packet_runtime.py` | Every new packet identity boundary includes the progress reminder. |
| 4 | Let Controller read only the matching packet `controller_status_packet.json` while waiting for long-running role-work results. | `skills/flowpilot/assets/flowpilot_router.py` | The pending `await_role_decision` action for `role_work_result_returned` includes that single status file in `allowed_reads`. |
| 5 | Extend FlowGuard control-plane friction checks before production edits are trusted. | `simulations/flowpilot_control_plane_friction_model.py`, `simulations/run_flowpilot_control_plane_friction_checks.py` | The model catches missing progress visibility and status-body leakage hazards, and the safe plan passes. |

## Risk Checklist

| Risk | Why It Matters | FlowGuard Coverage |
| --- | --- | --- |
| Controller waits for a long-running role with no readable progress status. | A normal wait timeout can look like a dead role and encourage unnecessary replacement. | Invariant: long-running role-work waits expose the matching status packet in `allowed_reads`. |
| Status message leaks sealed packet/result content. | The status file becomes Controller-readable, so it must stay metadata-only. | Invariant: Controller-visible progress status does not contain findings, evidence, recommendations, or body summaries. |
| Progress updates are written by ad hoc JSON edits. | Manual writes can bypass role identity and sealed-body constraints. | Invariant: working progress updates are runtime-written. |
| Progress regresses or uses nonnumeric/free-form values. | Controller can no longer compare progress movement reliably. | Invariant: progress is numeric and nonnegative when present. |
| Safe plan accidentally broadens Controller reads to the packet directory. | Directory-level reads could expose `packet_body.md` or `result_body.md`. | Invariant: status visibility grants only `controller_status_packet.json`, not the full packet directory or sealed body paths. |

## Minimal Safety Boundary

- `progress` is optional, numeric, and monotonic by convention.
- `message` is a brief status label such as `opened packet`, `running checks`, `building result envelope`, or `validating result`.
- `message` must not include sealed body content, findings, evidence, recommendations, result details, or body summaries.
- Controller may read the status packet only when the router explicitly lists that exact file in `allowed_reads`.
