## Context

The observed failures were not separate one-off bugs. They shared one pattern:
FlowPilot trusted a coarse control-plane marker after the real authority had
moved somewhere more specific. A closed action id was treated as proof for a
different packet request, a failed send was still called done, a stale crew
record was treated as a live worker, a corrupt ledger was treated as an
unexpected daemon crash, and a material evidence index described access that the
runtime would not actually grant.

## Design

### Identity Is Scoped To The Work Unit

Controller action identity and router scheduler idempotency must include the
fields that distinguish concrete work: `batch_id`, `request_id`, `packet_id`,
`packet_ids`, and recipient role. Existing blocker-specific identity remains in
place.

### Done Means Delivered

A Controller can report failed delivery, but not as a `done` receipt. If a
receipt payload says delivery failed, the valid status is `blocked`; `done`
with a failed delivery marker is rejected before reconciliation can close the
row.

### Ledger Writes Are Recoverable

Packet ledger writes use a unique temp file, lock file, `fsync`, `os.replace`,
and JSON readback. If a ledger read hits a corrupt duplicate-tail style write,
FlowPilot backs up the corrupt file, salvages the first complete JSON object
when possible, records recovery metadata, and continues with a valid ledger
instead of crashing the control loop.

### Active Holder Requires Live Role Evidence

The packet runtime may issue an active-holder lease only when the run's
`crew_ledger.json` proves the target role has a current live slot for the exact
agent id. The lease stores that proof so receipt folds can later verify it.

### Material Gate Evidence Does Not Overclaim

The material artifact map remains an index. It can list result envelopes and
sealed body references, but it cannot claim reviewer raw-body access unless the
runtime relay/open authority supports that role. PM formal gate packages block
when source result contract self-checks are missing, failed, or unparseable;
otherwise reviewer approval would be asked to reason from bad or unavailable
evidence.

## Trade-offs

This does not introduce a new control-plane subsystem. It strengthens the
existing contract helpers and runtime writes at the boundaries that already own
the behavior.
