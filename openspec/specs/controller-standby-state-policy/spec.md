# controller-standby-state-policy Specification

## Purpose
TBD - created by archiving change prune-controller-standby-state-policy. Update Purpose after archive.
## Requirements
### Requirement: Standby state policy is centralized and stable

FlowPilot SHALL derive foreground Controller standby state, foreground mode,
return permission, patrol requirement, and final-answer preflight from a single
internal state-policy boundary while preserving existing public payload fields.

#### Scenario: Current state names remain stable

- **WHEN** standby observes terminal, user input, daemon liveness, Controller
  action ready, wait-target blocker, wait-target reissue, wait-target check,
  waiting-for-role, or daemon-live-no-action conditions
- **THEN** the returned `standby_state` uses the same state name as before the
  pruning refactor.

#### Scenario: State policy preserves Controller mode

- **WHEN** a standby state maps to a Controller duty
- **THEN** `foreground_required_mode` matches the existing duty for that state
  and does not use chat history or sealed body content as authority.

#### Scenario: State policy preserves stop preflight

- **WHEN** the run is not terminal or a Controller duty remains active
- **THEN** final-answer preflight remains false and names the blocking reason.
