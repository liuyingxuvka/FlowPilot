## ADDED Requirements

### Requirement: Current route authority snapshot
FlowPilot SHALL derive a current route authority snapshot before any foreground route-control decision that may dispatch work, wait for a role decision, accept an external event, mutate a route/frontier, resolve a blocker, or claim terminal route closure.

The snapshot MUST identify the current owner role, current state family, legal next action ids, forbidden action ids or classes, current route/frontier version identity when available, and the required repair command for wrong-path submissions.

#### Scenario: PM decision sees current legal actions
- **WHEN** the router asks the project manager for a parent segment decision after current parent backward replay has passed
- **THEN** the foreground action includes a route authority snapshot whose `current_owner` is `project_manager`, whose `legal_next_actions` include `record_parent_segment_decision`, and whose forbidden actions exclude parent completion until the segment decision is recorded

#### Scenario: Missing authority snapshot blocks route progression
- **WHEN** a route-control action would ask a role to choose or commit route progress without a current route authority snapshot
- **THEN** FlowPilot rejects the progression and materializes a current-contract control blocker instead of continuing through a fallback path

### Requirement: Single owner for current route actions
FlowPilot SHALL treat owner absence and owner conflict as route-control faults. A state that requires a route-control decision MUST have exactly one current owner for the selected action family.

#### Scenario: Duplicate owner is blocked
- **WHEN** both router-internal progression and project-manager route mutation are simultaneously presented as owners for the same current state family
- **THEN** FlowPilot rejects the decision surface with an owner-conflict blocker and does not accept either route action as current progress

#### Scenario: Wrong role cannot advance route
- **WHEN** a worker, reviewer, or FlowGuard operator submits a project-manager route action
- **THEN** FlowPilot rejects the submission as wrong-role authority and returns current owner, legal next actions, and the required repair command

### Requirement: Wrong-path submissions are rejected with repair feedback
FlowPilot SHALL reject any submitted route action or external event whose selected action is not in the current legal action set. The rejection MUST be structured and actionable: it MUST name the rejected action or event, current owner, current state family, legal next actions, forbidden actions, and required repair command.

#### Scenario: PM chooses parent closure too early
- **WHEN** the project manager submits a parent completion or terminal closure action while child work, backward replay, segment decision, blocker, or stale evidence requirements remain open
- **THEN** FlowPilot rejects that wrong path, preserves route/frontier state, and returns the legal action the PM must submit next

#### Scenario: Corrected retry can return to main workflow
- **WHEN** a wrong-path submission is rejected and the next submission uses the required repair command with one current legal action
- **THEN** FlowPilot accepts the corrected route action and clears the wrong-path blocker without requiring a compatibility fallback

### Requirement: Unsupported old paths cannot become route progress
FlowPilot SHALL reject unsupported old action ids, legacy aliases, compatibility wrappers, prose-only route decisions, missing-field defaults, stale legal snapshots, and fallback evidence as unsupported current-route authority.

#### Scenario: Legacy alias is rejected
- **WHEN** a role submits an old action alias that resembles a current route action but is not listed in the current legal action set
- **THEN** FlowPilot rejects the alias and does not translate it into a current route action

#### Scenario: Prose fallback is rejected
- **WHEN** a role submits prose or a wrapper shape that describes route progress without the current structured route action fields
- **THEN** FlowPilot rejects the submission and returns the current structured repair command

### Requirement: ModelMesh blocks unsafe route-authority confidence
FlowPilot ModelMesh SHALL block `mesh_green_can_continue` when route-authority singularity evidence is missing, stale, conflicted, or contradicted by live route/control projections.

#### Scenario: Parent mesh sees missing route-authority evidence
- **WHEN** the route-authority singularity model or projection does not prove current owner, legal actions, wrong-path rejection, and no-fallback disposition for the changed route-control surface
- **THEN** ModelMesh reports blocked confidence instead of allowing a safe-to-continue claim
