## ADDED Requirements

### Requirement: Packet result family partial batches report only missing members
Every packet-result family SHALL derive partial-batch waits from refreshed
member state rather than from a stale family-level flag or event name.

#### Scenario: One member remains missing after durable refresh
- **WHEN** a `material_scan`, `research`, `current_node`, or `pm_role_work` batch has one returned member and one missing member
- **THEN** the wait action names only the missing role
- **AND** the returned role remains recorded as returned in batch member status.

#### Scenario: Family-level flag is not enough to skip sibling refresh
- **WHEN** a family-level result-return flag is already true
- **AND** a sibling batch member still has newly available durable envelope evidence
- **THEN** Router still refreshes the member-level batch status
- **AND** Router folds the sibling evidence before selecting a wait, reminder, or relay action.
