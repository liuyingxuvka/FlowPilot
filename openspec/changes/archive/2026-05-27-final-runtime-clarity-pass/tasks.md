## 1. Planning And Evidence Boundaries

- [x] 1.1 Validate the new OpenSpec change and keep remote publication out of scope.
- [x] 1.2 Update FlowGuard StructureMesh/TestMesh targets for facade export, packet runtime, card runtime, user-flow diagram, packet prompt assets, and packet control-plane model owners.
- [x] 1.3 Run focused pre-split compile/import checks to establish current behavior and public entrypoint parity.

## 2. Facade Export Registry

- [x] 2.1 Extract the `OWNER_EXPORTS` registry data into a dedicated manifest module.
- [x] 2.2 Keep `flowpilot_router_facade_exports.py` as the resolver/installer facade and preserve all registered targets.
- [x] 2.3 Add or update focused import checks for missing facade targets and public allowlist compatibility.

## 3. Packet Prompt Assets

- [x] 3.1 Add runtime-kit packet prompt templates for packet identity, result identity, and output-contract sections.
- [x] 3.2 Update `runtime_kit/prompts/manifest.json` with hashes and template variables for the new packet prompts.
- [x] 3.3 Refactor `packet_runtime_contracts.py` to render moved prompt text through PromptStore without unsafe inline fallbacks.
- [x] 3.4 Extend prompt-store tests to reject missing, stale, and undeclared packet prompt assets.

## 4. Packet Runtime Split

- [x] 4.1 Extract packet progress/status helpers into a focused owner module.
- [x] 4.2 Extract packet creation and controller handoff helpers into a focused owner module.
- [x] 4.3 Extract packet result write/read helpers into a focused owner module.
- [x] 4.4 Extract packet audit and replacement-chain helpers into a focused owner module.
- [x] 4.5 Keep `packet_runtime.py` as the compatible facade/CLI entrypoint.
- [x] 4.6 Run focused packet runtime tests and repair split import regressions.

## 5. Card Runtime Split

- [x] 5.1 Extract card runtime I/O/path/hash helpers into a focused owner module.
- [x] 5.2 Extract card and return ledger helpers into a focused owner module.
- [x] 5.3 Extract card envelope and identity validation helpers into a focused owner module.
- [x] 5.4 Extract single-card ACK helpers into a focused owner module.
- [x] 5.5 Extract bundle open/ACK/incomplete helpers into a focused owner module.
- [x] 5.6 Keep `card_runtime.py` as the compatible facade/CLI entrypoint.
- [x] 5.7 Run focused card runtime/router card tests and repair split import regressions.

## 6. User Flow Diagram Split

- [x] 6.1 Extract route/source loading helpers into a focused owner module.
- [x] 6.2 Extract route tree/topology helpers into a focused owner module.
- [x] 6.3 Extract stage classification helpers into a focused owner module.
- [x] 6.4 Extract Mermaid rendering helpers into a focused owner module.
- [x] 6.5 Extract chat Markdown rendering helpers into a focused owner module.
- [x] 6.6 Keep `flowpilot_user_flow_diagram.py` as the compatible facade/CLI entrypoint.
- [x] 6.7 Run focused user-flow diagram tests and repair split import regressions.

## 7. Packet Control-Plane Model Split

- [x] 7.1 Extract packet control-plane model dataclasses/state helpers into a focused model owner module.
- [x] 7.2 Extract packet control-plane transition classes into a focused model owner module.
- [x] 7.3 Extract packet control-plane invariants into a focused model owner module.
- [x] 7.4 Keep `packet_control_plane_model.py` as the compatible workflow facade.
- [x] 7.5 Run packet control-plane model checks and repair split import regressions.

## 8. Documentation, Version, And Local Sync

- [x] 8.1 Update maintainer module maps and prompt runtime-kit descriptions.
- [x] 8.2 Update legacy prompt/card matrix and maintenance notes for the moved packet prompt text.
- [x] 8.3 Bump version and update changelog.
- [x] 8.4 Synchronize the installed local FlowPilot skill and verify freshness.

## 9. Full Validation And Commit

- [x] 9.1 Run OpenSpec validation for the change.
- [x] 9.2 Run StructureMesh/TestMesh/model-test alignment checks.
- [x] 9.3 Run router background tier with hidden background artifacts and inspect final status.
- [x] 9.4 Run Meta and Capability FlowGuard regressions with hidden background artifacts and inspect final status.
- [x] 9.5 Run local public-release boundary checks without GitHub push/tag/release.
- [x] 9.6 Commit locally on `main`.
