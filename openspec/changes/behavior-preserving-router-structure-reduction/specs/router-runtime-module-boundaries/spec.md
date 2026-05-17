## ADDED Requirements

### Requirement: Router event dispatch is table-driven behind the legacy entrypoint

The router MUST route selected external events through a named handler table
while preserving `_record_external_event_unchecked` as the compatibility
entrypoint for migrated events.

#### Scenario: Stable event handlers are migrated first

- **GIVEN** heartbeat/manual resume, stop/cancel, heartbeat binding, or route
  activation events are submitted
- **WHEN** the compatibility entrypoint receives the event
- **THEN** it MAY delegate to a handler table
- **AND** the observable result and persisted state MUST match the pre-refactor
  behavior.

### Requirement: Controller action computation uses ordered providers

`compute_controller_action` MUST become orchestration over ordered provider
functions while preserving the current priority order.

#### Scenario: Provider order is stable

- **GIVEN** multiple provider sources could produce actions
- **WHEN** the action computation runs
- **THEN** lifecycle, pending action, card delivery, resume, startup, node loop,
  and closure providers MUST be queried in the documented order.

### Requirement: Controller action application uses registered handlers

`apply_controller_action` MUST dispatch low-risk action types through
registered handlers while preserving central state load/save and error handling.

#### Scenario: Handler does not bypass router persistence

- **GIVEN** a low-risk action handler applies display sync, terminal summary,
  system-card delivery commit, or passive wait handling
- **WHEN** the action completes
- **THEN** router state persistence, controller-action ledger semantics, and
  error handling MUST remain centralized or explicitly delegated through the
  same router save path.

### Requirement: Runtime domains split only after focused coverage exists

Domain modules such as startup, resume, cards, route, and closure MUST be
introduced one at a time and only with focused tests for the moved domain.

#### Scenario: Route domain extraction preserves route mutation behavior

- **GIVEN** route activation or mutation helpers move out of the main router
- **WHEN** existing route mutation tests run
- **THEN** return repair, supersede original, sibling branch replacement, stale
  evidence invalidation, current packet supersession, and replay blocking MUST
  keep passing.
