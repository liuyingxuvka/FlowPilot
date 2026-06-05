## ADDED Requirements

### Requirement: Reviewer replay policy distinguishes evidence inspection from rerun
FlowPilot reviewer guidance SHALL distinguish default inspection of existing
run results from targeted rerun of scripts, and SHALL allow targeted rerun only
when the reviewer identifies a critical, suspicious, or adversarial replay need.

#### Scenario: Reviewer inspects existing result first
- **WHEN** reviewer receives a package with existing script output or evidence
- **THEN** reviewer first evaluates freshness, input binding, and conclusion
  support before deciding whether rerun is needed.

#### Scenario: Reviewer reruns selected evidence
- **WHEN** reviewer identifies a critical, suspicious, or adversarial replay
  need
- **THEN** reviewer may rerun the selected script and use the replay result in
  the review decision.
