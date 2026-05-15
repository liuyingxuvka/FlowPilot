## Context

Current FlowPilot startup creates the minimal run shell, current pointer, and run index before starting or attaching the one-second Router daemon. Runtime evidence from `run-20260515-163026` confirms the daemon starts before startup intake UI, role startup, heartbeat binding, and Controller-core handoff.

The remaining risk is prompt ambiguity. Some runtime-facing prompt text still says "return to the router", "continue the router loop", or "prefer run-until-wait". Those phrases are correct only before daemon takeover, in diagnostics/tests, or during explicit repair. After daemon takeover, normal progress must be daemon status plus Controller action ledger rows.

## Goals / Non-Goals

**Goals:**

- Make every affected prompt source state the same authority rule: after daemon startup, Controller processes exposed ledger rows, writes Controller receipts, and otherwise uses standby.
- Keep the two-table explanation plain: Router owns ordering, barriers, dependency metadata, and reconciliation; Controller owns row execution and receipts.
- Make `next`, `apply`, and `run-until-wait` diagnostic/test/explicit-repair tools after daemon takeover.
- Add a focused FlowGuard prompt-boundary check that rejects known-bad prompt states where Controller manually drives Router in daemon mode.
- Sync the installed FlowPilot skill after verification.

**Non-Goals:**

- Do not change daemon startup order.
- Do not fix duplicate Controller-row exposure after completed receipts.
- Do not change PM, Reviewer, Worker, officer, packet, or sealed-body authority.
- Do not run the heavyweight Meta or Capability simulations in this task.

## Decisions

1. **Keep current daemon startup order.**
   - Decision: leave `create_run_shell`, `write_current_pointer`, and `update_run_index` before `start_router_daemon`.
   - Rationale: the daemon needs a run root and target files for lock/status/ledger writes.
   - Alternative rejected: make daemon the literal first action. That would remove the durable target it needs to operate safely.

2. **Patch prompt sources, not runtime scheduling.**
   - Decision: update `SKILL.md`, Controller role card text, heartbeat template text, and generated prompt strings in `flowpilot_router.py`.
   - Rationale: the user scoped this task to prompt ambiguity; another agent owns the non-prompt repeated-row issue.

3. **Use one repeated wording pattern.**
   - Decision: replace broad router-loop wording with "attach to daemon status and Controller action ledger; process exposed rows; write receipts; standby when no row is executable".
   - Rationale: repeated phrasing lowers the chance that future prompt edits reintroduce a manual Router metronome.

4. **Model prompt authority directly.**
   - Decision: add or extend a small FlowGuard check focused on prompt states and allowed actions.
   - Rationale: static prompt coverage can pass while natural-language authority is still ambiguous. Known-bad variants must fail before implementation is treated as safe.

## Risks / Trade-offs

- [Risk] Prompt wording becomes too long and harder to read. -> Mitigation: keep Controller table text compact but explicit about command prohibition.
- [Risk] Removing broad router-loop language breaks pre-daemon bootloader guidance. -> Mitigation: preserve pre-daemon bootloader wording only for the minimal startup phase.
- [Risk] Heartbeat repair genuinely needs to restart a stale daemon. -> Mitigation: wording allows daemon repair/restart only when lock/status evidence says the daemon is missing or stale.
- [Risk] FlowGuard focuses on prompts and misses the separate repeated-row bug. -> Mitigation: mark repeated-row reconciliation explicitly out of scope for this change.
- [Risk] Peer agents edit nearby files concurrently. -> Mitigation: check git state before editing and before syncing/committing; keep edits narrow and do not revert unrelated changes.
