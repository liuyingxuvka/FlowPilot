# synthetic-agent-trace-replay Spec Delta

## ADDED Requirements

### Requirement: Historical SkillGuard replay must reject body-pass artifact-block authority

Synthetic or historical replay coverage SHALL include the SkillGuard-exposed failure shape where a FlowGuard body claims pass while formal model evidence reports a hard blocker.

#### Scenario: Historical replay rejects non-authoritative FlowGuard pass

- **GIVEN** a replayed SkillGuard-style FlowGuard packet result
- **AND** the result body claims pass
- **AND** packet-owned hard evidence reports `missing_code_contract`
- **WHEN** the result is submitted through the real FlowPilot runtime gate
- **THEN** it is not authoritative pass evidence
- **AND** no Reviewer packet is released
