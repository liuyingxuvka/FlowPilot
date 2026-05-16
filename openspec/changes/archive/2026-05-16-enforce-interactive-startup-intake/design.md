## Context

Formal FlowPilot startup now opens a native WPF intake window and passes only result/envelope/receipt paths back to Router. The result validator checks schema, body secrecy, hash consistency, and enum values, but it does not distinguish a real user-operated window from the headless helper used by tests. That allowed a formal run to continue after a scripted `HeadlessConfirmText` result.

This is a stateful startup boundary: accepting the result records startup answers, seeds the run, and schedules role and heartbeat work. The repair must therefore be enforced in Router validation, not only in the prompt.

## Goals / Non-Goals

**Goals:**

- Make formal startup reject headless or synthesized startup intake results.
- Keep headless output available for tests and diagnostics with explicit non-formal metadata.
- Preserve sealed-body behavior: Controller still receives paths, hashes, answers, and status only.
- Strengthen the FlowGuard startup intake model so the bypass class is represented as a known-bad hazard.
- Sync the installed skill after repo-owned source changes.

**Non-Goals:**

- Remove the headless helper entirely.
- Change the startup UI layout or user-facing copy beyond provenance metadata.
- Run the heavyweight Meta and Capability simulations for this change.
- Alter old run history or reuse old run state as current evidence.

## Decisions

1. Require formal provenance fields in result, receipt, and envelope.

   `startup_intake_result.json`, `startup_intake_receipt.json`, and `startup_intake_envelope.json` will carry `launch_mode`, `headless`, and `formal_startup_allowed`. Interactive UI output uses `interactive_native`, `false`, and `true`; headless output uses `headless`, `true`, and `false`.

   Alternative considered: infer provenance from the PowerShell command line. That is weaker because Router validates persisted artifacts after the UI process has exited and should not trust transient command history.

2. Put the hard gate in `_validate_startup_intake_result_payload`.

   Router is the first component that turns UI output into startup answers and run side effects. Rejecting there prevents both direct bootloader apply and daemon Controller receipt paths from accepting a bypass.

   Alternative considered: only update `SKILL.md`. That would reduce future model error but would not protect against another agent, script, or test fixture producing the wrong artifact.

3. Keep headless tests explicit.

   Existing encoding and installed-skill smoke tests can continue to use `HeadlessConfirmText`, but their artifacts must identify themselves as headless. Runtime tests that simulate formal startup should use interactive provenance metadata in their fixtures.

   Alternative considered: remove `HeadlessConfirmText`. That would make smoke and encoding coverage slower and harder to run on CI-like hosts.

## Risks / Trade-offs

- Existing fixtures without new provenance fields may fail → Update formal startup fixtures to write the interactive fields.
- Headless smoke tests may look like failures if they feed Router → Add a dedicated rejection test so the intended separation is clear.
- A real UI crash before result creation will now block startup → This is intended; formal startup must report UI failure rather than silently continuing.
- The model can overstate confidence if it lacks the headless branch → Add a concrete `headless_result_accepted` hazard and invariant to the startup intake model.

## Migration Plan

1. Update script metadata and Router validation.
2. Update runtime fixtures and add headless rejection coverage.
3. Update prompt guidance.
4. Run focused startup intake model and pytest coverage.
5. Sync installed FlowPilot skill and run install/audit checks.
6. Keep Meta and Capability simulations deferred for this change per user instruction.

## Open Questions

None. The user explicitly approved making formal startup unable to bypass the native UI.
