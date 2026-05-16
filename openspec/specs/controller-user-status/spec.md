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
