## ADDED Requirements

### Requirement: Multi-round rehearsals cover bounded repeated-error convergence

Multi-round fake AI control rehearsals SHALL test repeated same-class errors
across normal repair escalation and the fifth-repeat break-glass safety fuse.

#### Scenario: Repeated known error escalates before break-glass

- **WHEN** a prepared fake AI package repeats the same known bad shape on
  attempts one through four
- **THEN** FlowPilot MUST record the repeated lineage and respond through
  normal control-plane reject, reissue, block, repair, redesign, or terminal
  stop without break-glass

#### Scenario: Fifth repeated no-progress error triggers break-glass

- **WHEN** the same bad package class is submitted a fifth time without a repair
  delta, new evidence, or legal next-action progress
- **THEN** the rehearsal MUST expect Controller break-glass and MUST record the
  safety-fuse evidence separately from normal recovery evidence

### Requirement: Multi-round rehearsals carry repair lineage

Repeated repair rehearsals SHALL carry prior blocker, packet, result, repair,
recheck, and failure-reason lineage into later attempts.

#### Scenario: Missing lineage blocks later repair

- **WHEN** a second or later repair attempt omits required prior repair lineage
- **THEN** FlowPilot MUST reject or block that attempt instead of treating it as
  a fresh first repair
