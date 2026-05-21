# FlowPilot Lock Boundary Map

Date: 2026-05-19

This map is a maintainer guide for the current FlowPilot structure. It does not
replace executable tests or FlowGuard checks.

## Boundary Summary

| Boundary | Owner | Persisted Artifacts | Meaning | Must Not Be Merged With |
| --- | --- | --- | --- | --- |
| Runtime JSON write lock | `flowpilot_router_io_locks.py` through the `flowpilot_router_io.py` facade | `<target>.write.lock`, `.tmp-*`, `runtime_json_write_lock_takeovers.jsonl` | Protects atomic JSON writes and daemon-critical reads from partial file state. | Packet active-holder leases or daemon lifecycle decisions. |
| Router daemon lock | `flowpilot_router_daemon_runtime.py` with liveness constants/helpers in `flowpilot_router_startup_daemon.py` | `runtime/router_daemon.lock`, `runtime/router_daemon_status.json`, `runtime/router_daemon_events.jsonl` | Enforces one Router daemon writer for a run and projects daemon status/heartbeat. | Runtime JSON write-lock takeover policy or packet holder authority. |
| Packet active-holder lease | `packet_runtime_active_holder_*.py` | `packets/<packet_id>/active_holder_lease.json`, `active_holder_events.jsonl`, packet ledger fields | Authorizes the current packet holder role/agent to ACK, report progress, or submit a result through the fast lane. | Filesystem locks or daemon single-writer locks. |
| Shared process liveness probe | `flowpilot_process_liveness.py` | None | Answers only whether a pid-like value appears to name a live local process. | Any lock-domain state machine or ownership decision. |

## Runtime JSON Write Locks

Runtime JSON write locks are file-write guards. They answer questions such as:

- is another process actively writing this JSON file;
- should the daemon wait and retry;
- is the owner process dead, allowing takeover evidence to be recorded;
- did a bounded atomic replace fail because the target was still busy.

The owner is `flowpilot_router_io_locks.py`, while `flowpilot_router_io.py`
keeps the legacy facade exports such as `_json_write_lock_liveness`,
`_raise_if_runtime_write_active`, and `write_json_atomic`. Callers should not
reimplement write-lock classification locally.

## Router Daemon Locks

Router daemon locks are run lifecycle guards. They answer questions such as:

- is there already a live Router daemon for this run;
- should a foreground controller attach to the existing daemon;
- may a stale lock be explicitly replaced;
- should terminal lifecycle release or mark the daemon lock.

The daemon runtime owns the lifecycle decision. The shared process-liveness
probe only supplies pid liveness; it does not decide whether a daemon is live,
stale, released, or terminal.

## Packet Active-Holder Leases

Active-holder leases are packet protocol authority. They answer questions such
as:

- which concrete role and agent currently owns a packet fast-lane action;
- whether the role may ACK, write progress, or submit a result;
- whether route/frontier versions still match the current packet authority.

They are intentionally separate from filesystem locks. A packet lease should not
be used to resolve partial JSON writes or daemon single-writer conflicts.

## Maintenance Rule

When touching any of these boundaries:

1. Identify which lock or lease concept is affected before editing.
2. Keep process-liveness probing shared, but keep lock-domain decisions in the
   domain owner.
3. Run focused owner-boundary tests and the StructureMesh gate before claiming
   the structure is green.
