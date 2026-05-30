## Why

FlowPilot's current runtime is meant to be a clean new system based on
runtime-requested role responsibilities and host-supported role bindings, but
active prompts, templates, state fields, models, tests, and install checks still
carry historical runtime-role, sidecar role, fixed-crew, unsupported historical, and
FlowPilot runtime terminology. Those residues can teach future agents the old topology
and keep unsupported historical surfaces alive after the product direction has moved on.

## What Changes

- **BREAKING**: remove old unsupported historical language from active FlowPilot prompt,
  template, state, model, check, and local-install surfaces instead of preserving
  old names as unsupported historical aliases.
- Replace fixed crew/background/sidecar role wording with topology-neutral runtime
  role responsibility and role-binding wording.
- Replace `crew`, `runtime_role_assistances`, `sidecar role`, `required_role_binding`, and
  `FlowPilot runtime` identifiers in current authoritative surfaces when they are not
  purely historical records.
- Retain only explicit "unsupported input" rejection behavior where needed for
  safety, without presenting unsupported routes as current repair options.
- Extend checks so role-facing prompts and project templates cannot reintroduce
  the old terminology.
- Regenerate affected FlowGuard/model/test result artifacts and sync the local
  installed FlowPilot copy after validation.

## Capabilities

### New Capabilities
- `flowpilot-clean-runtime-language`: defines the clean runtime-language
  contract across prompts, templates, state/model terms, validation checks, and
  installed-skill synchronization.

### Modified Capabilities
- `flowpilot-prompt-boundary-policy`: active prompt/card boundaries must avoid
  old topology and unsupported historical wording as current instruction.
- `flowpilot-maintenance-ideal-state`: final maintenance completion must include
  clean-language validation, install sync, and git synchronization for changed
  prompt/template/model/check surfaces.

## Impact

- FlowPilot skill entrypoint and runtime kit prompts/cards.
- `templates/flowpilot` runtime templates and generated-state terminology.
- Runtime CLI/state fields where old terminology is still current authority.
- FlowGuard meta/capability models, targeted result artifacts, and alignment
  checks that refer to fixed role binding or old agent topology.
- Install checks, local install audit/sync, topology generation, and repository
  maintenance documentation.
