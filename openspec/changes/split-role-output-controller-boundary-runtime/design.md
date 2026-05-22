## Context

`role_output_runtime_envelopes.py` currently mixes two responsibilities:
generic role-output envelope mechanics and controller-boundary confirmation
helpers. The controller-boundary branch is finite and mechanically scoped: it
collects controller-core source hashes, builds a confirmation body, and submits
that body through the existing role-output runtime.

This is a StructureMesh split, not a behavior change.

## Target Structure

- `role_output_runtime_envelopes.py`
  - generic role-output submission;
  - envelope and receipt construction;
  - ledger append and lookup;
  - runtime receipt validation;
  - compatibility wrappers for controller-boundary helper names.

- `role_output_runtime_controller_boundary.py`
  - controller-boundary confirmation body construction;
  - controller-boundary confirmation submission orchestration;
  - no direct ledger ownership; submission is delegated through an explicit
    `submit_output` callback supplied by the facade.

Dependency direction stays one-way: the envelope facade imports the child
module, and the child module depends only on schema/path helpers plus the
explicit submission callback.

## Compatibility Boundary

The following names remain available from `role_output_runtime_envelopes.py`
and through the public `role_output_runtime.py` facade:

- `build_controller_boundary_confirmation_body`
- `submit_controller_boundary_confirmation`

The child module must not become a second owner for envelope receipt validation
or role-output ledger lookup.

## Validation Boundary

The split is green only if:

- focused role-output runtime tests still pass;
- tests directly exercise the child controller-boundary module;
- source-audited model-test evidence covers the child module;
- full coverage diagnostics no longer report `role_output_runtime_envelopes`
  as a StructureMesh split finding;
- local installed FlowPilot is synced and fresh.
