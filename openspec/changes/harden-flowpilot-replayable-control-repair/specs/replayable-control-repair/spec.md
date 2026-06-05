## ADDED Requirements

### Requirement: Package-produced scripts are replayable
FlowPilot package instructions SHALL require scripts, checkers, and evidence
generators to be replayable and SHALL forbid gating their ability to run on a
specific FlowPilot packet id, current active packet, or one-time phase.

#### Scenario: Script is replayed after original packet acceptance
- **WHEN** a later role reruns a script produced by an earlier accepted packet
- **THEN** the script can execute from supplied inputs without requiring the
  earlier packet to still be the active FlowPilot packet.

#### Scenario: Script binds to a concrete packet id
- **WHEN** a script refuses to run solely because its producing packet id is no
  longer the active packet
- **THEN** FlowPilot treats the package artifact as failing the replayability
  rule rather than treating the later replay as invalid.

### Requirement: Reviewer reruns are targeted
FlowPilot reviewer guidance SHALL default to inspecting existing run results
for freshness, input binding, and conclusion support, and SHALL reserve script
reruns for critical, suspicious, or adversarial replay cases.

#### Scenario: Existing evidence is sufficient
- **WHEN** the existing run result is fresh, bound to the reviewed input, and
  supports the claimed conclusion
- **THEN** reviewer review can proceed without rerunning every script.

#### Scenario: Evidence needs adversarial replay
- **WHEN** the evidence is critical, suspicious, stale-looking, or otherwise
  needs adversarial replay
- **THEN** the reviewer may rerun the relevant script as part of review.

### Requirement: PM stop for user is a hard wait
FlowPilot runtime SHALL treat PM `stop_for_user` as a hard user wait and SHALL
not automatically reissue PM repair-decision packets during ordinary
patrol/resume.

#### Scenario: PM stops for user
- **WHEN** PM submits `stop_for_user` for an active blocker
- **THEN** FlowPilot exposes a waiting-for-user state with the stop reason and
  does not autonomously issue another PM repair-decision packet.

#### Scenario: User explicitly resumes stopped blocker
- **WHEN** the user explicitly requests recovery for a stopped blocker
- **THEN** FlowPilot may run a current-runtime recovery path and record that the
  recovery was user-requested.
