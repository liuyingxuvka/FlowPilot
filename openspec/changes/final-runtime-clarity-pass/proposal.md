## Why

The router facade is now a small skeleton, but several runtime and model files still carry mixed responsibilities and a few prompt-like text blocks remain embedded in Python. This pass finishes the structural cleanup by splitting the remaining heavy runtime surfaces into clear owner modules while preserving all public entrypoints and FlowGuard evidence.

## What Changes

- Move the large router facade export registry data into a dedicated manifest module while keeping the existing facade installer behavior.
- Externalize packet/result identity and output-contract prompt text into runtime-kit prompt assets with manifest hashes.
- Split `packet_runtime.py` into focused progress, creation, result, audit, and CLI owner modules behind the existing `packet_runtime.py` facade.
- Split `card_runtime.py` into focused I/O, ledger, envelope, ACK, and bundle owner modules behind the existing `card_runtime.py` facade.
- Split `flowpilot_user_flow_diagram.py` into source, route-tree, stage, Mermaid, Markdown, and CLI/facade modules.
- Split `packet_control_plane_model.py` into state/transition/invariant/workflow modules only after runtime splits are stable.
- Update FlowGuard StructureMesh/TestMesh/model-alignment evidence so the new owner boundaries are executable, not just documented.
- Update maintainer-facing descriptions and module maps in repository docs and skill assets.
- Sync the local installed FlowPilot skill and commit locally on `main`; remote GitHub push, tag, and release publication remain out of scope.

## Capabilities

### New Capabilities
- `runtime-structure-clarity`: Covers the final runtime/model owner split, prompt asset externalization, public facade compatibility, and validation gates for the FlowPilot runtime maintenance pass.

### Modified Capabilities
- `repository-maintenance-guardrails`: Extends maintenance requirements for this repo so large runtime splits require StructureMesh/TestMesh evidence, prompt-manifest validation, local install sync, and local-only git completion.

## Impact

- Affected runtime code: `skills/flowpilot/assets/flowpilot_router_facade_exports.py`, `packet_runtime.py`, `packet_runtime_contracts.py`, `card_runtime.py`, `flowpilot_user_flow_diagram.py`, `packet_control_plane_model.py`, plus new focused owner modules.
- Affected prompt assets: `skills/flowpilot/assets/runtime_kit/prompts/manifest.json` and new packet prompt templates under `runtime_kit/prompts/packets/`.
- Affected tests/models: focused packet/card/user-flow tests, prompt-store tests, StructureMesh/TestMesh checks, model-test alignment, router background tier, Meta and Capability FlowGuard regressions.
- Affected docs/versioning: `skills/flowpilot/assets/README.md`, `skills/flowpilot/assets/runtime_kit/prompts/README.md`, `docs/legacy_prompt_to_cards_matrix.md`, `CHANGELOG.md`, and `VERSION`.
