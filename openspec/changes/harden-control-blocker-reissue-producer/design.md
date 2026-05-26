## Context

The current repair transaction contract already says Router must reject empty waits, but the real run showed a gap in the `role_reissue` branch. PM selected same-gate repair with `repair_transaction.plan_kind=role_reissue`, `rerun_target=worker_scan_results_returned`, and no replacement packets or replayable operation. Router committed the transaction and exposed a wait for workers even though no fresh worker packet, mail, or Controller action could produce that event.

The fix stays inside the existing repair transaction and control-blocker wait machinery. It does not introduce a second repair system.

## Goals / Non-Goals

**Goals:**

- Make producer evidence mandatory before committing a role-produced follow-up wait.
- Preserve valid material rework paths: `packet_reissue`, `operation_replay`, `controller_repair_work_packet`, and true existing-event waits.
- Add model-miss evidence for the observed trace and a generalized no-producer wait.
- Keep Controller sealed-body boundaries unchanged.

**Non-Goals:**

- Do not read or summarize sealed worker result bodies in Controller.
- Do not add a broad new workflow for PM repair decisions.
- Do not change release, deployment, or stack choices.
- Do not modify the unrelated real-router dry-run rehearsal change currently in progress.

## Decisions

1. **Reject `role_reissue` unless it has producer evidence.**
   `role_reissue` is only valid when the repair request can prove fresh role work is already issued or will be issued by the committed transaction. For material-scan rework, that means using `packet_reissue` with replacement packets or an operation replay that creates the current-generation packet/result relay work.

2. **Keep `recovery_option` as policy context, not execution authority.**
   PM may still choose `same_gate_repair`, but the executable plan kind controls what Router does. Human-readable `repair_action` text cannot create a worker obligation.

3. **Record the miss in the model before trusting tests.**
   The FlowGuard update should classify the issue as an executable-boundary miss: a wait state was accepted without an event producer. The generalized case is any control-blocker repair that waits for a role event after commit without a packet, queued action, existing producer, or terminal/blocker outcome.

4. **Use tests to pin both rejection and valid repair.**
   Regression coverage should fail the observed bad `role_reissue` case and keep the known-good `packet_reissue` material repair path green.

## Risks / Trade-offs

- **Existing tests may have treated open-ended `role_reissue` as valid.** -> Update tests to reflect the stricter executable transaction contract rather than preserving the unsafe path.
- **PM cards may still suggest vague role reissue.** -> Runtime rejection protects the control plane; prompt/card wording can be tightened as a follow-up if needed.
- **Heavy model checks are slow.** -> Run focused model/tests first, then run heavier meta/capability checks in the background artifact contract and inspect completion artifacts before claiming them.

## Migration Plan

1. Add OpenSpec deltas and FlowGuard model-miss evidence.
2. Add focused tests that fail on the current no-producer `role_reissue` behavior.
3. Tighten repair transaction validation and wait action creation.
4. Run focused tests and model checks, then background heavy checks where practical.
5. Sync the repository-owned skill into the local installed FlowPilot copy and run install audit/check.

## Open Questions

- None for the implementation. A later UX/card cleanup may make PM guidance clearer, but the runtime guard is the required safety fix.
