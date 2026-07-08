## ADDED Requirements

### Requirement: PM Disposition Cannot Accept Status-Only Substitutes
FlowPilot PM package-result disposition and Reviewer package review SHALL NOT convert a status-only, reachable-only, report-only, or honest-missing worker result into acceptance evidence for a concrete user deliverable.

#### Scenario: PM receives incomplete deliverable explanation
- **WHEN** PM absorbs a package result whose evidence explains why a required deliverable was not produced, not verified, not extracted, not run, or not fully covered
- **THEN** PM SHALL release a blocker, repair, research, route mutation, or user clarification path using existing fields instead of marking the concrete deliverable accepted.

#### Scenario: Reviewer receives downgraded package
- **WHEN** Reviewer inspects a formal gate package whose PM disposition accepts a substitute objective instead of the original deliverable
- **THEN** Reviewer SHALL block the gate and identify the concrete source-intent element that was dropped or weakened.
