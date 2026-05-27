## Context

The current router structure already follows a facade-first split:
`flowpilot_router.py` remains the compatibility entrypoint while owner modules
hold implementation bodies. The remaining risk is not file count. The risk is
that maintainers see `lock`, `lease`, and `active holder` names in several
places and try to collapse distinct protocols into one module.

There are three separate concepts:

- runtime JSON write locks: short-lived `.write.lock` files around atomic JSON
  writes and daemon-critical reads;
- Router daemon lock: the run-scoped single-writer lock and heartbeat/status
  projection for the persistent router daemon;
- packet active-holder lease: a Router-authorized packet protocol lease for the
  current role holder, not a filesystem lock.

## Goals

- Preserve current public entrypoints and persisted records.
- Make the three lock/lease domains visible in documentation and StructureMesh
  evidence.
- Remove duplicated platform process-liveness code behind one small helper.
- Keep the patch narrow enough to avoid peer-agent conflicts.

## Non-Goals

- Do not perform a tree-wide module reorganization.
- Do not rename existing lock files, schema strings, CLI flags, event names, or
  JSON fields.
- Do not move packet active-holder leases into the runtime JSON write-lock
  owner.
- Do not edit persistent daemon model files currently modified by another
  parallel agent.

## Design

### Shared process liveness owner

Add `flowpilot_process_liveness.py` as the single platform-specific process
probe owner. Runtime JSON write-lock liveness and Router daemon lock liveness
import the helper instead of carrying separate implementations.

The helper has no FlowPilot state authority. It receives a pid-like value and
returns a boolean. The existing callers still decide whether that process state
means active writer, dead-owner takeover, daemon-live, or daemon-stale.

### Boundary map

Add a maintenance document that names:

- owner module;
- persisted artifact family;
- meaning of the lock/lease;
- allowed callers;
- what must not be merged.

The document is descriptive guardrail evidence. It does not replace executable
checks.

### FlowGuard / StructureMesh evidence

Update the existing StructureMesh router catalog with a partition and module
evidence row for `process_liveness`. This keeps the structure check aware that
the helper is intentionally shared, rather than duplicate state ownership.

### Validation strategy

Run focused owner-boundary tests for router boundaries and startup daemon lock
behavior, then run the StructureMesh gate. Background Meta and Capability
regressions can run through the existing `tmp/flowguard_background/` contract
and must be inspected by exit artifacts before completion is reported.

## Risks

- Process-liveness behavior could drift on Windows if the helper differs from
  the duplicated implementation. Mitigation: move the same code without changing
  logic and run focused boundary tests.
- A broad cleanup could collide with parallel work. Mitigation: avoid dirty
  files and keep changes to a small owner-helper/documentation/catalog slice.
- Documentation could be mistaken for validation. Mitigation: keep FlowGuard and
  unit checks in the task list and final evidence.
