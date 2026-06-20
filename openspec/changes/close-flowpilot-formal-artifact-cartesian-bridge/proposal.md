## Why

The formal artifact registry, fake-AI responder, and ContractExhaustionMesh now
cover registered AI-submitted file artifacts, but the upper FlowPilot
control-plane Cartesian bridge still treats the new formal artifact mutation
families as unknown. That makes lower-level coverage green while the global
coverage claim is not closed.

A role-recovery liveness test also still expects the old
`unknown_liveness_marked_safe` hazard name after the model renamed the current
state to `unknown_binding_evidence_marked_safe`.

## What Changes

- Add registered formal artifact fault modes to the control-plane Cartesian
  mutation alphabet as first-class current-contract mutations.
- Bind formal artifact mutations to the artifact/evidence/result bridge
  boundaries that can consume them, without compatibility aliases or fallback
  translations.
- Keep bridge rows identity-preserving unless a source mutation has an
  explicit canonical current-control-plane mapping.
- Update the role-recovery liveness test to assert the current model hazard
  name.

## Impact

- `simulations/flowpilot_cartesian_control_plane_exhaustion_model.py`
- `tests/test_flowpilot_cartesian_control_plane_exhaustion.py`
- `tests/test_flowpilot_role_recovery_liveness_model.py`
- Focused Cartesian, fake-AI, liveness, OpenSpec, topology, and install checks.
