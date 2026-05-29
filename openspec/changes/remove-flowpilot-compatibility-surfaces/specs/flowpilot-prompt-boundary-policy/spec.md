## ADDED Requirements

### Requirement: Active Prompts Describe Only Current FlowPilot Paths
FlowPilot active prompts and runtime cards SHALL describe only current
FlowPilot startup, event, return, repair, and artifact-authority paths.

#### Scenario: Prompt instructs a role how to return work
- **WHEN** an active card or prompt tells a role how to proceed, return output,
  or choose a next action
- **THEN** the text identifies the current Router-provided event, current
  runtime artifact contract, or current FlowGuard-backed gate
- **AND** the text SHALL NOT offer compatibility aliases, legacy event names,
  direct chat-body returns, or deprecated repair flows as options

#### Scenario: Historical compatibility term is retained outside active prompts
- **WHEN** a historical term appears in archived evidence or negative tests
- **THEN** the surrounding text marks it as rejected, unsupported, or
  historical evidence
