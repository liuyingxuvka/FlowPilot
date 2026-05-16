## Overview

Introduce a single Router-owned dispatch recipient gate. The gate runs before
Router exposes a Controller row for role-facing delivery actions:

- `deliver_mail`
- `deliver_system_card`
- `deliver_system_card_bundle`
- formal work-packet relay actions such as material scan, research,
  current-node, and PM role-work packets

The gate does not replace packet validation, active-holder validation, PM
decision authority, reviewer gates, or result quality checks. It decides only
whether a new role-facing delivery may be exposed now.

## Existing Checks To Preserve

- System-card ACK clearance before formal work packets.
- Same-batch duplicate target-role rejection.
- Packet envelope, hash, output-contract, path, and sealed-body validation.
- Controller relay boundary checks.
- Active-holder lease target role, agent id, packet, route version, and
  frontier version checks.
- PM role-work request/result state tracking.

## Gate Decision

The gate receives the candidate dispatch action and produces one of:

- `pass`: expose the dispatch action normally.
- `wait`: do not expose the dispatch; expose or preserve a wait for the
  unfinished prior obligation that blocks the same target role.
- `block`: stop dispatch for a malformed candidate or ambiguous state that
  cannot safely identify the target role or legal wait.

## ACK-Only vs Work Package

The gate classifies a system-card delivery by what it asks the role to do after
opening it:

- ACK-only prompt/material package: the card or bundle requires only runtime
  open/read receipt/ACK. It does not by itself ask for a decision, report,
  packet, result, blocker, or next instruction.
- Output-bearing work package: the card, bundle, event card, mail, or packet
  asks the recipient for anything beyond ACK. Examples include PM decisions,
  reviewer reports, worker results, packet specs, repair choices, route
  mutations, and model-miss triage decisions.

Only ACK-only packages are treated as passive prompt/material delivery. Anything
with an output obligation participates in the recipient-idle rule. Event cards
such as `pm.event.reviewer_report` and `pm.event.reviewer_blocked` are work
context when PM must inspect them and produce a later decision; they are not
free-standing prompt cards.

## User Intake First Work

`user_intake` is formal PM work material, not a prompt card. After startup
activation, Controller relays it to PM as the first PM work entry. That relay
must declare the first expected PM output:

- PM opens `user_intake` through the runtime.
- PM receives `pm.material_scan` as the same-obligation instruction card.
- PM returns `pm_issues_material_and_capability_scan_packets`, the first
  material/capability scan packet specs derived from the user input.

Until that first output returns, the gate treats PM as busy with the
`user_intake` chain. The only same-role system card allowed through that active
packet holder is the `pm.material_scan` instruction card that tells PM how to
produce the first output. Other independent PM dispatches must wait.

## Idle Rule

A target role is busy when the current run has an unfinished obligation for the
same target role that is not part of the candidate grouped delivery or the
same active obligation. The main sources are:

- unresolved target-role system-card or bundle ACKs;
- controller/passive waits for that target role;
- packet ledger records where the target role still holds an active packet,
  for new independent mail or work-packet dispatches;
- PM role-work request records where the target role has not returned its
  result yet, for new independent mail or work-packet dispatches.

System-card delivery is the handoff that may start or guide a role obligation.
It is still blocked by unresolved card ACKs and active passive waits. ACK-only
prompt/material cards are not treated as new work packages, but their ACK must
clear before later output-bearing work can proceed. An active packet held by
the same role only allows an output-bearing card when that card is part of the
same obligation, such as `pm.material_scan` for the PM-held `user_intake`
packet, or an event/context card that feeds the already-pending PM decision.
If the card asks the role to produce a decision, report, packet, result, or
blocker for a different obligation, the post-card wait/expected event is the
busy source that blocks the next independent dispatch.

For PM role-work, the original target role is no longer busy after its result
has returned. If the result has returned but PM has not absorbed, cancelled, or
superseded it, PM is the busy role for the pending decision.

## Grouping Rule

Same-role system-card bundles remain a single grouped delivery. The gate must
not split or reject the members only because they are grouped together. Same
batch work packets remain valid for different target roles, but a single batch
still cannot assign two independent open packets to the same role.

## FlowGuard Scope

Use a focused model for this change instead of the heavy project-wide Meta and
Capability models. The model must show:

- a busy role receiving a second independent dispatch is rejected;
- ACK-only prompt/material cards are distinguished from output-bearing work
  packages;
- output-bearing event/context cards for a pending PM decision are treated as
  work context, not free prompt cards;
- a same-role system-card bundle is allowed as one grouped delivery;
- `user_intake` makes PM busy until PM returns material/capability scan packet
  specs;
- the `pm.material_scan` first-output instruction card is allowed while PM
  holds `user_intake`;
- different idle roles can receive parallel dispatch;
- a target role becomes eligible again after its prior result returns;
- PM stays busy while a returned result awaits PM disposition.

The Meta and Capability simulations are explicitly deferred by user direction
because the change is within Router dispatch gating, not broad capability
routing or parent model hierarchy.

## Compatibility

The implementation should add the gate as a small Router helper and call it at
dispatch action boundaries. Existing local checks should remain in place as
defense in depth until focused tests prove the unified path covers them.
