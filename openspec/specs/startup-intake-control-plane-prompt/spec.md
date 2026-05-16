# startup-intake-control-plane-prompt Specification

## Purpose
TBD - created by archiving change clarify-startup-intake-ledger-return. Update Purpose after archive.
## Requirements
### Requirement: Startup Intake Prompt Returns To Router Work Board
After the native startup intake UI closes, FlowPilot prompt text SHALL direct
Controller back to Router daemon status and the Controller action ledger rather
than telling Controller to directly apply the startup intake action.

#### Scenario: Startup UI closes under daemon-owned startup
- **WHEN** the startup intake instruction is shown after Router daemon startup
- **THEN** the instruction names Router daemon status and the Controller action ledger as the continuation authority
- **THEN** the instruction does not say to apply the pending action as the normal next step

### Requirement: Startup Intake Body Remains Sealed From Controller
The startup intake handoff SHALL continue to pass only controller-visible result
metadata and SHALL NOT instruct Controller to read, paste, or reconstruct the
user's work request body.

#### Scenario: Controller handles startup intake result
- **WHEN** Controller sees startup intake result metadata
- **THEN** prompt text preserves the rule that the user work request body is not pasted into chat or included in the Router payload
- **THEN** PM receives startup intake through the existing sealed `user_intake` path
