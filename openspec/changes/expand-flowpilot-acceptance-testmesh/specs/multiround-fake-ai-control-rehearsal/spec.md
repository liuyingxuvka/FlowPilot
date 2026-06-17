## ADDED Requirements

### Requirement: Fake AI Uses Opened Current Packet Body
Fake AI rehearsal helpers SHALL derive acceptance-item ids, terminal segment targets, and branch-specific minimal valid shapes from the current opened packet body and current packet-result contract catalog. Static success fixtures MUST NOT satisfy terminal replay or acceptance-item closure when the current packet body provides more specific targets.

#### Scenario: Terminal replay derives segments from opened packet
- **WHEN** fake AI opens a terminal backward replay packet
- **THEN** the submitted replay result includes segment reviews for the runtime-issued `segment_targets` and rejects missing, duplicate, or unexpected segment ids

#### Scenario: PM disposition derives item ids from opened packet
- **WHEN** fake AI opens a PM disposition or node acceptance packet
- **THEN** the submitted result closes the node-owned acceptance item ids from the current packet body instead of using a static item list

### Requirement: Fake AI Payload Chaos Matrix
Fake AI rehearsal SHALL include negative payload cases for acceptance-item registry and terminal replay currentness. The matrix MUST cover at least one successful recovery path for each payload family that can be mechanically reissued or PM-repaired.

#### Scenario: Payload chaos blocks false terminal success
- **WHEN** fake AI submits a malformed acceptance item or terminal replay payload
- **THEN** FlowPilot blocks, reissues, or routes repair without reporting terminal completion

#### Scenario: Payload chaos can recover
- **WHEN** fake AI resubmits the current-contract payload after a block or reissue
- **THEN** FlowPilot accepts the corrected result and continues to the next current route step
