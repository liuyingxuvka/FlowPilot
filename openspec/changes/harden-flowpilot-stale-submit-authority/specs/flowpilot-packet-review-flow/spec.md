## ADDED Requirements

### Requirement: Accepted result pointer is authoritative for accepted packets

FlowPilot SHALL use `accepted_result_id` as the sole authoritative result for
an accepted packet. Historical `result_ids` ordering MUST NOT select or replace
the accepted result for review, validation, PM decision, status projection, or
closure.

#### Scenario: Historical duplicate follows accepted result
- **WHEN** a packet has `accepted_result_id`
- **AND** `packet.result_ids` contains a later historical result id
- **THEN** Reviewer target selection MUST use `accepted_result_id`
- **AND** PM disposition, system validation, and closure MUST NOT treat the
  later historical id as the accepted result

#### Scenario: Accepted packet lacks pointer
- **WHEN** a packet status claims accepted but `accepted_result_id` is missing
- **THEN** Runtime MUST report a mechanical control-plane inconsistency
- **AND** Runtime MUST NOT infer acceptance from `result_ids[-1]`

### Requirement: Review targets are current-object bound

FlowPilot SHALL bind Reviewer and validation targets to the current packet and
accepted result instead of stale packet history.

#### Scenario: Reviewer attempts old packet review
- **WHEN** a Reviewer result targets a stale packet or stale result
- **THEN** Runtime MUST reject or block the review through mechanical
  currentness gates
- **AND** Runtime MUST NOT treat the old review as approval for the current
  packet, PM package, node, or route gate.
