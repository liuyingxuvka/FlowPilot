## Why

FlowPilot's v0.9.6 structural pass made the router and model files easier to
inspect, but several active Python scripts are still too large, duplicated, or
too responsibility-heavy for safe long-term maintenance. This change continues
the behavior-preserving structure work by reducing Python module weight while
keeping current public entrypoints, protocol semantics, persisted JSON shapes,
and release scope unchanged.

## What Changes

- Record the current `main` baseline and local rollback backups before editing.
- Extend the structural FlowGuard guard to cover this second simplification
  pass: duplicate wrapper cleanup, packet runtime slicing, install-check slicing,
  Meta/Capability phase slicing, router hotspot slicing, test-domain migration,
  installed-skill sync, and local git sync without release publication.
- Convert duplicated repository CLI logic into thin wrappers where the skill
  asset is the source of truth.
- Split large Python modules behind compatibility facades:
  `packet_runtime.py`, `scripts/check_install.py`, selected Meta/Capability
  model phases, selected router event/action hotspots, and router runtime tests.
- Preserve import compatibility, command-line compatibility, validation output
  shapes, event names, persisted JSON payloads, and runtime card/protocol
  semantics.
- Synchronize the local installed FlowPilot skill and local git state after
  validation.
- Do not tag, publish a GitHub Release, deploy, package binaries, or push remote
  branch changes as part of this structure-only pass.

## Capabilities

### New Capabilities

- `python-structure-simplification`: rules for reducing active FlowPilot Python
  file/function size through source-of-truth wrappers, compatibility facades,
  domain modules, focused validation, install sync, and local git sync.

### Modified Capabilities

- None. Existing product, protocol, and runtime behavior requirements remain
  unchanged.

## Impact

- Affected code:
  - `scripts/flowpilot_user_flow_diagram.py`
  - `skills/flowpilot/assets/packet_runtime.py` and new packet runtime helper modules
  - `scripts/check_install.py` and new install-check helper modules
  - `simulations/meta_model.py`, `simulations/capability_model.py`, and new phase helper modules
  - `skills/flowpilot/assets/flowpilot_router.py` and focused router helper modules
  - router runtime domain tests
- Affected model/check artifacts:
  - `simulations/flowpilot_structural_refactor_model.py`
  - `simulations/run_flowpilot_structural_refactor_checks.py`
  - FlowGuard result JSON files touched by reruns
- Affected documentation:
  - `HANDOFF.md`
  - `README.md`
  - `docs/flowguard_adoption_log.md`
  - optional structural baseline notes
- No external dependency, user-facing feature, protocol, public API, release,
  deployment, or package format changes.
