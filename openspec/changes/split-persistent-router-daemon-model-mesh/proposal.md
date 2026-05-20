# Split Persistent Router Daemon Model Mesh

## Why

The broad release/smoke gate is blocked because the parent model hierarchy still
consumes `flowpilot_persistent_router_daemon` as a single child evidence item.
That child result is green, but its state graph is larger than the thin-child
threshold, so the parent cannot claim release confidence from it.

## What Changes

- Keep the existing persistent daemon model as a compatibility/full-scope
  check.
- Add thin child model evidence for the daemon subdomains that the parent
  actually needs to consume:
  - startup, daemon lock, and runtime write-lock settlement;
  - Controller action receipts and stateful postcondition repair;
  - role wait metadata, liveness, mailbox, and external-event closure;
  - current-work projection, heartbeat, and terminal cleanup.
- Update the parent responsibility ledger, smoke checks, install checks, and
  alignment plan to consume the thin child evidence.

## Impact

The release gate can distinguish "the compatibility model remains available"
from "the parent has current thin child evidence." It must not pass by raising
thresholds or hiding the old result.
