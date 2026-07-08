## ADDED Requirements

### Requirement: Fake AI replay rejects old backend submissions at runtime ingress

FlowPilot SHALL replay fake backend agents that submit accepted, noncurrent, or
inactive-lease packet results and prove the real runtime rejects them before
result allocation.

#### Scenario: Fake backend repeats accepted packet
- **WHEN** a fake backend agent submits a result for a packet that already has
  an accepted result
- **THEN** replay MUST observe an ingress rejection
- **AND** replay MUST prove no new result row and no `packet.result_ids` append

#### Scenario: Fake backend submits old packet after next wait
- **WHEN** a fake backend agent submits an old packet result after a new
  current packet is waiting
- **THEN** replay MUST observe noncurrent-packet rejection
- **AND** replay MUST prove current packet state remains unchanged

### Requirement: Fake Reviewer replay preserves runtime semantic boundary

FlowPilot SHALL include fake Reviewer attempts that fail through mechanical
currentness or evidence gates, while explicitly preserving the rule that
runtime does not grade Reviewer prose semantics.

#### Scenario: Fake Reviewer lacks current open receipt
- **WHEN** a fake Reviewer submits a pass-shaped result without current
  authorized-read/open evidence for the accepted result
- **THEN** replay MUST reject or block the result mechanically
- **AND** the replay report MUST NOT describe the failure as runtime semantic
  text grading
