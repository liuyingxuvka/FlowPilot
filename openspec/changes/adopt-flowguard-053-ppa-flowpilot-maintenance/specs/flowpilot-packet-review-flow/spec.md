## ADDED Requirements

### Requirement: Packet Review Does Not Accept Unreviewed Field Expansion
FlowPilot packet and result review paths SHALL NOT accept PM-visible summary,
authorized-read, or similar field surfaces as complete current contract changes
until field lifecycle and PPA evidence prove they are canonical.

#### Scenario: Field-heavy packet review change is unfinished
- **WHEN** a packet-review change introduces or preserves `recent_role_report_summary`, `authorized_result_reads`, or a similar field/path surface
- **THEN** the change SHALL remain incomplete until field lifecycle, PPA, negative tests, and model-test alignment evidence are current.

#### Scenario: Summary metadata is present
- **WHEN** PM receives navigation or summary metadata from a role result
- **THEN** packet review SHALL NOT treat that metadata as a formal substitute for required packet/result body evidence, opened-body receipts, or Reviewer/FlowGuard semantic judgement.
