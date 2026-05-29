## ADDED Requirements

### Requirement: Fixed Value Prompt Fields Enumerate Allowed Values

FlowPilot SHALL make every prompt-controlled fixed-value command field self-contained by listing the allowed values at the point where an AI operator is expected to fill the field.

#### Scenario: Host kind is selected for a live role agent
- **WHEN** the runtime asks an operator to record a dynamic role lease with `flowpilot_new.py lease-agent`
- **THEN** the prompt guidance MUST list `--host-kind` allowed values `live`, `fake`, and `dry_run`
- **AND** it MUST state that a real Codex or multi-agent background worker uses `live`
- **AND** it MUST state that unlisted values such as `codex_subagent` MUST NOT be invented.

#### Scenario: No listed value fits
- **WHEN** an AI operator needs to fill a fixed-value command field and none of the listed values fits the real situation
- **THEN** the operator MUST stop and report the value-menu mismatch instead of guessing a new value.

#### Scenario: Runtime receives an invalid fixed value
- **WHEN** a caller passes an unlisted fixed value such as `--host-kind codex_subagent`
- **THEN** the formal command surface MUST reject the value rather than silently normalizing it.
