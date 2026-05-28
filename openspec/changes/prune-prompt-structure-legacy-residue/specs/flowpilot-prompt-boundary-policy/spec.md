## ADDED Requirements

### Requirement: Active Prompt Surfaces Reject Retired Control Paths
FlowPilot active prompt and card surfaces SHALL NOT instruct a role to use a
retired recovery layer, watchdog, direct role dispatch, chat-body return,
ACK-as-completion, or memory/chat-history authority as the current control path.

#### Scenario: Retired path appears only as rejected evidence
- **WHEN** an active prompt, card, or runtime prompt-policy asset mentions a retired control path
- **THEN** the text SHALL mark that path as retired, rejected, historical, compatibility-only, or test-only evidence

#### Scenario: Current authority is explicit
- **WHEN** a role is told how to proceed, return output, or determine next action
- **THEN** the text SHALL identify the Router-directed runtime path, FlowGuard-backed gate, run-scoped artifact, or current owner contract as the active authority

### Requirement: Prompt Residue Cleanup Is Focused
FlowPilot prompt cleanup SHALL preserve domain-specific role instructions while
removing or clarifying only wording that conflicts with current FlowGuard-kernel
control boundaries.

#### Scenario: Role-specific instruction is compatible
- **WHEN** a prompt contains role-specific guidance that does not contradict current control ownership
- **THEN** cleanup SHALL leave that guidance intact

#### Scenario: Old wording contradicts current ownership
- **WHEN** a prompt grants completion, dispatch, repair, or body-access authority to a retired or wrong owner
- **THEN** cleanup SHALL revise the wording before installed-skill synchronization is claimed
