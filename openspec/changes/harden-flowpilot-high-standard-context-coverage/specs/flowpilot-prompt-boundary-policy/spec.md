## ADDED Requirements

### Requirement: Prompt Context Uses Current Global Standard References
FlowPilot SHALL require PM-authored planning and node-context prompt cards to
carry the user's original standard and PM's high-standard execution intent
through existing current-contract reference fields rather than chat memory,
local-only task prose, fallback defaults, or new compatibility fields.

#### Scenario: PM node context includes global standard references
- **WHEN** PM prepares a node acceptance plan or worker-facing node context
- **THEN** the prompt SHALL require existing fields such as
  `relevant_references`, `acceptance_criteria`, `known_risks`, and acceptance
  item projection to cite the current root/user contract, product architecture,
  high-standard contract, acceptance item registry, route node, material
  evidence, risks, and verification intent.

#### Scenario: Local-only packet context is insufficient
- **WHEN** a prompt or card can be satisfied by local task prose without a
  recoverable user/PM standard
- **THEN** prompt validation SHALL require the card to make that package
  blocker-worthy for Reviewer or PM repair using existing blocker fields.

#### Scenario: Runtime remains mechanical
- **WHEN** a packet or result includes all current required fields but the
  substantive plan appears low-standard or source-intent diluted
- **THEN** runtime SHALL NOT add semantic scoring or fallback interpretation
- **AND** Reviewer, FlowGuard, or PM review SHALL own the substantive challenge
  through existing review, blocker, repair, or suggestion fields.
