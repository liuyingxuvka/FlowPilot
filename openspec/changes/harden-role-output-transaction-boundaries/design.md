## Context

FlowPilot already separates role bodies from Controller-visible envelopes for most formal role outputs through `role_output_runtime`. It also has a control transaction registry that is intended to be the bottom-level authority for route progression, packet dispatch, result absorption, reviewer gates, repair, route mutation, and legacy reconciliation.

The current gap is that PM package result disposition still sits between those mechanisms. Router waits ask PM for a disposition payload, but the PM disposition is not represented as a registry-backed role output contract and is not fully covered as a transaction before package artifacts, batch status, wait flags, and run-state projections are mutated. Control-blocker identity has a similar coverage gap: blocker identity fields exist, but only the initial `handle_control_blocker` action uses them.

## Goals / Non-Goals

**Goals:**
- Make PM package result disposition an ordinary registry-backed PM role output.
- Keep PM disposition body fields out of Controller-visible event envelopes.
- Route PM package absorption through a registered result-absorption transaction before any state mutation can unlock continuation.
- Make repeated or resumed PM package disposition idempotent instead of leaving half-written state.
- Reuse existing control-blocker identity fields for all blocker-related waits and repairs that carry blocker identity.
- Cover the new obligations with FlowGuard models, source conformance checks, and ordinary runtime tests.

**Non-Goals:**
- Do not introduce a new envelope framework.
- Do not duplicate contract or event metadata into a second registry.
- Do not change worker result envelope schemas.
- Do not publish, deploy, or change external dependencies.
- Do not modify unrelated active OpenSpec changes or unrelated dirty files.

## Decisions

1. Use the existing contract registry as the source of truth.
   - Add a PM package disposition output contract that binds allowed role, output type, body schema, fixed Router events, default path metadata, and role-output runtime channel.
   - Alternative rejected: keep accepting hand-authored event envelopes and add another ad hoc validator. That would preserve the same class of human-shaped envelope errors.

2. Treat PM package disposition as result absorption in the existing transaction registry.
   - Extend `result_absorption` to include PM package disposition events and commit surfaces needed by PM absorption.
   - Alternative considered: create a separate transaction type. This is only needed if the existing `result_absorption` row cannot express PM producer role, PM output contract, packet authority, and commit targets cleanly.

3. Keep the runtime envelope small and reference-only.
   - The role-output runtime envelope remains Controller-visible and contains body references, hashes, receipt references, contract ids, and output types.
   - The decision body remains file-backed and readable only by the authorized role path.

4. Generalize blocker identity through the existing helper.
   - `control_plane_action_identity_extra_fields` will include blocker identity for any action that carries blocker identity, not only `handle_control_blocker`.
   - This preserves the current deterministic action-id mechanism while preventing old blocker waits from matching new blocker waits.

5. Validate with model-first evidence before broad runtime confidence.
   - Extend focused FlowGuard models first: role-output runtime, control transaction registry, PM package absorption, and control-plane friction.
   - Then run targeted runtime/unit tests.
   - Heavy Meta and Capability checks can run in the documented background artifact contract after focused checks are stable.

## Risks / Trade-offs

- [Risk] A new PM contract could drift from runtime output specs. -> Mitigation: add source conformance checks that compare registry rows, runtime specs, Router events, and allowed roles.
- [Risk] Extending `result_absorption` could make worker and PM absorption responsibilities ambiguous. -> Mitigation: keep producer role, output contract, and event scenarios explicit in the model and tests.
- [Risk] Idempotent replay could hide a stale half-write. -> Mitigation: replay must verify hashes/commit targets before treating a prior disposition as complete; mismatches become quarantine/blockers.
- [Risk] Installed skill sync could overwrite peer changes. -> Mitigation: sync only after validation and inspect git status before staging or committing.
- [Risk] Background long checks can be mistaken for pass evidence. -> Mitigation: use `tmp/flowguard_background/<name>.*` artifacts and report exit files, status, timestamps, and proof reuse status before claiming completion.
