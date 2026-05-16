## Why

FlowPilot can still waste foreground time after Controller relays a card or
packet because the host may keep waiting on a role response even when Router
state, direct ACKs, result envelopes, or `controller_next_action_notice.json`
already authorize the next step. This change makes Router-ready evidence
preempt stale role waits without weakening PM, reviewer, officer, or sealed-body
boundaries.

## What Changes

- Add a Controller rule that after any router-authored card, bundle, packet, or
  result relay, Controller must immediately return to Router status/`next`/
  `run-until-wait` unless the router explicitly requires a user, host, payload,
  card, packet, ledger, or role boundary.
- Treat direct Router ACKs, resolved return-ledger entries, active-holder
  next-action notices, and returned result envelopes as higher priority than
  foreground `wait_agent` or chat-response waiting.
- Limit bounded `wait_agent` use to explicit liveness/recovery checks requested
  by Router; timeout remains `timeout_unknown`, never proof that a role is
  active or that Controller should keep waiting.
- Add FlowGuard coverage for the bad state where a router-ready next action
  exists while Controller continues waiting on a role.
- Keep Controller envelope-only: no sealed packet/result body reads, no
  semantic approvals, no PM/reviewer/officer bypass.

## Capabilities

### New Capabilities

- `router-ready-preemption`: Controller foreground waiting must be preempted by
  router-ready state, direct Router ACK/result evidence, or active-holder
  next-action notices.

### Modified Capabilities

None.

## Impact

- Runtime/protocol guidance:
  - `skills/flowpilot/SKILL.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
  - `skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md`
  - `skills/flowpilot/references/protocol.md`
- Router/runtime behavior and tests:
  - `skills/flowpilot/assets/flowpilot_router.py`
  - `tests/test_flowpilot_router_runtime.py`
- FlowGuard models/checks:
  - `simulations/flowpilot_role_output_runtime_model.py`
  - `simulations/run_flowpilot_role_output_runtime_checks.py`
  - `simulations/flowpilot_control_plane_friction_model.py` if the wait
    reconciliation path needs broader state coverage.
- Local install sync and git:
  - `scripts/install_flowpilot.py --sync-repo-owned --json`
  - install audits/checks after sync
  - local git staging and commit only; no remote push.
