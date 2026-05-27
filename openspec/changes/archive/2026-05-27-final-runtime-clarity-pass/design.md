## Context

`flowpilot_router.py` has been reduced to a small skeleton, but the runtime still has several large responsibility clusters:

- `flowpilot_router_facade_exports.py` is mostly registry data plus facade installation logic.
- `packet_runtime.py` mixes packet creation, progress, handoff, result, audit, and CLI behavior.
- `card_runtime.py` mixes I/O, ledgers, envelopes, single-card ACKs, and bundle ACKs.
- `flowpilot_user_flow_diagram.py` mixes route source loading, tree projection, stage classification, Mermaid rendering, Markdown rendering, and CLI behavior.
- `packet_control_plane_model.py` mixes model state, transitions, invariants, and workflow construction.
- `packet_runtime_contracts.py` still carries prompt-like packet/result boundary text and output-contract text in Python.

The current user constraint is local maintenance on `main`: no branch creation, no GitHub push, no tag, and no remote release publication. Long regressions must run through hidden/background logging so they do not interrupt the desktop.

## Goals / Non-Goals

**Goals:**
- Preserve public runtime entrypoints and CLI behavior.
- Move registry/config/prompt text out of behavior modules where practical.
- Split large modules by cohesive ownership, not one function per file.
- Keep each split module independently readable and import-compatible.
- Update StructureMesh/TestMesh/model-alignment evidence for the changed boundaries.
- Synchronize the installed local FlowPilot skill and create a local git commit.

**Non-Goals:**
- No GitHub push, tag, or GitHub Release.
- No behavioral redesign of packet/card protocols beyond defects discovered during the split.
- No one-function-per-file micro-module explosion.
- No replacement of FlowGuard with prose-only validation.

## Decisions

### Decision: Facade-first runtime splits

Each large public module remains as the compatibility facade while new owner modules carry cohesive bodies. This preserves existing imports and command lines while making internal ownership clearer.

Alternative considered: rename public modules and update all callers. Rejected because the compatibility surface is broad and unnecessary for this maintenance pass.

### Decision: Prompt assets use the existing PromptStore manifest

Packet/result boundary and output-contract text move into `runtime_kit/prompts/packets/` and are loaded through the existing manifest/hash path. This keeps copied runtime kits protected against stale or partial prompt assets.

Alternative considered: keep packet prompt strings in Python constants. Rejected because it leaves the same maintainability problem the router prompt-store split already solved.

### Decision: Runtime splits precede model split

`packet_runtime.py`, `card_runtime.py`, and `flowpilot_user_flow_diagram.py` are split before `packet_control_plane_model.py`. The model split is last because model coverage can look green while accidentally losing obligation clarity if state/transition/invariant ownership is changed too early.

Alternative considered: split the model first. Rejected because runtime behavior provides the concrete parity target for model-test alignment.

### Decision: Hidden background contract for heavy validation

Router tier, Meta, and Capability regressions run through the existing background artifact contract under `tmp/flowguard_background/`, with stdout/stderr/combined/exit/meta artifacts inspected before pass claims.

Alternative considered: run long checks in foreground. Rejected because the user explicitly reported foreground command windows interfering with normal work.

## Risks / Trade-offs

- Public facade export drift -> Mitigate with import/public symbol checks and StructureMesh public entrypoint evidence.
- Prompt hash mismatch after text movement -> Mitigate with manifest hash validation and prompt-store tests.
- Packet/card behavior regressions from split imports -> Mitigate with focused packet/card tests before broader router tiers.
- Model split hides coverage loss -> Mitigate by keeping known-bad hazards and model-test alignment checks green after the split.
- More files could reduce readability if overdone -> Mitigate by grouping by behavior family and keeping facade modules as maps.

## Migration Plan

1. Add/validate OpenSpec and FlowGuard maintenance evidence for the target owner layout.
2. Extract facade registry data into a manifest module.
3. Move packet prompt text into runtime-kit prompt assets and update hashes/tests.
4. Split packet runtime behind its existing facade and run focused tests.
5. Split card runtime behind its existing facade and run focused tests.
6. Split user-flow diagram generation behind its existing facade and run focused tests.
7. Split packet control-plane model behind its existing facade and run model checks.
8. Update docs/version/install evidence.
9. Run hidden/background router, Meta, and Capability regressions.
10. Sync local installed FlowPilot and commit locally on `main`.

Rollback is local git rollback to the pre-pass commit because no remote publication is in scope.

## Open Questions

No user decision is currently required. If the model split exposes unclear ownership or a behavior bug rather than a mechanical split issue, stop only for a materially different product/protocol decision.
