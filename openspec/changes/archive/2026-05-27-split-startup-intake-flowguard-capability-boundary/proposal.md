## Why

`flowpilot_router_startup_intake_materialization.py` still combined startup
intake materialization, deterministic seed orchestration, and FlowGuard
capability snapshot classification/writing. The FlowGuard capability snapshot is
a finite startup policy boundary and can be tested directly, so keeping it in
the materialization parent kept the model too coarse.

## What Changes

- Add a startup intake FlowGuard capability child module.
- Keep the existing startup intake materialization parent as the compatibility
  surface.
- Move FlowGuard capability snapshot path, portable skill-root discovery,
  route classification, import snapshot, route discovery, and snapshot writing
  into the child.
- Add source-audited model/test evidence for the new leaf boundary.

## Impact

- No startup answer, user-intake, deterministic seed, mailbox, or bootstrap
  behavior changes.
- The materialization parent falls below the StructureMesh threshold.
- FlowGuard route classification and capability snapshot writes now have direct
  child-boundary tests.
