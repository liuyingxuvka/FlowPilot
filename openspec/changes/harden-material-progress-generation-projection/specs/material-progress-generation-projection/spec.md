## ADDED Requirements

### Requirement: Active material generation owns material progress
FlowPilot SHALL derive material repair progress from the active material-scan batch and current material generation before run-wide material progress flags can drive material next actions.

#### Scenario: Old flags disagree with active repair batch
- **WHEN** the active material batch belongs to the current repair generation and has not relayed all packets
- **THEN** Router MUST expose a material packet relay action even if run-wide material relay or result flags are already true.

#### Scenario: Active batch is missing worker results
- **WHEN** the active material batch reports missing blocking worker results
- **THEN** Router MUST wait for the missing active batch members and MUST NOT relay material results to PM from stale run-wide result flags.

### Requirement: Material reissue clears stale progress authority
FlowPilot SHALL prevent stale run-state saves from restoring material progress flags that were cleared for a newer active material generation.

#### Scenario: Older save races with current reissue
- **WHEN** a current material repair generation clears material progress flags and an older stale save contains those flags as true
- **THEN** the stale-save merge MUST preserve the cleared current-generation material progress state.

### Requirement: Material disposition closure is current-generation scoped
FlowPilot SHALL close material PM-disposition waits only from role-output evidence whose scoped identity matches the active material batch, current generation, and body reference.

#### Scenario: Old PM disposition exists for superseded batch
- **WHEN** a PM disposition role-output entry exists for a superseded material generation
- **THEN** Router MUST NOT close the active material PM-disposition wait using only the run-wide material disposition flag.
