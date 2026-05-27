# synthetic-agent-trace-replay Specification

## Purpose
TBD - created by archiving change add-synthetic-agent-trace-replay. Update Purpose after archive.
## Requirements
### Requirement: Synthetic traces use real control-plane APIs

Synthetic agent trace tests SHALL replay fake role actions through real
FlowPilot packet, result, router, ledger, and evidence-boundary APIs instead of
directly marking route work complete.

#### Scenario: Happy-path worker trace reaches PM disposition

- **WHEN** a synthetic worker trace receives a PM-issued packet, acknowledges
  it, opens the packet body through the runtime, and submits a fake result
- **THEN** the persisted packet ledger records the controller relay, body-open
  receipt, result envelope, result hash, and next PM disposition step

#### Scenario: Direct completion mutation is not a valid trace

- **WHEN** a trace attempts to prove completion by seeding final completion
  state without runtime packet/result evidence
- **THEN** the trace replay review MUST reject the trace as invalid evidence

### Requirement: Synthetic traces cover known-bad role behavior

Synthetic trace packs SHALL include known-bad role behavior that is expected to
fail at specific FlowPilot gates.

#### Scenario: ACK-only role output does not complete work

- **WHEN** a synthetic worker acknowledges a packet but does not submit a result
  body through the runtime
- **THEN** FlowPilot MUST keep the semantic work wait open and MUST NOT treat
  the ACK as completion evidence

#### Scenario: Wrong role or agent result is rejected

- **WHEN** a synthetic result envelope is submitted by the wrong role or by an
  agent identity that does not own the active holder lease
- **THEN** FlowPilot MUST reject the result before PM disposition or reviewer
  approval can use it

#### Scenario: Tampered result hash is rejected

- **WHEN** a synthetic result body changes after its envelope hash is recorded
- **THEN** FlowPilot MUST reject the result as stale or tampered evidence

### Requirement: Synthetic evidence stays separate from live completion evidence

Synthetic and fixture evidence SHALL be recorded and tested as non-live
evidence, and SHALL NOT satisfy live project completion, release, or final
acceptance gates.

#### Scenario: Fixture evidence cannot close live completion

- **WHEN** a final ledger contains only fixture or synthetic evidence for a
  live project gate
- **THEN** FlowPilot MUST keep the live gate unresolved or explicitly disclose
  the evidence as non-live

#### Scenario: Synthetic replay can validate control flow

- **WHEN** a synthetic trace pack passes its positive and negative assertions
- **THEN** FlowPilot MAY count it as regression evidence for control-flow
  behavior but MUST NOT count it as live project outcome evidence

### Requirement: Route mutation traces invalidate stale evidence

Synthetic route-mutation traces SHALL prove that replacement, repair, and stale
evidence paths cannot reuse old active packets or old proof as current proof.

#### Scenario: Route mutation marks old evidence stale

- **WHEN** a synthetic reviewer block causes a PM route mutation or replacement
- **THEN** FlowPilot MUST mark affected old packet/result/review evidence stale
  and require same-scope replay before completion

#### Scenario: Old active packet cannot block replacement route

- **WHEN** a synthetic route replacement supersedes an old current node packet
- **THEN** FlowPilot MUST dispose or supersede the old packet before the new
  route can be rechecked

### Requirement: Resume traces preserve sealed-body and PM authority

Synthetic resume traces SHALL verify that heartbeat or manual resume uses
current-run metadata and routes existing results to PM without reading sealed
packet or result bodies.

#### Scenario: Resume relays existing result to PM

- **WHEN** a synthetic resume finds a returned worker result envelope for the
  current run
- **THEN** FlowPilot MUST relay the result envelope to PM disposition and MUST
  NOT send the raw worker result body directly to reviewer completion

#### Scenario: Resume blocks ambiguous worker state

- **WHEN** a synthetic resume finds unclear holder, agent, relay, or body-open
  evidence
- **THEN** FlowPilot MUST block for PM recovery instead of guessing completion

### Requirement: Background trace validation requires final artifacts

Synthetic trace validation for background model or tier checks SHALL treat
progress output as liveness evidence only.

#### Scenario: Progress-only background evidence is not a pass

- **WHEN** a background artifact has progress output but no exit artifact or
  final passing status
- **THEN** FlowPilot MUST classify the evidence as incomplete, running, or
  progress-only rather than passing
