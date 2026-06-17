# end-to-end-synthetic-agent-chaos-replay Spec Delta

## ADDED Requirements

### Requirement: Fake e2e replay must cover FlowGuard artifact contradiction

The fake AI end-to-end rehearsal SHALL include a chaos mode where the FlowGuard result body claims pass while the formal packet-owned FlowGuard evidence artifact reports a hard blocker.

#### Scenario: Fake AI artifact contradiction is reissued and completes

- **GIVEN** fake e2e runs with artifact consistency faults enabled
- **WHEN** the first FlowGuard post-result report body claims pass but its artifact reports `missing_code_contract`
- **THEN** FlowPilot mechanically blocks that result
- **AND** reissues the needed packet path
- **AND** the corrected run can still complete
