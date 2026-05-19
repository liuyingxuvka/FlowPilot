## Context

FlowPilot already uses a Router daemon, Controller action ledger, foreground
standby row, and patrol timer to keep the foreground Controller attached while
the daemon owns progress. The recent failure mode shows a remaining ambiguity:
a nonterminal status projection can say the foreground turn may return while
`continuous_controller_standby` is still waiting. A Controller can then read the
projection as permission to final-answer even though the ledger still requires
patrol.

The repository already contains relevant surfaces:

- `flowpilot_router_controller_scheduler_standby.py` builds standby snapshots
  and patrol timer results.
- `flowpilot_router_route_frontier_status_summary.py` builds
  `current_status_summary.json`.
- Controller prompt/card assets explain the standby and patrol contract.
- `flowpilot_controller_patrol_model.py` and focused runtime tests cover the
  patrol loop.

## Goals / Non-Goals

**Goals:**

- Make `controller_stop_allowed=true` the only normal authority to end the
  foreground Controller role.
- Preserve useful user status returns without letting them imply Controller
  shutdown.
- Make status summaries explicitly display-only, with source/freshness metadata
  for `next_step` projections.
- Add a known-bad model/runtime case where stale/completed display projection
  plus nonterminal return permission cannot end standby.
- Sync the validated repository source to the local installed FlowPilot skill.

**Non-Goals:**

- Do not restart or redesign the Router daemon.
- Do not add a second Router writer or separate monitor.
- Do not change sealed packet/result body boundaries.
- Do not push to GitHub or publish a release.

## Decisions

1. **Keep old fields compatible but add clearer fields.**

   Runtime payloads will retain `foreground_turn_return_allowed` for existing
   readers, but will add `user_status_update_allowed` and
   `controller_patrol_required`. The legacy field remains informational only;
   the stop gate is `controller_stop_allowed`.

   Alternative considered: remove `foreground_turn_return_allowed`. That is too
   risky because installed prompt/code surfaces may still read it.

2. **Ledger and terminal gate outrank display projections.**

   Status summaries will include a projection authority block that states the
   summary is display-only, names the Controller action ledger as the control
   source, and marks whether `next_step` points at a pending executable action
   or only at stale/no-control display information.

   Alternative considered: make status summary drive Controller decisions after
   extra validation. That would preserve the ambiguity and duplicate ledger
   authority.

3. **Final-answer preflight is explicit in code payloads and prompts.**

   Controller-facing outputs will name the preflight: terminal state,
   `controller_stop_allowed=true`, no waiting/in-progress
   `continuous_controller_standby`, and no pending Controller work. Nonterminal
   user returns are treated as status updates or repair duties, not final
   closure.

   Alternative considered: prompt-only wording. This is insufficient because
   stale projection data can still be machine-read as permission.

4. **Focused FlowGuard first, broad checks in background.**

   The focused patrol model will cover the new hazard directly. Heavy meta and
   capability checks may run through the repository's background log contract
   after targeted checks pass.

## Risks / Trade-offs

- **Legacy field confusion remains visible** -> Mitigate by marking
  `foreground_turn_return_allowed` as informational and pairing it with
  stronger `user_status_update_allowed`, `controller_stop_allowed=false`, and
  `controller_patrol_required=true`.
- **Status summaries become more verbose** -> Mitigate by keeping new metadata
  compact and machine-readable.
- **Prompt text can drift from runtime behavior** -> Mitigate with tests and
  install checks that look for the new stop-preflight language on key surfaces.
- **Parallel agents may edit nearby files** -> Mitigate by keeping this change
  scoped to Controller standby/status/prompt/model/test files and checking git
  state before final sync.

## Migration Plan

1. Add OpenSpec deltas and focused FlowGuard model obligations.
2. Update runtime payloads and prompt surfaces.
3. Add focused runtime tests for nonterminal user return versus stop permission
   and stale/completed `next_step` projection.
4. Run focused FlowGuard and runtime checks.
5. Start heavy meta/capability regressions in the background log directory and
   inspect final artifacts.
6. Sync the local installed FlowPilot skill from the validated repository source
   and run install audit/check.
