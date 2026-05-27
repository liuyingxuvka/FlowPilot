# controller-user-status Specification

## Purpose
TBD - created by archiving change simplify-controller-user-status. Update Purpose after archive.
## Requirements
### Requirement: Controller user reports use plain language

The Controller SHALL explain user-visible status in plain language and SHALL
avoid exposing internal event names, packet ids, ledger names, hashes, action
ids, contract names, or diagnostic file paths unless the user explicitly asks
for technical details.

#### Scenario: Controller reports a wait to the user

- **WHEN** Controller mentions a Router-authorized wait or action to the user
- **THEN** the user-visible message states what is happening, what FlowPilot is
  waiting for, and whether the user needs to act without copying internal
  action names or metadata.

#### Scenario: User asks for technical details

- **WHEN** the user explicitly asks for technical details
- **THEN** Controller may include diagnostic names or paths while preserving
  sealed-body and role-authority boundaries.

### Requirement: Router actions remind Controller to avoid internal wording

Every Router-generated Controller action SHALL carry a policy reminder that any
user mention of the action must be explained in plain language instead of
copying internal action names or metadata.

#### Scenario: Router creates a Controller action

- **WHEN** Router constructs a Controller action
- **THEN** the action includes a controller-facing user-reporting policy
  reminder.

#### Scenario: Display action is rendered to the user

- **WHEN** a Router action includes `display_text`
- **THEN** the display text does not include the controller-facing policy
  reminder or internal action metadata.

### Requirement: Status summary exposes compact progress facts

The current status summary SHALL include a compact `progress_summary` object
derived from public route/frontier metadata and SHALL exclude sealed body
content, evidence tables, source fields, hashes, and diagnostic paths from that
object.

#### Scenario: Active route has nested current path

- **WHEN** Router writes `current_status_summary.json` for an active route with
  a known current node
- **THEN** `progress_summary` includes `level_count`, one entry per active path
  level with node count, completed count, current index, and current label,
  overall completed and total node counts, elapsed seconds when known, and the
  coarse state.

#### Scenario: Runtime start time is unavailable

- **WHEN** Router cannot derive a valid run start time
- **THEN** `progress_summary.elapsed_seconds` is `null` and the rest of the
  progress facts remain available.

#### Scenario: Status summary remains public

- **WHEN** `current_status_summary.json` is used by chat or UI status surfaces
- **THEN** `progress_summary` contains only public progress facts and does not
  expose sealed body fields, evidence tables, source file paths, hashes, packet
  body details, or report content.

### Requirement: Controller status may use process asides operationally

The Controller SHALL be allowed to use Controller-facing process asides to
explain operational status in plain language, but SHALL NOT present aside text
as formal content, evidence, approval, route decision, report reasoning, or
gate judgment.

#### Scenario: Controller reports submitted status from an aside

- **WHEN** a Controller-facing process aside says a role has submitted a
  formal output or is waiting for Router processing
- **THEN** Controller may tell the user that the formal output has been
  submitted or the system is waiting for processing
- **AND** Controller does not summarize the formal output content from the
  aside.

#### Scenario: Controller sees business content in an aside

- **WHEN** a Controller-facing process aside includes apparent business
  content, evidence, conclusion, recommendation, or approval wording
- **THEN** Controller ignores that content for formal decision purposes
- **AND** Controller does not expose it as a formal user-facing conclusion.

### Requirement: Current status summary is display-only projection

The current status summary SHALL declare itself as a display-only projection
and SHALL name the Controller action ledger plus Router daemon status as the
authoritative control sources for Controller progress and stop decisions.

#### Scenario: Status summary names projection authority

- **WHEN** Router writes `current_status_summary.json`
- **THEN** the summary includes projection metadata stating that it is not a
  Controller stop authority
- **AND** the summary names the Controller action ledger and Router daemon
  status as authoritative control sources.

#### Scenario: Status update permission is separate from stop permission

- **WHEN** the summary reports that a user/status update may be returned during
  a nonterminal run
- **THEN** it also reports `controller_stop_allowed=false` and
  `nonterminal_controller_must_stay_attached=true`.

### Requirement: Next step projection carries source and freshness

The current status summary SHALL attach source and freshness metadata to its
`next_step` projection so Controller can distinguish executable ledger work
from display-only or stale information.

#### Scenario: Pending action is current

- **WHEN** `next_step` is derived from the current pending Controller action
- **THEN** the summary includes a `source_action_id`, `source_status`, and
  `fresh_for_controller_decision=true`.

#### Scenario: No pending action or completed action projection

- **WHEN** there is no pending executable Controller action or the projected
  action is already done/reconciled
- **THEN** the summary marks `next_step.fresh_for_controller_decision=false`
  and `next_step.display_only=true`.

#### Scenario: Stale next step cannot authorize stop

- **WHEN** `next_step.fresh_for_controller_decision=false`
- **THEN** Controller MUST NOT use `next_step` as evidence that final Controller
  exit is allowed.

### Requirement: Current status reflects latest control-plane facts
Controller user status SHALL derive current progress and wait wording from the
latest reconciled run state, repair transaction, active blocker, ACK ledger,
and lifecycle facts.

#### Scenario: PM repair decision is already committed
- **WHEN** a PM repair transaction has been committed and the fresh repair
  generation is registered
- **THEN** user-visible current status MUST NOT say FlowPilot is still waiting
  for PM to decide the same blocker.

#### Scenario: ACK has been resolved
- **WHEN** a required ACK has a valid receipt and the target semantic work is
  still pending
- **THEN** user-visible current status MUST state that the receipt is resolved
  and that the remaining wait is for semantic work, not for the same ACK.

#### Scenario: Run is stopped
- **WHEN** a user stop has been recorded for the current run
- **THEN** user-visible current status MUST report the run as stopped or
  terminal and MUST NOT present it as an active route.
