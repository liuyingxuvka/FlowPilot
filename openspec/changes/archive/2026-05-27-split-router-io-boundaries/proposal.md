# Split Router IO Boundaries

## Summary

Split `flowpilot_router_io.py` into a thin compatibility facade plus focused
child owner modules for runtime paths/time helpers, runtime JSON write-lock
handling, JSON read/write operations, and role-output hash helpers.

## Motivation

`flowpilot_router_io.py` is currently the largest runtime owner module in the
maintenance map. It mixes unrelated responsibilities:

- path and runtime-kit resolution;
- UTC timestamp parsing/formatting;
- runtime JSON write-lock liveness, takeover, cleanup, and settlement;
- JSON read/write wrappers;
- role-output semantic hash helpers.

Those responsibilities already have separate behavior boundaries and tests.
Keeping them in one large file increases StructureMesh pressure and makes
future lock or path changes harder to review.

## Scope

In scope:

- preserve every existing import from `flowpilot_router_io`;
- move implementation into child modules without changing observable behavior;
- update install manifests, StructureMesh catalogs, model-test alignment
  contracts, maintenance maps, and focused tests;
- run focused IO/daemon/terminal validations plus background router, Meta, and
  Capability regressions before claiming done;
- sync the repo-owned FlowPilot skill into the local installed skill location;
- capture the result in local git.

Out of scope:

- changing runtime JSON lock semantics;
- changing daemon lock behavior;
- changing packet, role-output, or Router public APIs;
- pushing to GitHub, publishing a release, or tagging a version.

## Compatibility Contract

Existing callers SHALL continue to import and call through
`flowpilot_router_io.py`. The parent module remains the compatibility surface;
child modules are implementation owners.
