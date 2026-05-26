## ADDED Requirements

### Requirement: Historical friction surfaces are hard regression gates
FlowPilot SHALL maintain a known-friction regression gate for historical
control-plane failures that have already occurred or materially recurred.

#### Scenario: Known friction row is registered
- **WHEN** a friction surface is accepted for hardening
- **THEN** the gate records the friction id, historical source class, expected
  safe behavior, required model obligation, ordinary test evidence, runtime or
  daemon replay evidence when applicable, and confidence boundary.

#### Scenario: Known friction row is missing evidence
- **WHEN** a known friction row lacks replay evidence, model coverage, or a
  current test reference
- **THEN** FlowPilot MUST report the row as uncovered and MUST NOT count the
  friction gate as passed.

### Requirement: Historical live failures replay through real control surfaces
Known-friction replay SHALL exercise the real Router, packet runtime,
role-output runtime, status projection, lifecycle, daemon, or background
evidence surface that owns the original failure.

#### Scenario: Direct helper test is insufficient for live failure class
- **WHEN** a historical failure involved daemon-visible state, mailbox
  evidence, lifecycle state, status projection, or background artifacts
- **THEN** a direct helper or model-only test MAY support diagnosis but MUST NOT
  be the only passing evidence for the replay row.

#### Scenario: Exact historical fixture is available
- **WHEN** a live-run message, envelope, result, status file, or daemon error
  shape is available
- **THEN** the replay fixture MUST preserve the fields that triggered the
  historical failure and assert the generalized safe behavior.

### Requirement: Completion claims disclose scoped evidence
FlowPilot SHALL separate full regression confidence from scoped confidence when
any relevant live audit, daemon replay, conformance check, or background check
was skipped, model-only, timed out, or still in progress.

#### Scenario: Skipped live audit exists
- **WHEN** a result file reports `ok: true` but also records a skipped live
  audit, skipped conformance replay, model-only mode, or timeout note
- **THEN** FlowPilot MUST classify the evidence as scoped and MUST NOT report
  the known-friction gate as fully passed.

#### Scenario: Background check has final artifacts
- **WHEN** a long check is used as known-friction evidence
- **THEN** FlowPilot MUST verify exit status, stdout, stderr, combined output,
  metadata, last update time, completion status, and proof-reuse status before
  counting it as passed.
