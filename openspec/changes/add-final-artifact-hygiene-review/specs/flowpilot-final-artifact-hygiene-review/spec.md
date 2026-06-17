## ADDED Requirements

### Requirement: Terminal Reviewer Inspects Final Artifact Hygiene

FlowPilot SHALL require terminal Reviewer replay reports to include a
`final_artifact_hygiene_review` section that inspects whether the delivered
artifact should be left cleaner, more complete, and more maintainable before
terminal closure.

#### Scenario: Required hygiene gap blocks terminal pass

- **WHEN** terminal Reviewer finds a code, document, UI, model, test, artifact,
  or process hygiene issue classified as `current_goal_required_repair` or
  `clean_delivery_required_repair`
- **THEN** the terminal replay result is blocking
- **AND** PM must repair, waive with authority, mutate route, stop, or convert
  the finding into a terminal supplemental repair item before closure can pass.

#### Scenario: Optional hygiene note does not block closure by itself

- **WHEN** terminal Reviewer finds a hygiene item classified as
  `pm_decision_support` or `future_contract_candidate`
- **THEN** the item is PM decision support or a future-contract candidate
- **AND** it does not block terminal closure unless PM imports it into the
  current supplemental repair contract.

### Requirement: PM Final Ledger Closes Hygiene Findings

FlowPilot SHALL include final artifact hygiene closure rows in the PM final
route-wide ledger and treat unresolved required hygiene rows as terminal
closure blockers.

#### Scenario: Final ledger omits required hygiene closure

- **WHEN** a required hygiene finding exists
- **AND** the final route-wide ledger does not include a covered, repaired,
  waived, stopped, or future-disposition row for it
- **THEN** terminal closure remains blocked.

### Requirement: Supplemental Repair Handles Required Hygiene Work

FlowPilot SHALL route required final artifact hygiene repair through the
existing terminal supplemental repair contract and repair-node mechanics.

#### Scenario: Hygiene repair item preserves original contract

- **WHEN** PM continues terminal repair for a required hygiene gap
- **THEN** PM writes a supplemental repair item with
  `gap_kind: "final_artifact_hygiene_gap"`
- **AND** the item cites the frozen original contract, Reviewer gap result,
  owner repair node, required evidence, and `hygiene_category`
- **AND** the original frozen contract is not edited.

#### Scenario: Repair node projection remains mandatory

- **WHEN** a supplemental hygiene repair item is created
- **THEN** the owner repair node projects the supplemental contract id and
  repair item id
- **AND** the repair node must pass existing FlowPilot gates before final
  ledger or terminal replay can count it as covered.
