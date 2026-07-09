## ADDED Requirements

### Requirement: Fake AI Replays Exercise Global Context Failure And Repair
FlowPilot SHALL include fake-AI replay or model scenarios that exercise missing
global standard context, low-standard planning packages, empty existing fields,
and legal corrected retries through current runtime paths.

#### Scenario: Missing global context blocks before completion claim
- **WHEN** a fake-AI route produces a node plan, worker result, or review
  package that omits recoverable user/PM standard references
- **THEN** the replay or model SHALL show the route blocked by current review,
  FlowGuard, or PM repair behavior before terminal completion.

#### Scenario: Empty existing field is mechanically rejected
- **WHEN** a fake-AI result omits or empties a field that the current contract
  declares required and non-empty
- **THEN** runtime contract projection SHALL reject the result mechanically and
  return packet-local correction information for a legal retry.

#### Scenario: Corrected retry follows current runtime path
- **WHEN** the fake-AI package is retried with the current required fields and
  recoverable global standard references
- **THEN** the replay or model SHALL advance through the legal current-runtime
  path without old-field aliases, defaults, or compatibility fallback.
