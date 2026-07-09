## ADDED Requirements

### Requirement: Backstage Roles Use The Full User PM Standard In Scope
FlowPilot SHALL require Worker, Reviewer, and FlowGuard prompt cards to treat
the current user request, PM high-standard contract, PM acceptance registry,
route intent, and node context as available standards for their assigned work
when those artifacts are cited by the current packet or review package.

#### Scenario: Worker performs in-scope high-quality completion
- **WHEN** a Worker receives a current node, implementation, or repair packet
  with relevant global standard references
- **THEN** the Worker prompt SHALL require the Worker to inspect those
  references, complete the assigned work to the highest reasonable in-scope
  quality, repair in-scope defects before returning, and rerun required
  evidence.

#### Scenario: Worker escalates standard-changing improvements
- **WHEN** a useful improvement requires changed user acceptance, route shape,
  broader writes, another role's authority, or a different product target
- **THEN** the Worker prompt SHALL require a blocker, `needs_pm`, or PM
  Suggestion Item instead of silently changing the scope.

#### Scenario: FlowGuard reviews process against same standard
- **WHEN** FlowGuard reviews a plan, route effect, or artifact package
- **THEN** the FlowGuard prompt SHALL require it to use the cited user/PM
  standard and current artifacts as process/model obligations while keeping
  product-quality approval with Reviewer.

#### Scenario: Reviewer challenges from original and PM standards
- **WHEN** Reviewer inspects a node plan, worker result, formal package, or
  final replay
- **THEN** the Reviewer prompt SHALL require comparison against the current
  user/PM standard, not just the local packet summary.
