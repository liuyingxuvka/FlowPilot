## ADDED Requirements

### Requirement: Runtime Records Have Canonical Closure Classification
FlowPilot SHALL classify lifecycle records through a shared closure kernel before
using them in blocker, wait, busy, reconciliation, or terminal-closure decisions.
The kernel SHALL return one of `open`, `closed_success`, `closed_terminal`,
`repair_required`, `invalid_or_incomplete`, or `unknown_needs_recheck`.

#### Scenario: Closed role-specific row does not block progress
- **WHEN** a Controller, Router, Worker, PM, Reviewer, packet, ACK, or terminal
  record carries role-specific evidence that its lifecycle obligation has
  already closed
- **THEN** the caller receives a nonblocking closure classification instead of
  applying a local closed-status list

#### Scenario: Unknown lifecycle vocabulary stays visible
- **WHEN** a record has a status or evidence combination that the closure kernel
  cannot classify as success or terminal closure
- **THEN** the caller receives `unknown_needs_recheck` or
  `invalid_or_incomplete` and MUST keep the item visible as a blocker or repair
  candidate

### Requirement: Closure Classification Does Not Replace Semantic Gates
FlowPilot SHALL use closure classification only to decide mechanical lifecycle
blocking and SHALL NOT use it to bypass role-specific quality, authority,
artifact, reviewer-package, self-check, or sealed-body boundaries.

#### Scenario: ACK closure does not complete output work
- **WHEN** a system-card ACK is classified as `closed_success`
- **THEN** only the ACK/read obligation may clear, and any worker, PM, reviewer,
  or officer output obligation remains governed by its own evidence contract

#### Scenario: Signed artifact closure does not permit mutation
- **WHEN** a signed packet or result lifecycle record is classified as closed
- **THEN** repair or migration code MUST NOT rewrite the signed original and
  must use mutable indexes, ledgers, or sidecar records for follow-up facts

### Requirement: Closure Classification Is Evidence-Aware
FlowPilot SHALL combine status fields with reconciliation, supersession,
artifact, receipt, or package evidence when deciding closure. A status token
alone MUST NOT close work when required evidence is missing.

#### Scenario: Resolved row with reconciled evidence is nonblocking
- **WHEN** a record has a closed status such as `resolved` and matching
  reconciliation evidence for the same obligation identity
- **THEN** the closure kernel classifies it as nonblocking

#### Scenario: Closed-looking row without required evidence remains repairable
- **WHEN** a record has a closed-looking status but lacks the required artifact,
  receipt, package path, or reconciliation identity
- **THEN** the closure kernel classifies it as `repair_required` or
  `invalid_or_incomplete`
