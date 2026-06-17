## ADDED Requirements

### Requirement: Full-flow fake AI replay proves prepared body and runtime path

Full-flow fake AI replay SHALL prove both the prepared fake AI body contract and
the public runtime path for accepted executable bridge rows.

#### Scenario: Prepared body and runtime path both pass

- **WHEN** a full-flow replay row is accepted for bridge coverage
- **THEN** it MUST show the prepared body matched the current packet-result
  contract and the body advanced only through authorized Runtime/CLI entrypoints

#### Scenario: Body-only replay stays scoped

- **WHEN** a prepared fake AI body passes contract checks but is not submitted
  through the public runtime path
- **THEN** the replay MUST mark the row as fake-body evidence only, not
  Runtime/CLI evidence
