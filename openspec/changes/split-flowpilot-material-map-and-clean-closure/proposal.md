## Why

The latest FlowPilot control-plane hardening left one explicit completion gap:
`flowpilot_material_artifact_map.py` still exceeds the model-test-code
diagnostic split threshold. The repository also contains parallel repair
dossier and active-child-lineage work that must be preserved and verified
without being silently folded into unrelated cleanup.

## What Changes

- Split material artifact-map implementation internals behind the existing
  public facade so the facade remains small and behavior-compatible.
- Keep the material map policy unchanged: it is a navigation/audit index, not a
  permission allowlist; ordinary non-sealed project/run files remain readable by
  formal work roles, while sealed bodies still require runtime authorization.
- Bind the split to FlowGuard StructureMesh, material-map model checks,
  boundary tests, and model-test-code diagnostics.
- Re-verify the historical blocker repair replay surfaces produced by the
  repair dossier and active child lineage work without reverting or absorbing
  unrelated peer-agent files.
- Serialize install sync, install audit, installed self-check, and local git
  evidence after source validation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `material-artifact-map`: split internal ownership while preserving the
  existing facade, schema, public functions, sealed-body boundary, and
  navigation-only semantics.
- `full-model-test-code-diagnostics`: require the material artifact-map split
  debt to be closed before claiming clean FlowPilot control-plane closure.
- `tiered-flowpilot-test-validation`: require clean closure verification to
  distinguish current source evidence, historical replay evidence, install
  sync evidence, and peer-agent dirty worktree boundaries.

## Impact

- `skills/flowpilot/assets/flowpilot_material_artifact_map*.py`
- Material artifact-map FlowGuard model and boundary tests.
- Model-test alignment and topology result artifacts.
- OpenSpec verification and install/sync audit evidence.
