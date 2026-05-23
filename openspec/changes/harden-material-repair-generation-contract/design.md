## Context

FlowPilot already has the right ownership surfaces:

- `repair_transaction` owns PM-selected repair plans such as `packet_reissue`, `operation_replay`, and `controller_repair_work_packet`.
- `control_transaction_registry.json` owns commit authorization for `result_absorption` and `control_blocker_repair`.
- `parallel_packet_batch` owns packet batch lifecycle and result joins.
- Controller receipt reconciliation owns postcondition folding before pending action clearance.
- `role_output_runtime` and scoped event identity own formal role-output envelope validation and idempotency.
- break-glass incident/patch files already record emergency control-plane repairs.

The bug class appears when those existing owners do not share one current material-generation identity. The fix should add the missing identity and fold checks at their current boundaries, not create a second material repair subsystem.

## Goals / Non-Goals

**Goals:**

- Reuse existing `repair_transaction` and `control_transaction` paths.
- Make material packet reissue commit one current generation across material index, active batch, packet ledger projection, and repair transaction.
- Ensure operation replay creates a fresh current Controller action without copying stale action identity.
- Ensure `controller_repair_work_packet` receipt reconciliation updates the repair transaction before clearing Router pending state.
- Ensure PM material-scan disposition verifies active batch/generation/packet identity before committing result absorption.
- Ensure duplicate role-output events cannot repeat PM disposition or material-review side effects.
- Ensure break-glass patches receive a final validation disposition before the run can be considered clean.

**Non-Goals:**

- Do not introduce a new transaction registry or new PM repair lane.
- Do not change packet envelope immutability rules.
- Do not change worker result contract shape except for validating existing authority fields.
- Do not absorb unrelated peer-agent work, broad refactors, release publication, or remote GitHub actions.

## Decisions

1. Extend `packet_reissue` inside existing repair transactions.
   - The current `_commit_material_scan_repair_generation` already writes `current_generation_id` to the material index. Extend the same path to update the active `parallel_packet_batch` and any batch ref needed by current material-scan dispatch.
   - Old packets or batches become superseded evidence; they cannot satisfy current waits.

2. Treat operation replay as fresh action synthesis.
   - Use existing `operation_replay` plan kind.
   - Preserve `replay_of_controller_action_id` as audit metadata only.
   - Exclude action identity fields from copied source metadata and rederive reads/writes from current generation/batch/index state when the operation touches material packets.

3. Keep Controller repair work packet as a bounded Controller action.
   - Use the existing `controller_repair_work_packet` action and receipt helper.
   - A done receipt moves the repair transaction to `awaiting_recheck`; failure to update the transaction remains a control blocker.

4. Bind PM disposition to the active current generation.
   - PM package disposition remains `result_absorption`.
   - For `material_scan`, disposition must check that the active batch records match the material index current generation and packet ids.
   - If an old disposition artifact exists, replay must verify transaction identity, body hash, batch id, packet ids, and generation before marking complete.

5. Extend existing idempotency policy.
   - Add PM package disposition events to scoped event identity with body reference/hash and batch/generation fields.
   - Duplicate role-output ledger entries should close waits only when they are the same current scoped identity, not when they are stale or mismatched.

6. Close break-glass through the existing incident/patch lifecycle.
   - Add a validation/final-disposition update path for patch records.
   - FlowGuard should continue to flag any patch with completed validation evidence but no final disposition.

## Risks / Trade-offs

- [Risk] Touching multiple existing owners can over-broaden the patch. Mitigation: implement only identity/fold checks at existing helper boundaries and avoid broad module restructuring.
- [Risk] Parallel AI work may change the same files. Mitigation: inspect diffs before edits, preserve existing partial fixes, and stage only owned files if a local git sync is possible.
- [Risk] Background checks can be mistaken for pass evidence. Mitigation: use `tmp/flowguard_background/` artifacts and inspect exit/meta files before claiming completion.
- [Risk] Installed skill sync can race source changes. Mitigation: run install sync only after source validation, then run audit/check sequentially.

## Validation Plan

- Focused syntax and runtime tests for changed helpers.
- FlowGuard checks for control-plane friction, repair transaction, PM package absorption, role-output runtime/idempotency, controller break-glass, control transaction registry, and model-test alignment.
- Background Meta/Capability and router-tier checks when practical, using the documented `tmp/flowguard_background/` contract.
- Local install sync, install audit, install check, and final git status.
