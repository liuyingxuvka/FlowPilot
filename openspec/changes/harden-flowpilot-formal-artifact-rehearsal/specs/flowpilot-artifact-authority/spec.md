## ADDED Requirements

### Requirement: Runtime-owned formal artifacts are projected for repair
FlowPilot SHALL project runtime-owned formal artifact paths and concise failure
details into downstream repair packets when those artifacts are part of the
current blocker context.

#### Scenario: FlowGuard failure repair packet carries formal evidence path
- **WHEN** a FlowGuard operator result creates a `flowguard_failure` blocker
  and a packet-owned FlowGuard evidence artifact path exists
- **THEN** the PM repair packet MUST carry that formal evidence path through the
  current packet body or current handoff contract
- **AND** PM MUST NOT be forced to infer the path by scanning run directories.

#### Scenario: FlowGuard failed checks are PM-actionable
- **WHEN** the FlowGuard formal evidence artifact records failed checks
- **THEN** the PM repair packet or PM-visible FlowGuard result summary MUST
  carry concise failed-check ids or summaries sufficient to choose a repair
  without reading unrelated run artifacts
- **AND** sealed result bodies MUST still be read only through authorized
  result reads.

### Requirement: Formal artifact rejection stays current-contract only
FlowPilot SHALL reject missing, stale, wrong-path, malformed, or internally
incomplete formal artifacts without accepting body-only substitutes,
historical artifacts, or old field aliases.

#### Scenario: Body-only submission cannot satisfy a formal artifact contract
- **WHEN** a packet requires both a result body and a formal artifact
- **AND** the role submits a valid result body but omits the formal artifact
- **THEN** runtime MUST reject the result and issue a current-contract reissue
- **AND** runtime MUST NOT treat the body as a substitute artifact.

#### Scenario: Wrong-path formal artifact is rejected
- **WHEN** the role writes a formal artifact under an old run, old packet, or
  non-current packet-owned path
- **THEN** runtime MUST reject the result as current-contract invalid
- **AND** runtime MUST name the current expected artifact path in the reissue
  material.

#### Scenario: Internal formal artifact decision mismatch is rejected
- **WHEN** the result body says `passed=true` but the packet-owned formal
  artifact reports a blocking or unknown hard-evidence decision
- **THEN** runtime MUST reject the result and name the required artifact
  decision field.
