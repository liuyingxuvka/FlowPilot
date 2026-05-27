## Context

`flowpilot_router_controller_scheduler_standby.py` currently computes a
standby state, then repeats knowledge about that state when deriving foreground
mode, turn-return permission, patrol flags, stop preflight, and patrol-timer
instructions. The behavior is well covered by the existing
`flowpilot_controller_patrol` FlowGuard model and focused foreground Controller
runtime tests.

The user goal is branch pruning for maintainability and lower bug risk, not
file splitting. This change therefore keeps the current module and public
entrypoints while moving repeated state-policy decisions behind internal helper
functions.

## Goals / Non-Goals

**Goals:**

- Represent standby state selection as one explicit internal classifier.
- Represent derived foreground mode and permission flags as one explicit
  state-policy layer.
- Keep all current JSON fields and state names compatible.
- Keep Controller stop authority anchored in terminal status and the Controller
  action ledger.
- Validate with the existing FlowGuard patrol model and focused runtime tests.

**Non-Goals:**

- Do not change the daemon monitor, lock ownership, or Controller action
  ledger authority.
- Do not split the standby module.
- Do not merge distinct business states such as blocker, reissue, liveness,
  user input, terminal, and pending Controller work.
- Do not use patrol timer or standby as a new Router progress driver.

## Decisions

### Decision 1: Introduce internal standby policy helpers

The implementation will add private helpers that classify standby state and map
that state to foreground mode. The existing public functions will call the
helpers and continue returning the same payload fields.

Alternative considered: keep the inline if/elif chains. Rejected because the
same state knowledge is already repeated in several places, which makes future
fixes error-prone.

### Decision 2: Keep state names as the observable contract

The helpers will not collapse state names. They only centralize the mapping so
that `wait_target_blocker_required`, `wait_target_reissue_required`,
`wait_target_check_due`, `controller_action_ready`, `user_input_required`,
`daemon_liveness_check_required`, `waiting_for_role`,
`daemon_alive_no_controller_action`, and `terminal` remain visible outcomes.

Alternative considered: collapse all wait-target states into one generic
`wait_target_action_ready`. Rejected because blocker, reissue, and check modes
drive different Controller actions.

### Decision 3: Use existing FlowGuard model before extending it

The first pass will reuse `flowpilot_controller_patrol_model.py` and
`run_flowpilot_controller_patrol_checks.py`. If validation shows a missing
state-policy case, the model should be extended before any broader contraction.

Alternative considered: create a new model immediately. Rejected because the
existing patrol model already owns the standby safety contract.

## Risks / Trade-offs

- Incorrect mode mapping -> mitigated by focused runtime tests for every
  Controller-visible standby return class.
- Stop authority accidentally loosened -> mitigated by final-answer preflight
  tests and FlowGuard patrol known-bad checks.
- Hidden Router progress driver -> mitigated by tests that standby does not
  call normal Router progress commands.
- Over-pruning business states -> mitigated by preserving state names and only
  centralizing repeated mapping.

## Migration Plan

1. Add OpenSpec and FlowGuard grounding for standby-state policy pruning.
2. Add or update source-level tests for the internal policy helpers where
   useful.
3. Refactor only the standby state/mode/permission mapping.
4. Run the Controller patrol FlowGuard model, foreground Controller focused
   runtime tests, structure checks, and install sync.
