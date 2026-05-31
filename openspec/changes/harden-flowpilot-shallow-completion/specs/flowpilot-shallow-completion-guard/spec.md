## ADDED Requirements

### Requirement: PM identifies shallow-completion traps
For each formal FlowPilot route, PM SHALL identify a small task-specific list of
results that could look complete while still leaving the final user without the
practical next step implied by the accepted user outcome.

#### Scenario: Runnable outcome has a design-only trap
- **WHEN** the accepted user outcome asks for a runnable pilot, first data pass,
  implementation-ready package, operational handoff, or other practical next
  action
- **THEN** PM SHALL name the shallow-completion traps that would leave that
  next action undefined.

#### Scenario: Planning-only outcome is explicitly bounded
- **WHEN** the accepted user outcome is discussion, planning, proposal, or
  review only
- **THEN** PM SHALL record that the route may close with a bounded planning
  artifact
- **AND** PM SHALL NOT claim runnable, operational, or implementation-ready
  completion unless the route produces that evidence.

### Requirement: PM routes work to defeat current shallow-completion traps
PM SHALL bind each current shallow-completion trap to existing route work,
merge it into an adjacent route node, or block route activation until the trap
has a concrete owner.

#### Scenario: All-design route for practical outcome
- **WHEN** a route for a practical user outcome is made only of design, define,
  review, integrate, or report-style nodes
- **THEN** PM SHALL either add or merge work that produces the missing practical
  next-step evidence
- **OR** PM SHALL block route activation with the missing next step named.

#### Scenario: Existing node can own the proof
- **WHEN** an existing node can produce the proof that defeats the shallow trap
- **THEN** PM SHALL keep the guard inside that node instead of adding a separate
  node that does not improve evidence, failure isolation, role authority, or
  user-visible progress.

### Requirement: Reviewer attacks shallow-completion traps
Reviewer SHALL challenge PM and worker evidence against the current
shallow-completion trap list before passing a node-completion or terminal-readiness
gate that affects the final user's outcome.

#### Scenario: Report-only proof leaves trap plausible
- **WHEN** the proof only shows that a document, report, ledger row, screenshot,
  or command record exists
- **AND** any named shallow-completion trap is still plausible
- **THEN** Reviewer SHALL block the gate or request more evidence rather than
  downgrade the issue to a nonblocking improvement.

### Requirement: Closure replays the final output against user usefulness
Terminal closure SHALL compare the delivered output to the original accepted
user outcome and SHALL block closure when the user still lacks the practical
next step that the route was supposed to deliver.

#### Scenario: Lifecycle evidence is clean but user cannot proceed
- **WHEN** route ledger, packet lifecycle, and evidence matrix rows are clean
- **AND** the final output still leaves the user's practical next step undefined
- **THEN** terminal closure SHALL block and return the route to PM repair,
  route mutation, or explicitly scoped user-facing partial completion.
