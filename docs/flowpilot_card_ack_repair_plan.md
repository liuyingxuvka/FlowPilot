# FlowPilot Direct Router ACK Plan

## Current Direction

This older card-ACK repair note is superseded by the direct-Router ACK
migration. The protected harm is still the same: a FlowPilot run must not get
stuck or advance incorrectly because a role hand-writes an ACK, sends an ACK to
Controller, or lets Controller record an ACK as an ordinary external event.

The current rule is stricter:

- system-card ACKs go directly from the addressed role to Router through the
  card check-in command;
- active-holder packet ACKs and packet completion reports go directly from the
  current holder to Router through the lease;
- Controller waits for Router action envelopes or
  `controller_next_action_notice.json`;
- Controller does not receive, write, relay, recover, or record ACKs;
- the legacy `record-event *_card_ack` path is rejected, not rerouted.

## Implementation Plan

| Step | Change | Why | Acceptance check |
| --- | --- | --- | --- |
| 1 | Add a direct-Router ACK token to every committed system-card and bundle envelope. | Router must know which current card holder may check in. | ACK validation rejects tokenless, stale, wrong-role, wrong-agent, and wrong-card ACKs. |
| 2 | Make the card runtime write ACKs as `direct_to_router` receipts only. | ACKs are mechanical check-ins, not Controller mail. | Runtime ACKs include direct token/hash and `controller_ack_handoff_used: false`. |
| 3 | Reject legacy `record-event *_card_ack` submissions. | Compatibility with the old path keeps the system ambiguous. | Router returns a control-plane failure instead of accepting or rerouting the ACK. |
| 4 | Update all role/system card prompts and packet templates. | Roles must see the new rule in the work they receive, not infer it from memory. | Prompt coverage model fails on stale Controller ACK wording and missing direct-Router ACK wording. |
| 5 | Preserve Controller visibility without making Controller the return receiver. | Reports, decisions, and review envelopes need Router-recorded coordination, not Controller handoff. | Packet/result docs distinguish direct Router submission from later Router-authorized Controller relay. |
| 6 | Sync repo source to the installed local FlowPilot skill and make a local git commit only. | The user asked for local install, local repo, and local git synchronization, not GitHub push. | Installer check reports the installed skill is fresh; local commit exists; no remote push. |

## Bug Risks To Catch Before Editing

| Risk | What could go wrong | FlowGuard must catch |
| --- | --- | --- |
| 1 | Controller receives, submits, or records a system-card ACK. | Legacy `record-event *_card_ack` path is rejected and prompts forbid Controller ACK handling. |
| 2 | A role card still teaches the old ACK path. | Prompt coverage fails on stale ACK-to-Controller phrases. |
| 3 | A work packet omits the new active-holder ACK/result fast-lane instruction. | Packet prompt coverage fails when direct Router ACK/result terms are missing. |
| 4 | Router accepts a hand-written or tokenless ACK. | Runtime validation requires the direct Router token, receipt paths, role, agent, card, envelope, and hashes. |
| 5 | ACK from old run, wrong role, wrong agent, or wrong card is accepted. | Validation rejects mismatched run/role/agent/card/hash. |
| 6 | Controller infers packet completion from worker chat. | Controller card and packet docs require waiting for Router's next-action notice. |
| 7 | Bundle cards regress while fixing single-card ACK. | Bundle ACK validation keeps per-card receipt join and incomplete-ACK recovery. |
| 8 | Local installed skill is stale after the repository fix. | Install/audit check confirms installed FlowPilot source is fresh. |
