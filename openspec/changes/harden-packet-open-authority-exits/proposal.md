## Why

FlowPilot can reach a state where a role successfully opens an addressed packet through the runtime, but the role still waits for extra relay confirmation or silently stops after ACK. The concrete failure surfaced with PM: the packet ledger proved `open-packet` succeeded for `project_manager`, while PM reported that it was standing by for corrected relay evidence.

That is a protocol gap. A successful runtime packet open already verifies the target role, relay authority, and body hash. After that, the role has enough authority to work the packet. If the role truly cannot proceed, the route must receive a formal existing exit instead of a chat wait.

## What Changes

- Make successful `open-packet` sessions carry explicit work-authority metadata: success authorizes the addressed role to continue work without waiting for another Controller relay.
- Strengthen packet and role-card prompts so every addressed role continues after a verified open, or returns a formal existing blocker/repair output.
- Preserve the PM special case: PM does not submit a normal blocker to itself; PM uses existing startup repair, startup protocol dead-end, or control-blocker repair decision contracts.
- Preserve the ordinary role path: workers, reviewers, and officers may submit existing blockers or PM suggestions for PM/Router disposition when they cannot complete the packet.
- Add focused FlowGuard coverage for the invalid states: verified open followed by indefinite wait, PM self-blocker loop, new custom PM repair flow, and ordinary role silent wait.

## Capabilities

### New Capabilities

- `packet-open-authority-exits`: Runtime and prompt contract that a verified packet-open receipt is enough authority to work, and every unable-to-proceed state must use an existing formal exit.

### Modified Capabilities

- `blocker-repair-policy`: PM inability to proceed must compose with the existing startup repair/protocol-dead-end/control-blocker repair policy rather than inventing a parallel blocker route.
- `work-packet-ack-continuation`: Packet continuation guidance now covers verified `open-packet` success, not only ACK.

## Impact

- Affected code: `skills/flowpilot/assets/packet_runtime.py`.
- Affected cards: FlowPilot role cards and PM startup/control-blocker phase cards.
- Affected tests: packet runtime and card instruction coverage.
- Affected models: focused FlowGuard packet-open authority model; broad meta/capability checks should still be run in the background because this touches project-control protocol.
- Affected install flow: local installed FlowPilot skill must be resynced after source changes.
