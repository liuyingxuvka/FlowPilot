# complete-ai-workstream-orchestration Specification

## Purpose
TBD - created by archiving change upgrade-flowpilot-complete-workstream-orchestration. Update Purpose after archive.
## Requirements
### Requirement: Every substantive AI role executes a complete bounded workstream
FlowPilot SHALL instruct PM, Worker, research/evidence Worker, Reviewer, FlowGuard Operator, and any substantive helper role to understand the assigned scope, write a numbered plan before substantive execution, assess risk and FlowGuard need, execute or delegate within authority, integrate outputs, verify, repair in-scope defects, and only then submit its current result.

#### Scenario: Worker receives a bounded route leaf
- **WHEN** Runtime dispatches a current Worker packet for an accepted route leaf
- **THEN** Worker SHALL create and execute a local numbered plan that fully closes the packet outcome and proof boundary
- **AND** Worker SHALL NOT reinterpret local planning as authority to change product scope, route structure, acceptance, or cross-role decisions.

#### Scenario: Reviewer or FlowGuard Operator receives formal work
- **WHEN** Runtime dispatches a substantive Reviewer or FlowGuard Operator packet
- **THEN** the role SHALL plan its own direct inspection, adversarial probes, evidence checks, and report verification as a complete bounded workstream
- **AND** SHALL preserve its existing anti-repair or non-approval authority boundary.

### Requirement: Substantive reports expose numbered plan completion
Every substantive AI report SHALL include a `Workstream Plan and Completion` subsection inside the existing `Contract Self-Check`, containing each numbered plan step, its intended outcome, status, evidence refs, deviation or blocker, delegation integration, verification performed, unresolved items, and claim-to-plan consistency.

#### Scenario: Complete workstream report
- **WHEN** a role submits completion
- **THEN** every numbered step SHALL be marked `completed`, `partial`, `blocked`, or `not_started`
- **AND** the completion claim SHALL be consistent with those statuses and cited current evidence.

#### Scenario: Missing or contradictory plan evidence
- **WHEN** a mechanically valid report omits the plan subsection, leaves steps unaccounted, or claims completion while a required step is partial or blocked
- **THEN** Runtime SHALL NOT invent or repair the plan
- **AND** Reviewer SHALL treat the gap as a quality/audit failure and block whenever required completeness or evidence cannot be trusted.

### Requirement: Controller remains a mechanical coordinator
FlowPilot SHALL NOT require Controller to invent or submit a substantive project workstream plan; Controller's current foreground action/duty ledger remains the sole machine-owned coordination plan for Controller.

#### Scenario: Controller relays a role packet
- **WHEN** Controller delivers current metadata or follows the current foreground duty
- **THEN** Controller SHALL use the existing Runtime-derived action ledger
- **AND** SHALL NOT create a competing product plan, role plan, route tree, or acceptance authority.

### Requirement: Route leaves are independently accountable complete workstreams
FlowPilot SHALL define a dispatchable leaf as the smallest independently accountable complete workstream with one coherent outcome, accepted scope, proof boundary, dependency boundary, and failure boundary, not as the smallest literal action.

#### Scenario: Leaf contains several local execution steps
- **WHEN** one role can complete an accepted outcome through multiple ordered local steps, bounded helper delegation, verification, and repair without changing PM-owned boundaries
- **THEN** the route MAY keep that work as one leaf
- **AND** Reviewer SHALL NOT require fragmentation merely because the role wrote a multi-step local plan.

#### Scenario: Leaf leaks PM authority
- **WHEN** completing a proposed leaf requires the role to invent product scope, acceptance criteria, route children, cross-node dependency order, or another role's authority
- **THEN** Reviewer SHALL block the plan or result through the existing PM repair/route mutation path.

### Requirement: PM operates FlowPilot as a high-standard long project
PM SHALL treat every FlowPilot invocation as a complex, long-running, high-standard project and SHALL own product ambition, architecture, route depth, acceptance, integration, Reviewer finding disposition, and final closure.

#### Scenario: Local results pass but the project is incoherent
- **WHEN** packet results are locally complete but upstream use, downstream handoff, sibling fit, parent contribution, or final artifact coherence is missing
- **THEN** PM SHALL use an existing rework, blocker, role-work, or route mutation path instead of marking the project complete.

#### Scenario: Reviewer score is below target
- **WHEN** Reviewer returns a quality score below 9/10 while the minimum hard contract may still be satisfied
- **THEN** PM SHALL explicitly repair, add work, accept with evidence-based rationale, waive with authority, or stop
- **AND** SHALL NOT silently ignore the score or treat the numeric score alone as a Runtime hard block.

### Requirement: Role-local FlowGuard cannot self-approve
Any substantive role MAY use FlowGuard inside its authorized workstream when process, state, transition, coverage, or evidence-freshness risk warrants it, but the resulting local model SHALL NOT approve that role's own output or replace the formal independent FlowGuard or Reviewer gate.

#### Scenario: Worker uses role-local FlowGuard
- **WHEN** Worker models a risky state transition to improve its in-scope implementation
- **THEN** Worker SHALL cite the model and check evidence in the current result
- **AND** the normal PM absorption, formal FlowGuard boundary, and Reviewer decision SHALL remain independently required when applicable.

