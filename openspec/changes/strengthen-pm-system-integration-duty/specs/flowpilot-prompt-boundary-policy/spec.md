## ADDED Requirements

### Requirement: Integration prompts preserve existing authority boundaries
FlowPilot SHALL express system integration duties in prompt cards without granting new runtime authority or adding compatibility surfaces.

#### Scenario: PM card owns integration
- **WHEN** PM reads its role and phase cards
- **THEN** the cards SHALL identify PM as system integration owner for product architecture, route composition, node relation, result absorption, parent replay decisions, final closure, and model-miss triage.

#### Scenario: Reviewer card challenges but does not own route decisions
- **WHEN** Reviewer reads parent, node, or final review cards
- **THEN** the cards SHALL direct Reviewer to challenge composition defects while leaving route mutation, gate approval, and completion decisions with PM and Runtime.

#### Scenario: FlowGuard card reports process/model risk
- **WHEN** FlowGuard operator reads route or product process cards
- **THEN** the cards SHALL direct FlowGuard to model scattered local-pass/global-incoherence risks as process evidence for PM, not as direct route mutation authority.

#### Scenario: Runtime contract remains current-only
- **WHEN** integration-duty prompt text is added
- **THEN** it SHALL NOT introduce legacy aliases, prose parsing, missing-field defaults, old-router fallback, alternate package shapes, or automatic historical-artifact promotion.

### Requirement: Node context package remains fixed
FlowPilot SHALL keep integration planning metadata outside the five-field `node_context_package`.

#### Scenario: Integration touchpoint is outside node context package
- **WHEN** the node acceptance plan template adds integration guidance
- **THEN** the `node_context_package` SHALL still contain only `purpose`, `acceptance_criteria`, `relevant_references`, `known_risks`, and `acceptance_item_projection`.

#### Scenario: Prompt text forbids node context package expansion
- **WHEN** PM or Reviewer cards discuss node integration touchpoints
- **THEN** they SHALL say that integration touchpoints are plan-level PM/Reviewer material and not extra worker starting-context fields.
