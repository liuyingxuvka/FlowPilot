## Context

Formal startup now requires the built-in Router daemon before Controller core loads. The daemon writes `runtime/router_daemon_status.json` and `runtime/controller_action_ledger.json`, and roles return ACKs and formal outputs directly through Router-directed runtime paths. A remaining failure mode is user-visible: when the daemon is alive but waiting for a role, the foreground Controller can report the wait and end the turn. That leaves the user seeing a stopped Controller even though Router is still ticking.

## Goals / Non-Goals

**Goals:**

- Add a foreground standby loop that keeps Controller attached to the live Router daemon while the daemon waits for roles or future Controller actions.
- Keep standby read-only with respect to Router progress: it may poll daemon status and ledger files, but it must not call `next` or `run-until-wait`.
- Return from standby only when there is a real Controller action, terminal state, user-needed state, daemon failure, stale/missing daemon lock, or an explicit bounded timeout.
- Make the standby contract visible in Controller-facing prompts and executable checks.

**Non-Goals:**

- Do not replace the Router daemon with a foreground loop.
- Do not make Controller author PM/reviewer/worker outputs or route decisions.
- Do not reintroduce heartbeat automation as the normal foreground wait mechanism.
- Do not make `next` or `run-until-wait` the normal runtime metronome.

## Decisions

1. **Add a bounded foreground standby command.**
   - Decision: add a CLI/runtime command that polls daemon status and the Controller action ledger until a wake condition is present.
   - Rationale: the host conversation needs an active blocking operation to avoid ending while Router waits for role output.
   - Alternative considered: rely on heartbeat/manual resume. Rejected because the user-visible Controller still stops and must be pulled back later.

2. **Poll daemon artifacts instead of computing Router progress.**
   - Decision: the foreground wait reads `router_daemon.lock`, `router_daemon_status.json`, and `controller_action_ledger.json`; it does not call `compute_controller_action`, `next`, or `run-until-wait`.
   - Rationale: Router daemon remains the single normal progress owner.
   - Alternative considered: let Controller run a folded router loop. Rejected because it recreates the manual-metronome path the daemon replaced.

3. **Classify role waits as standby, not completion.**
   - Decision: `waiting_for_role` while the daemon lock is live is a foreground standby state. It is not a final answer and not a controlled stop.
   - Rationale: live role waits are expected long-running work, not task completion.

4. **Keep waits bounded at the command layer.**
   - Decision: the command accepts a maximum wait duration for tests and host safety, while the Controller prompt treats ordinary live waits as a reason to call the standby command again rather than end the FlowPilot run.
   - Rationale: host/tool environments can have hard execution limits; a bounded command is testable and can be chained by foreground Controller without changing Router state.

## Risks / Trade-offs

- Long waits can still hit host-level execution limits -> Keep the command bounded, report `timeout_still_waiting`, and instruct Controller to re-enter standby rather than call `next`.
- Daemon status can be stale or lock can disappear -> Exit standby with `daemon_stale_or_missing` so Controller can use the existing repair path.
- A role may submit invalid output -> Router daemon continues to own validation and blocker routing; standby only observes the resulting status/action.
- Foreground polling could be mistaken for Router progress -> Model and tests assert no diagnostic router metronome command is used during standby.
