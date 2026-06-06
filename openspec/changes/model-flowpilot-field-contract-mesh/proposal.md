# Proposal: Model FlowPilot Field Contract Mesh

## Summary

Add a multi-layer FlowGuard field model for current FlowPilot. The parent model
tracks critical transition fields. The child mesh classifies every observed
field into ownership and importance layers, binds critical fields to code
validators, and rejects production references to old FlowPilot field paths.

## Why

Strict current FlowPilot maintenance cannot rely on broad model passes if tests
or prompts can still advance through stale field names, old role-startup
shapes, or uninstalled split entry modules. Field-level modeling gives the
runtime and tests a concrete map of which fields advance which current path.

## Scope

- Add parent field contracts for startup acknowledgement, current background
  collaboration payloads, role binding ledgers, and role memory.
- Add a generated field mesh covering all observed fields across code, tests,
  simulations, templates, and current specs.
- Bind critical fields to current validators and reject unbound critical fields.
- Ensure public FlowPilot role handoff commands use `flowpilot_new.py` after the
  entrypoint split.
- Ensure install checks include the split `flowpilot_new_*` modules.
