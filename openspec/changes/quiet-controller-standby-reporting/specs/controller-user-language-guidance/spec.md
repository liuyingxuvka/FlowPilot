## ADDED Requirements

### Requirement: Controller decides whether to speak before translating wording
Before translating internal terms into plain language, the Controller SHALL first decide whether the information belongs in a user-visible message under the reporting budget.

#### Scenario: Internal action has no user-facing value
- **WHEN** a Controller action only updates internal FlowPilot control state and does not require user action or report a meaningful state change
- **THEN** Controller keeps it out of user-visible chat even if it could be translated into plain language.

#### Scenario: User-visible action uses plain language
- **WHEN** a Controller action is allowed by the reporting budget to be shown to the user
- **THEN** Controller explains it in plain language first and avoids internal action, ledger, packet, ACK, hash, contract, or diagnostic terms unless requested or needed for a concrete blocker.
