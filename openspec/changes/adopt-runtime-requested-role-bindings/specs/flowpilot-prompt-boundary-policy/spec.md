## ADDED Requirements

### Requirement: Active prompts use current role binding language
FlowPilot active prompts SHALL describe role work in terms of the current
runtime-requested role binding and SHALL avoid carrying historical fixed-crew
wording as active instruction.

#### Scenario: Lease prompt names current requested role
- **WHEN** an active Controller, PM, reviewer, officer, worker, startup, or
  resume prompt describes role setup
- **THEN** it uses current-rule wording such as requested role, role binding,
  addressable id, or host-supported role mechanism
- **AND** it does not instruct the agent to create or recover roles that are not
  required by the current runtime action

#### Scenario: Prompt avoids host mechanism explanations
- **WHEN** an active prompt tells Controller how to satisfy a requested role
  binding
- **THEN** it does not need to explain the host mechanism's concrete form
- **AND** it still requires runtime-visible binding evidence before claiming the
  role is available

#### Scenario: Historical fixed-crew wording stays out of active authority
- **WHEN** a prompt is delivered as active runtime authority
- **THEN** it MUST NOT present historical fixed-count crew language as a
  current startup, resume, or route-work requirement
