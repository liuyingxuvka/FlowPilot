## MODIFIED Requirements

### Requirement: Active prompts use current role binding language

FlowPilot active prompts SHALL describe role work in terms of the current runtime-requested role binding and SHALL avoid carrying historical fixed-runtime roles, old Router, Process/Product-scope FlowGuard operator, Validator, or Closure Officer wording as active instruction.

#### Scenario: Lease prompt names current requested role
- **WHEN** an active Controller, PM, reviewer, FlowGuard operator, worker, startup, or resume prompt describes role setup
- **THEN** it uses current-rule wording such as requested responsibility, requested role, role binding, addressable id, host-supported role mechanism, or runtime-provided responsibility
- **AND** it does not instruct the agent to create or recover roles that are not required by the current runtime action.

#### Scenario: Historical topology wording stays out of active authority
- **WHEN** a prompt is delivered as active runtime authority
- **THEN** it MUST NOT present historical fixed-count runtime roles language, Process/Product-scope FlowGuard operator language, Validator/Closure Officer role language, or old Router daemon control paths as a current startup, resume, or route-work requirement.
