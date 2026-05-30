## ADDED Requirements

### Requirement: Prompt boundaries avoid old topology instructions
FlowPilot prompt-boundary policy SHALL ensure current role-facing and
Controller-facing prompt surfaces use clean runtime role-binding vocabulary and
do not teach old topology or unsupported historical paths as current authority.

#### Scenario: Shared prompt policy uses current vocabulary
- **WHEN** shared prompt-policy text is inserted into a system card, role card,
  phase card, event card, or packet prompt
- **THEN** it describes return paths, runtime context, and next-step authority
  with Router, role-binding, active-holder, and output-contract language
- **AND** it does not describe runtime role assistance, sidecar roles, fixed crew, old
  router commands, or unsupported historical aliases as current instruction

#### Scenario: Repair prompts do not advertise old repair routes
- **WHEN** a repair, resume, or break-glass prompt needs to mention stale
  context
- **THEN** it frames stale context as unsupported current authority or
  superseded evidence
- **AND** it does not present unsupported-run inspection or diagnostic router repair as a
  normal FlowPilot operating mode
