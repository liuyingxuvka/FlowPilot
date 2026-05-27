## Context

The runtime JSON writer already uses a sentinel lock file to prevent concurrent
writes. The incident shows the lock file itself can become stale even when the
owner process is alive, because the owner may have finished the atomic replace
and then failed to remove its own sentinel. The existing model and runtime
logic did not distinguish `owner_pid == current daemon pid` from a different
live process.

## Goals / Non-Goals

**Goals:**

- Preserve protection against two processes writing the same JSON ledger.
- Avoid a daemon self-deadlock when its own stale lock remains after a
  successful write.
- Keep the normal cleanup path small and fast.
- Record lock cleanup failures instead of silently swallowing them.
- Require safe artifact checks before clearing a later-discovered self-owned
  stale lock.

**Non-Goals:**

- Replace JSON ledgers with a database.
- Replace the existing sentinel lock protocol wholesale.
- Let one process steal a lock from a different live process.
- Treat lock recovery as PM semantic repair before mechanical recovery fails.

## Design

### Normal cleanup path

`write_json_atomic()` owns the lock it just created. After writing, replacing,
and optionally verifying the target JSON, it should try to remove the matching
lock directly. If unlink fails, it should retry briefly with the existing
runtime lock polling interval. If the bounded retries still fail, it should
append a cleanup diagnostic record and then leave the sentinel in place for
later mechanical recovery.

This path does not need stale-lock takeover logic because it is cleaning up the
lock created by the same write call.

### Later recovery path

When a future writer sees an existing `.write.lock`, liveness should classify:

- `active_live_owner`: owner is a different live process; wait and do not clear.
- `active_self_owner`: owner is the current process and the lock is still fresh;
  wait and do not clear.
- `self_owned_stale_takeover`: owner is the current process, the lock is stale,
  the target JSON is parseable, and no matching `.tmp-*` write artifact remains;
  record takeover evidence, unlink the lock, and retry the write.
- `self_owned_stale_unsafe`: owner is the current process and stale, but target
  JSON is invalid or temp artifacts remain; do not clear automatically.
- Existing dead-owner and unknown-owner behavior remains intact.

### Diagnostics

Both cleanup failures and self-owned stale takeovers should write JSONL
diagnostics with target path, lock path, owner pid, classification, age,
target-valid flag, temp-artifact flag, and error text when available.

## Validation

- FlowGuard persistent daemon model includes the self-owned stale lock state,
  unsafe-clear hazards, cleanup diagnostic hazards, and rejoin-to-flow hazard.
- Focused unit tests cover self-owned stale takeover, fresh self-owned lock
  deferral, unsafe temp-artifact rejection, and cleanup failure diagnostics.
- Existing dead-owner takeover and fresh other-live-owner wait tests remain
  green.
- Heavy model regressions may run in background, but final reporting must
  distinguish completed checks from still-running or timed-out checks.
