## ADDED Requirements

### Requirement: Packet review rejects same-subject no-delta continuation
FlowPilot packet/result review flow SHALL prevent a rejected subject from
returning to ordinary progress with the same payload, same action, or same
semantic contradiction unless new current evidence or an explicit disposition
exists.

#### Scenario: Same subject result repeats after rejection
- **WHEN** a packet result, FlowGuard report, Reviewer report, or PM repair
  package is rejected and a later submission repeats the same subject state
  without fixing any cited defect
- **THEN** packet review flow MUST classify it as no-delta continuation
- **AND** it MUST route to blocker, repair, stop, wait, or break-glass handling.

#### Scenario: Rejected subject names repair target
- **WHEN** packet review flow emits rejection feedback
- **THEN** the feedback MUST name the current run, subject packet/result/report,
  responsible owner, legal command or event, and minimum valid shape required
  for a corrected attempt.

