## MODIFIED Requirements

### Requirement: Formal Outputs Return Through Runtime Paths
FlowPilot SHALL require formal role outputs to be written to run-scoped
artifacts and submitted through the current Router-directed runtime path,
preserving Controller-visible metadata boundaries.

#### Scenario: Formal output avoids chat body leakage
- **WHEN** a role is asked for a report, result, decision, blocker, or formal
  output
- **THEN** the prompt SHALL direct the role to submit through
  `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id
  <packet-id> --body <sealed_result_summary>`
- **AND** the prompt SHALL forbid report bodies, blockers, evidence details,
  recommendations, commands, or repair instructions in chat.

#### Scenario: Current packet open command is not replaced by old shape arguments
- **WHEN** a role-facing prompt, card, or generated contract names the current
  packet-open path
- **THEN** it SHALL use `flowpilot_new.py open-packet --lease-id <lease-id>
  --packet-id <packet-id>`
- **AND** it SHALL NOT instruct roles to call `open-packet` with
  `--output-type`, `--role`, or `--agent-id` as live current arguments.

#### Scenario: Role authority stays scoped
- **WHEN** a Reviewer, Officer, Worker, PM, or Controller reads a prompt card
- **THEN** the card SHALL NOT grant authority outside that role's existing
  Router-authorized scope
- **AND** it SHALL NOT teach lower-level role-output helper commands as the
  live current handoff path.

### Requirement: Prompt Policy Drift Is Testable
FlowPilot SHALL provide focused validation that card-manifest entries,
prompt-policy assets, and current generated role-facing contract sources stay
aligned for common boundary text.

#### Scenario: Generated role-facing old command fails validation
- **WHEN** a current role-facing card, prompt asset, runtime-kit asset, or
  generated role-facing contract source exposes obsolete commands such as old
  runtime submission/progress commands, lower-level live handoff commands, or
  `open-packet --output-type`
- **THEN** prompt/card validation SHALL fail before installed-skill
  synchronization.

#### Scenario: Role-specific content remains allowed
- **WHEN** a card includes domain-specific instructions in addition to shared
  boundary policy
- **THEN** validation SHALL allow that content as long as it does not
  contradict the shared policy.

