## Context

FlowPilot already has two related runtime surfaces:

- the Router daemon monitor, which automatically refreshes daemon status and
  Controller ledger projections;
- the foreground Controller standby path, which should keep the chat attached
  when no ordinary Controller row is ready.

The monitor is useful as the source of truth, but its automatic nature can make
the foreground Controller believe that a quiet board means "nothing to do" and
return a final answer. The repair is to keep the existing monitor automatic and
add an explicit Controller-operated timer wrapper that keeps the foreground
agent busy waiting for the next signal.

## Goals / Non-Goals

**Goals:**

- Add a named Controller patrol timer command with a concrete CLI invocation.
- Preserve the existing Router daemon monitor as the live status source.
- Make `continuous_controller_standby` an executable waiting loop, not a
  finishable checklist item.
- Put the exact patrol command and anti-exit purpose into the Controller role
  card, resume card, generated table prompt, and final standby row payload.
- Ensure `continue_patrol` tells Controller to rerun the command and wait for
  the next output.
- Validate the behavior with a focused FlowGuard model and runtime tests.

**Non-Goals:**

- Do not replace the Router daemon monitor or make it semi-automatic.
- Do not make Controller drive Router progress through `next`, `apply`, or
  `run-until-wait`.
- Do not add a second source of truth for daemon state.
- Do not run the heavyweight Meta and Capability models in this pass; the user
  explicitly approved skipping them because they are expensive.
- Do not revert or overwrite unrelated parallel-agent changes.

## Decisions

1. **Keep monitor and patrol timer separate**

   The Router daemon monitor remains automatic and writes the authoritative
   status/ledger view. The new patrol timer waits for the requested interval,
   reads that existing view, and returns a Controller-facing instruction.

   Alternative considered: make the monitor itself semi-automatic. Rejected
   because daemon liveness, role return visibility, and resume state would go
   stale whenever the foreground Controller is not actively pressing the
   monitor.

2. **Expose a concrete command**

   Add `controller-patrol-timer --seconds 10` to the existing
   `flowpilot_router.py` CLI. The generated prompts and standby row name this
   exact command so Controller does not have to invent a script or infer how to
   wait.

   Alternative considered: only instruct Controller to use
   `controller-standby --poll-seconds 10`. Rejected because the returned
   payload must include stronger anti-exit wording and loop instructions than a
   generic diagnostic standby snapshot.

3. **Return explicit patrol outcomes**

   The patrol command returns one of:

   - `continue_patrol`: no ordinary Controller work is ready; rerun the same
     command and wait for its next output.
   - `new_controller_work`: ready Controller action exists; read the action
     ledger and process rows top-to-bottom.
   - `terminal_return`: terminal state with `controller_stop_allowed=true`.
   - existing non-standby duty modes such as user input, daemon repair, wait
     target check, or blocker handling when the monitor requires them.

4. **Use layered prompt placement**

   The anti-exit instruction lives in four existing surfaces:

   - Controller role card: identity-level duty.
   - Controller resume/reentry card: recovery-level duty.
   - Generated `controller_table_prompt`: table-reading duty.
   - `continuous_controller_standby` row payload: action-level duty and exact
     command.

   This prevents a single missed prompt surface from allowing premature
   foreground exit.

5. **Model before implementation**

   Add a focused FlowGuard model for the patrol loop rather than extending the
   currently dirty daemon reconciliation model files. The model must make known
   bad cases fail: quiet monitor -> foreground exit, command started ->
   completion, and `continue_patrol` without "rerun and wait for next output."

## Risks / Trade-offs

- [Risk] The timer command duplicates too much standby logic. -> Mitigation:
  implement it as a thin wrapper over the existing standby snapshot/monitor
  projection and keep Router progress daemon-owned.
- [Risk] Controller treats "command started" as task completion. -> Mitigation:
  require prompt text, row payload, and command output to say that starting or
  restarting the command is not completion.
- [Risk] Tests pass prompt substrings while runtime behavior still exits. ->
  Mitigation: add runtime tests for the actual CLI/payload state transitions
  plus focused FlowGuard hazards.
- [Risk] Skipping Meta/Capability leaves broader route regressions undiscovered.
  -> Mitigation: record the skip explicitly, run focused model/runtime/install
  checks, and leave Meta/Capability as deferred heavy checks.

## Migration Plan

1. Add the focused OpenSpec and FlowGuard artifacts.
2. Implement the patrol timer CLI and payload generation.
3. Harden the four prompt surfaces.
4. Add focused tests and install sync checks.
5. Synchronize the local installed FlowPilot skill.
6. Record FlowGuard adoption notes, including skipped heavyweight models.

Rollback is narrow: remove the patrol CLI, prompt additions, and focused model
artifacts. The existing automatic monitor remains unchanged.
