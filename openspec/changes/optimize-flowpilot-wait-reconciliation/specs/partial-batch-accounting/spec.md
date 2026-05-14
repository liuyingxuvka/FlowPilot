## ADDED Requirements

### Requirement: Batch members have independent status
Each Router-owned packet batch SHALL track every member packet with packet id, target role, holder, dependency class, relay state, ACK/progress state, result state, and result envelope reference.

#### Scenario: One member returns before another
- **WHEN** worker A returns a valid result and worker B remains pending in the same batch
- **THEN** the batch records worker A as returned, worker B as missing, and the aggregate returned count as one

### Requirement: Batch summaries name remaining work accurately
The user-facing and controller-facing batch summary SHALL derive missing roles and counts from refreshed member state, not from stale expected-role fields.

#### Scenario: Old expected role differs from actual pending role
- **WHEN** the old wait names worker A but worker A has returned and worker B is still pending
- **THEN** the status summary says worker A returned and worker B remains pending

### Requirement: Protected joins require all blocking members
The Router SHALL NOT mark a blocking batch as joined, reviewed, PM-absorbed, or stage-advanceable until all blocking member packets have returned or been explicitly canceled or superseded by an authorized PM decision.

#### Scenario: Blocking member still missing
- **WHEN** a material-scan batch has one missing blocking member
- **THEN** material sufficiency, PM final absorption, reviewer formal gate, and stage advancement remain unavailable
