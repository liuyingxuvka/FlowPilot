## Why

FlowPilot already has several blocker paths, but their recovery rules are split
between router keyword classification, phase-specific PM cards, reviewer block
flows, startup repair, and self-interrogation gates. This makes it easy for a
blocker to stop the route without a uniform explanation of who handles the first
repair attempt, when the issue escalates to PM, and where the route must return
for recheck.

## What Changes

- Introduce a run-visible `blocker_repair_policy` table that maps blocker
  families to first handlers, direct retry budgets, PM escalation, PM recovery
  options, return-gate rules, and hard-stop conditions.
- Keep Router responsible for triage and delivery only: Router may send
  mechanical control-plane reissue blockers to the original responsible role
  within the configured retry budget, and must escalate to PM when the budget is
  exhausted or the blocker requires semantic judgment.
- Make PM the recovery authority after escalation. PM may repair in place,
  roll back to an earlier gate, add a supplemental node, create a repair node,
  mutate the route, quarantine stale evidence, record a bounded waiver, or stop
  for the user, but may not silently mark the blocked gate as passed.
- Make self-interrogation/grill-me blockers first-class PM-recovery blockers:
  missing or dirty records require PM to re-run/record interrogation, turn
  findings into repair work, record a justified waiver when allowed, or change
  the route.
- Persist retry attempts and policy-row metadata in control-blocker artifacts so
  PM, Controller, and future resumes can see why the blocker was delivered to
  its target and why it escalated.

## Capabilities

### New Capabilities

- `blocker-repair-policy`: Defines the unified blocker policy table, router
  first-handler routing, retry-budget escalation, PM recovery options, and
  return-gate requirements.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/runtime_kit/cards/roles/controller.md`
- `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
- PM phase cards for repair, startup, model-miss triage, final ledger, closure,
  and self-interrogation-bearing phases
- `templates/flowpilot/` control-blocker and policy templates
- `simulations/meta_model.py`, `simulations/capability_model.py`, and their
  runners/results
- Router runtime tests and OpenSpec validation artifacts
