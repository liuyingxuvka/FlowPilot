## ADDED Requirements

### Requirement: Closure maintenance finishes with synchronized local evidence

Repository maintenance for FlowPilot runtime closure SHALL finish with
FlowGuard adoption evidence, local install freshness, OpenSpec validation, and
local git commit evidence before claiming the pass complete.

#### Scenario: Maintenance pass completes
- **WHEN** all implementation and validation tasks for this maintenance pass
  are complete
- **THEN** the final evidence includes FlowGuard adoption log updates, strict
  OpenSpec validation, install sync/check/audit pass status, and a local git
  commit containing the completed changes.

#### Scenario: Publication remains separate
- **WHEN** the maintenance pass commits locally
- **THEN** it does not push, tag, publish, or create a release unless the user
  explicitly authorizes that separate action.
