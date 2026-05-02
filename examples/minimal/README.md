# Minimal FlowPilot Example

This example shows the smallest useful FlowPilot adoption shape for a target
software task.

## User Request

Implement a small retry-safe background job and prove it cannot complete before
its side effect is recorded.

## FlowPilot Startup

1. Enable FlowPilot by default.
2. Offer run-mode selection and record the selected mode or fallback reason.
3. Run self-interrogation:
   - What must be true before completion?
   - What state can drift?
   - What side effects must be idempotent?
   - What verification proves the contract?
4. Create or restore the six-agent crew and have the project manager write
   `.flowpilot/product_function_architecture.json` before contract freeze:
   user tasks, product capabilities, feature decisions, display rationale,
   missing-feature review, negative scope, and functional acceptance matrix.
   Six live background subagents are the default startup target where the host
   permits them. If authorization is missing or startup fails, pause and ask;
   use memory-seeded single-agent role continuity only after explicit fallback
   approval.
5. Have the product FlowGuard officer approve modelability and the human-like
   reviewer challenge usefulness.
6. Freeze the contract in `.flowpilot/contract.md` from the approved
   product-function architecture.
7. Copy `templates/flowpilot/` into the target project as `.flowpilot/`.
8. Fill `state.json`, `capabilities.json`, and `routes/route-001/flow.json`.
9. Record a dependency plan and install only the minimum tools needed for the
   current model/check step.
10. Defer future implementation, native-build, and packaging dependencies until
   their route node or verification command is active.
11. Build a task-local FlowGuard model under `.flowpilot/task-models/`.
12. Run route and task-model checks.
13. Run the startup activation guard:

   ```powershell
   python scripts/flowpilot_startup_guard.py --root . --route-id route-001 --record-pass --json
   ```

14. Execute only the first bounded chunk whose verification is declared.

## Expected Evidence

- `.flowpilot/state.json` points to the active node.
- `.flowpilot/startup_guard/latest.json` records a startup hard-gate pass.
- `.flowpilot/product_function_architecture.json` records the pre-contract PM
  product design gate.
- `.flowpilot/capabilities.json` records required gates.
- `.flowpilot/routes/route-001/flow.json` records allowed transitions.
- `.flowpilot/task-models/` contains the retry/idempotency model.
- `.flowpilot/checkpoints/` records verified milestones.
- Final report lists passed checks and skipped checks with reasons.

## Not Included

This example does not include runnable target application code. It is an
adoption pattern for applying the skill to a real target repository.
