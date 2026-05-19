## Why

FlowPilot now has many small owner modules, but lock-related names can still be
misread as one scattered subsystem. The next maintenance step should preserve
the current facade-first split while making runtime JSON locks, daemon locks,
and packet active-holder leases visibly separate ownership domains.

## What Changes

- Add a lock-boundary ownership map for maintainers.
- Add a small shared process-liveness helper so runtime JSON write-lock checks
  and Router daemon lock checks do not duplicate platform-specific process
  probing.
- Update StructureMesh evidence so the new helper is a named owner boundary.
- Keep existing public router imports, CLI behavior, event names, persisted JSON
  shapes, and lock file formats stable.
- Do not reorganize the full source tree or merge active-holder leases into the
  runtime file-lock mechanism.

## Capabilities

### New Capabilities

- `lock-boundary-ownership`: Documents and preserves distinct ownership for
  FlowPilot runtime JSON write locks, Router daemon locks, and packet
  active-holder leases.

### Modified Capabilities

- None.

## Impact

- Affected code: small owner-helper extraction under
  `skills/flowpilot/assets/`, StructureMesh catalog evidence, boundary tests,
  and maintenance documentation.
- Affected validation: focused owner-boundary tests, StructureMesh checks,
  model-test alignment where relevant, install sync checks, and background
  Meta/Capability regressions before final local commit.
- Release behavior: local repository and installed local skill sync only; no
  remote push, tag, deploy, or GitHub Release.
