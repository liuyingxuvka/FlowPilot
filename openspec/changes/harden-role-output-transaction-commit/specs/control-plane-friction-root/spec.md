## MODIFIED Requirements

### Requirement: Material Gate Evidence Authority Is Runtime-Backed

Material artifact maps and PM formal gate packages MUST NOT advertise raw
result-body authority for a reviewer unless runtime relay/open evidence grants
that role. PM formal gate packages MUST require source result contract
self-checks to be present, parseable, matching, and passed. No event ingress
path, including direct role-output ledger reconciliation, may mark a PM package
disposition as recorded before this source self-check requirement is enforced.

#### Scenario: PM releases a material formal gate package with bad source self-check

- **GIVEN** a source result envelope has missing or failed `contract_self_check`
- **WHEN** PM records an absorbed package disposition
- **THEN** FlowPilot blocks formal gate package release for source result repair
- **AND** FlowPilot does not set `material_scan_result_disposition_recorded`
  or close the PM disposition wait from a role-output ledger replay

#### Scenario: Control-plane friction gate rejects scoped-only confidence

- **GIVEN** a FlowPilot PM package disposition repair changes event identity,
  role-output replay, or canonical package state
- **WHEN** the repair is claimed complete
- **THEN** the control-plane friction model MUST include a live-run or
  historical bad-case audit for authority-state consistency
- **AND** scoped unit tests, abstract model checks, or skip-live-audit results
  alone MUST NOT be reported as full closure for the defect family
