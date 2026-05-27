## ADDED Requirements

### Requirement: Background Progress Is Not Maturation Evidence
FlowPilot SHALL classify background progress logs as liveness only, not as model maturation or validation completion evidence.

#### Scenario: Progress-only logs scope confidence
- **WHEN** a long-running check has stdout or stderr progress but lacks final exit and metadata artifacts
- **THEN** the maturation gate emits `refresh_evidence` or `downgrade_claim` instead of counting the check as passed

#### Scenario: Final artifacts satisfy background proof
- **WHEN** a background check has current stdout, stderr, combined output, exit code, metadata, and result proof artifacts
- **THEN** FlowPilot may consume the evidence for the matching validation obligation

### Requirement: Background Evidence Carries Proof Boundary
FlowPilot SHALL include final artifact paths, exit status, metadata status, timestamp, proof reuse status, and covered obligation when background evidence is consumed by a parent gate.

#### Scenario: Parent gate consumes background child
- **WHEN** a parent model, test mesh, or maturation gate consumes background child evidence
- **THEN** the consumed row names the final artifacts and covered obligation
