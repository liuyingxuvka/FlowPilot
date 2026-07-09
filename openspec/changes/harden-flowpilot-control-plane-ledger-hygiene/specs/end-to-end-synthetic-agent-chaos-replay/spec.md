## ADDED Requirements

### Requirement: Synthetic replay covers observed DataBank control-plane miss
FlowPilot SHALL preserve the observed DataBank control-plane failure chain as
synthetic replay evidence without relying on the original private run
directory.

#### Scenario: Observed accepted pointer race is replayed
- **WHEN** synthetic replay constructs the `packet-0205/result-0209/event-5616`
  shape where a PM FlowGuard acceptance result is later review-blocked
- **THEN** runtime MUST reject assignment repair and block terminal hygiene
- **AND** the replay MUST prove the packet is not returned to accepted state

#### Scenario: Observed final reviewer authorization gap is replayed
- **WHEN** synthetic replay issues a final Reviewer route-node task with no
  authorized result reads
- **THEN** the corrected runtime path MUST issue the packet with the required
  authorized evidence bundle
- **AND** the replay MUST fail if the bundle is empty or missing required
  current result bodies
