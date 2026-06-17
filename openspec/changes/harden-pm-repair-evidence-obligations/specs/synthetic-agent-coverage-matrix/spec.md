## ADDED Requirements

### Requirement: Synthetic matrix covers PM repair obligation failure shapes
FlowPilot SHALL include synthetic or focused runtime coverage for finite PM
repair obligation failure shapes.

#### Scenario: Reason-only fake PM output is covered
- **WHEN** the synthetic agent coverage matrix is generated
- **THEN** it MUST include a row for a fake PM repair result that submits
  `decision` and `reason` without required `repair_obligation_disposition`
- **AND** the row MUST identify the expected runtime reaction as mechanical
  contract rejection.

#### Scenario: Old and unsupported PM repair obligation fields are covered
- **WHEN** the synthetic agent coverage matrix is generated
- **THEN** it MUST include rows for summary-only, old-alias, unknown-obligation,
  duplicate-obligation, stale-obligation, and registry-only PM repair payloads
- **AND** each row MUST cite a current evidence owner or mark the row as a gap.

#### Scenario: Synthetic coverage remains non-live
- **WHEN** a PM repair obligation failure row is backed by fake AI or synthetic
  trace evidence
- **THEN** FlowPilot MUST classify that row as control-flow evidence only
- **AND** it MUST NOT treat the row as live project completion evidence.

#### Scenario: Partial authorized-body read fake output is covered
- **WHEN** the synthetic agent coverage matrix is generated
- **THEN** it MUST include rows for fake PM, repair worker, Reviewer, or
  FlowGuard outputs that act from summaries or only one delivered body while
  required blocker/target/upstream bodies remain unread
- **AND** each row MUST identify the expected runtime reaction as missing
  required body-read receipt or downstream semantic-consumption rejection.
