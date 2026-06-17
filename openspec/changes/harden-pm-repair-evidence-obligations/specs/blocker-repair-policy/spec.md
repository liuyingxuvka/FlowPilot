## ADDED Requirements

### Requirement: PM repair decisions disposition blocker evidence obligations
FlowPilot SHALL require PM repair decisions to disposition every current repair
evidence obligation declared by the PM repair packet before runtime may apply
the PM decision.

#### Scenario: PM repairs current scope with obligation disposition
- **WHEN** an active blocker produces a PM repair packet containing
  `repair_evidence_obligations`
- **AND** PM chooses `repair_current_scope`
- **THEN** the PM result MUST include `repair_obligation_disposition`
- **AND** every obligation id from the packet MUST be covered exactly once
- **AND** runtime MUST treat `reason` text as explanation only, not obligation
  closure.

#### Scenario: Reason-only PM repair remains blocked
- **WHEN** a PM repair packet declares one or more repair evidence obligations
- **AND** PM submits only `decision` and `reason`
- **THEN** runtime MUST mechanically reject the PM repair result
- **AND** the active blocker MUST remain targeted at PM for a corrected current
  repair decision.

#### Scenario: Waiver covers obligations only with authority
- **WHEN** PM chooses `waive_with_authority` for a blocker with repair evidence
  obligations
- **THEN** the result MUST include `authority_ref`
- **AND** `repair_obligation_disposition` MUST identify which obligations are
  waived by that authority
- **AND** runtime MUST reject waiver text that does not cover the declared
  obligation ids.

### Requirement: PM repair decisions consume all related blocker bodies
FlowPilot SHALL require PM repair decisions to use every required
runtime-authorized blocker, target, and upstream result body before selecting a
repair path.

#### Scenario: PM repair packet carries multiple required bodies
- **WHEN** a blocker repair packet includes `authorized_result_reads` for the
  blocker result body, blocked target result body, or upstream context bodies
- **THEN** PM MUST open the packet through the current runtime path
- **AND** PM MUST read every delivered required body before submitting the
  repair decision
- **AND** runtime MUST reject submission when any required body lacks a current
  open receipt for the PM lease.

#### Scenario: Summary-only repair choice remains blocked
- **WHEN** a PM repair packet includes `recent_role_report_summary` and
  required authorized result bodies
- **AND** PM submits a repair decision without opening all required bodies
- **THEN** runtime MUST reject the decision as missing required body reads
- **AND** PM MUST correct the current packet result instead of asking
  Controller to summarize sealed bodies.
