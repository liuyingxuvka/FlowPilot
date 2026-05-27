## Why

The first router modularization pass removed several low-risk helper
responsibilities from `flowpilot_router.py`, but the remaining file still mixes
stateful reconciliation, startup/daemon helpers, dispatch gates, terminal
status handling, and the large runtime test suite. A second conservative pass
is needed while the fresh baseline is still easy to compare against.

This change continues the extraction only at seams that can be validated as
behavior-preserving. Anything that needs a protocol, authority, schema, or
settlement behavior change remains in the router until a separate OpenSpec
change captures it.

## What Changes

- Keep a local non-runtime backup of the current router and key runtime tests
  before further maintenance.
- Split the monolithic runtime test file into smaller boundary suites that
  reuse the current test class and keep the facade suite available.
- Extract pure Controller receipt/scheduler reconciliation helpers where they
  can be verified without moving write-bearing finalizers prematurely.
- Extract pure ACK/return-settlement helpers that preserve the separation
  between ACK waits and output-bearing work completion.
- Extract startup/daemon, dispatch/packet gate, and terminal helper boundaries
  only where the seam is table-driven or pure.
- Update install checks, FlowGuard adoption notes, and local installed skill
  sync after validation.
- Run focused tests, OpenSpec validation, install audit, smoke checks, and
  broad FlowGuard regressions before local git commit.

No breaking CLI, runtime schema, packet schema, role authority, or OpenSpec
behavior change is intended.

## Capabilities

### New Capabilities

- `router-stateful-maintenance-boundaries`: behavior-preserving requirements
  for the second router maintenance pass, including boundary test
  partitioning, safe helper extraction, FlowGuard evidence, and installed skill
  synchronization.

### Modified Capabilities

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- Additional helper modules under `skills/flowpilot/assets/`
- Focused router runtime test modules under `tests/`
- `tests/test_flowpilot_router_boundaries.py`
- `scripts/check_install.py`
- `docs/flowguard_adoption_log.md`
- OpenSpec change artifacts and validation
- Local installed FlowPilot skill under the Codex skills directory after
  repository validation passes
