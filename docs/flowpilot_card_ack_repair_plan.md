# FlowPilot Card ACK Repair Plan

## Risk Intent Brief

This change repairs the system-card check-in path. The protected harm is a
FlowPilot run getting stuck before startup because a role hand-writes an ACK or
Controller routes a card ACK as a normal external event.

The model must make these states visible:

- a system-card delivery has a real committed envelope;
- the receiving role gets an explicit check-in instruction;
- the role opens the card through the runtime check-in tool;
- the runtime writes the read receipt and ACK;
- Controller never treats a card ACK as ordinary project output;
- Router can safely recover if Controller sends a card ACK to the external
  event entrypoint;
- Router still rejects hand-written or stale ACK files.

Residual blindspots: the model checks the control-plane flow and file shape. It
does not prove the role semantically understood the card body; reviewer or PM
judgement gates still own semantic review.

## Implementation Plan

| Step | Change | Why | Acceptance check |
| --- | --- | --- | --- |
| 1 | Add one short check-in instruction block to every system-card envelope that requires ACK. | The role should see the "打卡" instruction inside the work package, not infer it from memory. | Delivered card envelope exposes the runtime command and says not to hand-write ACK. |
| 2 | Keep the runtime check-in tool as the official path and make it one-step. | Add `receive-card` / `receive-card-bundle`, which opens the card, writes the read receipt, and writes the ACK. Keep `open-card` / `ack-card` for lower-level compatibility. | Tests prove the one-step command creates an ACK accepted by Router. |
| 3 | Tighten Controller core wording for card ACKs. | Controller currently has a broad "role/event envelope -> record-event" instruction that can mislead it. | Controller card explicitly says card ACKs are not normal events and must return to Router for ACK checking. |
| 4 | Upgrade Router's external-event entrypoint for card ACK mistakes. | If Controller still sends a card ACK to record-event, Router should guide or consume it through ACK validation, not dead-end. | `record_external_event(..., "reviewer_card_ack")` with a valid runtime ACK resolves the pending card return. |
| 5 | Keep validation strict. | The fix must not accept hand-written or stale ACK files. | Tests show malformed ACK, wrong role, wrong agent, or missing receipt still fail. |
| 6 | Sync repo source to the installed local FlowPilot skill and make a local git commit only. | The user asked for local install, local repo, and local git synchronization, not GitHub push. | Installer check reports the installed skill is fresh; local commit exists; no remote push. |

## Bug Risks To Catch Before Editing

| Risk | What could go wrong | FlowGuard must catch |
| --- | --- | --- |
| 1 | Controller sends card ACK through normal external-event recording again. | ACK cannot be recorded as ordinary event; valid ACK must be routed to card-return validation. |
| 2 | Router "fix" becomes too permissive and accepts a hand-written ACK. | ACK is accepted only with runtime read receipt references, matching run, role, agent, envelope, and hashes. |
| 3 | Work package still hides the check-in command. | A committed system-card envelope that requires ACK must include check-in instructions. |
| 4 | Role opens the card but does not send the ACK. | Router must stay in pending-return state with a recovery reminder, not advance. |
| 5 | ACK from old run, wrong role, wrong agent, or wrong card is accepted. | Validation rejects mismatched run/role/agent/card/hash. |
| 6 | Controller reads card body while trying to help. | Controller remains envelope-only; card body access remains forbidden. |
| 7 | Bundle cards regress while fixing single-card ACK. | Bundle ACK path keeps per-card receipt join and incomplete-ACK recovery. |
| 8 | Local installed skill is stale after the repository fix. | Install/audit check must confirm installed FlowPilot source is fresh. |
