## ADDED Requirements

### Requirement: Rejection liveness matrix owns malformed output families
FlowPilot SHALL maintain a parent rejection/liveness matrix covering malformed
or insufficient AI outputs across startup intake, packet envelopes, packet
bodies, result envelopes, result bodies, FlowGuard reports, Reviewer reports,
PM repair decisions, route mutation, terminal replay, and acceptance-item
surfaces.

#### Scenario: Required malformed cells have owners
- **WHEN** the rejection/liveness matrix is generated
- **THEN** every required malformed-output cell MUST have a contract family,
  defect class, owning model obligation, owning code contract, and validation
  evidence owner
- **AND** missing cell ownership MUST fail the parent matrix gate.

#### Scenario: Broad routine cells include common malformed classes
- **WHEN** the routine rejection/liveness matrix is generated
- **THEN** it MUST include practical cells for missing fields, missing bodies,
  missing paths, missing hashes, wrong owners, wrong ids, unsupported enums,
  stale evidence, prose-only critical content, contradictory pass/blocker
  states, same-payload retry, same-action retry, and corrected retry
- **AND** each skipped malformed class MUST include an explicit out-of-scope
  rationale.

#### Scenario: Matrix does not overclaim live AI quality
- **WHEN** the matrix consumes fake AI, fixture, or synthetic replay evidence
- **THEN** it MUST classify that evidence as contract-bound control-flow
  evidence
- **AND** it MUST NOT classify the row as live AI semantic quality or live
  project completion evidence.

### Requirement: Rejection feedback is actionable
Every supported mechanical or semantic rejection path SHALL return feedback
that identifies the rejected subject, missing or contradictory fields, the
responsible owner, the legal command or event, and the minimum valid structured
shape needed for a corrected attempt.

#### Scenario: Missing required field feedback is precise
- **WHEN** a packet, result, report, or repair output is rejected for a missing
  required field, missing body, missing path, missing hash, unsupported enum,
  stale subject, or contradictory pass/blocker state
- **THEN** the rejection feedback MUST name the rejected subject id and the
  concrete missing or invalid fields
- **AND** it MUST name the role or runtime owner responsible for the corrected
  attempt.

#### Scenario: Vague rejection feedback fails
- **WHEN** a rejected output receives only generic prose such as "try again" or
  "fix the result" without current subject identity and minimum valid shape
- **THEN** the matrix MUST classify the rejection feedback as insufficient
- **AND** the row MUST NOT support continuation confidence.

### Requirement: Post-rejection continuation requires progress
FlowPilot SHALL require the next continuation for the same subject after a
rejected or blocked AI output to prove a semantic delta, a current
external/user event, or an explicit blocker, repair, stop, wait, or
break-glass disposition.

#### Scenario: Same payload cannot continue
- **WHEN** the next submitted payload or next action matches the rejected
  subject without fixing any cited field, body, identity, owner, command,
  evidence, or semantic contradiction
- **THEN** FlowPilot MUST classify the continuation as a no-delta retry
- **AND** it MUST block, repair, stop, wait on a current event, or route
  break-glass rather than treat the attempt as ordinary progress.

#### Scenario: Corrected payload can continue
- **WHEN** the next attempt fixes at least one cited defect and preserves the
  current run, subject, and owner identities
- **THEN** FlowPilot MAY continue through the ordinary current-contract path
- **AND** the matrix MUST record the repaired defect class and evidence row.

### Requirement: Stuck detection is absorbed into stable disposition
FlowPilot SHALL distinguish detecting a stuck control-plane state from absorbing
that stuck state. Once a same action key and observed event count crosses the
configured repeat threshold, later refreshes MUST NOT return to ordinary
process continuation unless new progress evidence exists.

#### Scenario: Repeated action becomes blocker
- **WHEN** a current run repeats the same nonterminal action key with the same
  observed event count above `max_repeated_action_without_event`
- **THEN** the live projection MUST report a blocker, repair requirement,
  user-required wait, stop, or break-glass disposition
- **AND** parent mesh MUST NOT report the run as green continuation.

#### Scenario: New event clears repeated action blocker
- **WHEN** a current event, corrected subject, changed action key, or explicit
  interactive wait is recorded after stuck detection
- **THEN** FlowPilot MAY clear the previous repeated-action blocker
- **AND** the clearing evidence MUST be visible in the run metadata or result
  artifact consumed by the parent matrix.
