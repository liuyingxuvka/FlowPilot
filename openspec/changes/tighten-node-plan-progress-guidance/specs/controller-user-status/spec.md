## ADDED Requirements

### Requirement: Controller status includes runtime-owned node fraction when reporting
FlowPilot SHALL instruct Controller to include the runtime-owned expanded-node
fraction in legitimate user-facing status updates whenever that fraction is
available.

#### Scenario: User-facing status update has progress fraction
- **WHEN** Controller is already allowed or required to report status to the
  user
- **AND** the current runtime output includes `progress_fraction.display`
- **THEN** Controller guidance MUST tell Controller to normally include that
  exact current expanded-node fraction in the status note
- **AND** Controller MUST NOT calculate a fraction, convert it to a percent,
  inspect sealed bodies, infer progress from chat, or treat the fraction as
  completion, gate, route-advance, stop, or final-return authority.

#### Scenario: Node fraction changes during an active run
- **WHEN** Controller observes a current runtime status update where the active
  node or `progress_fraction.display` changed since the last user-facing status
  note
- **THEN** Controller guidance MUST allow a short plain-language progress note
  using only the runtime-owned fraction and public status labels.

#### Scenario: Internal patrol remains quiet
- **WHEN** patrol, receipts, ACK bookkeeping, ledger cleanup, relay
  bookkeeping, or process-only work has no meaningful user-facing status change
- **THEN** Controller guidance MUST preserve the quiet default and MUST NOT
  require a user-facing message solely because internal progress metadata
  exists.
