## 1. Policy Artifacts

- [x] 1.1 Add a `blocker_repair_policy` template with first handler, retry budget, escalation, PM recovery options, return policy, and hard-stop fields.
- [x] 1.2 Include blocker policy snapshot locations in run/control-block templates and documentation.

## 2. FlowGuard Model Updates

- [x] 2.1 Update the meta model to represent blocker first-handler routing, retry-budget exhaustion, PM recovery choices, and hard-stop outcomes.
- [x] 2.2 Update the capability model to cover self-interrogation PM recovery and policy-visible blocker handling.
- [x] 2.3 Rerun the relevant FlowGuard checks and inspect stable background artifacts before reporting success.

## 3. Router Runtime

- [x] 3.1 Add policy-row definitions and helper functions to attach policy metadata to new control blockers.
- [x] 3.2 Track direct repair attempt counts and escalate exhausted non-PM first-handler blockers to PM.
- [x] 3.3 Materialize self-interrogation gate failures as PM-handled control blockers with return-gate metadata.
- [x] 3.4 Validate PM control-blocker recovery decisions against allowed recovery options, return policy, and hard-stop conditions.

## 4. Cards And Templates

- [x] 4.1 Update PM and Controller role cards to follow the policy row, retry budget, escalation, and PM recovery rules.
- [x] 4.2 Update PM phase cards for review repair, model-miss triage, startup activation, final ledger, closure, and self-interrogation-bearing phases.
- [x] 4.3 Update template README and control-block examples to explain the unified blocker repair policy.

## 5. Verification And Installation

- [x] 5.1 Add runtime tests for mechanical retry, retry escalation to PM, self-interrogation blocker delivery, PM recovery validation, and hard-stop waiver rejection.
- [x] 5.2 Run focused router/card tests plus OpenSpec validation.
- [x] 5.3 Synchronize the local installed FlowPilot skill and run install/audit checks.
