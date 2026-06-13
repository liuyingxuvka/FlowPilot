## ADDED Requirements

### Requirement: Same-node repair-loop threshold is a valid break-glass trigger
FlowPilot SHALL allow Controller break-glass evaluation when current-run metadata shows that a same-node consecutive repair loop has exceeded the ordinary repair threshold.

#### Scenario: Threshold opens break-glass
- **WHEN** the runtime reports that the same current route node has more than five consecutive repair attempts for the same blocker problem identity
- **THEN** Controller MAY open the existing break-glass repair playbook
- **AND** Controller MUST NOT request another ordinary PM repair packet for that same node/problem loop.

#### Scenario: Cross-node repeats stay normal
- **WHEN** similar failures occur in multiple different route nodes without any one node exceeding the same-node consecutive threshold
- **THEN** Controller MUST NOT open break-glass for that similarity alone
- **AND** FlowPilot MUST continue through ordinary PM, Reviewer, or FlowGuard repair paths.

#### Scenario: Break-glass cannot approve project work
- **WHEN** break-glass was opened from a same-node repair-loop threshold
- **THEN** break-glass artifacts MUST NOT approve node completion, PM decisions, Reviewer decisions, FlowGuard Operator decisions, route mutation, terminal closure, or target-project work.
