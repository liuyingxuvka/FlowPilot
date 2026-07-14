## MODIFIED Requirements

### Requirement: Executable worker packets require in-scope repair
FlowPilot SHALL require PM-authored executable worker packets to tell the addressed worker to understand the complete packet outcome, write a numbered local plan, execute and integrate all in-scope steps, self-check, repair defects inside the packet's allowed reads/writes, acceptance slice, role authority, and verification requirements, rerun the required checks, and only then return completion with per-step evidence.

#### Scenario: Worker completes and repairs a packet-scoped workstream
- **WHEN** PM issues a current-node, implementation, or repair packet to a Worker
- **THEN** the packet guidance requires the Worker to plan the whole accepted outcome, fix in-scope defects, rerun required evidence, and report every numbered step before returning completion.

#### Scenario: Worker escalates out-of-scope defect
- **WHEN** the Worker finds a defect that requires broader scope, changed acceptance, another role's authority, route mutation, or forbidden writes
- **THEN** the packet guidance requires a blocker, `needs_pm`, or PM Suggestion Item instead of silent repair or local replanning of PM authority.

### Requirement: Evidence and model packets self-correct only their own outputs
FlowPilot SHALL require research/evidence and FlowGuard report/model packets to plan and complete their own full evidence or modeling workstream and correct defects in their own report, model, or evidence before returning, while routing target-product, implementation, route, or authority defects as formal findings, blockers, or PM Suggestion Items unless the packet explicitly grants bounded write authority.

#### Scenario: Ordinary evidence packet reports target defect
- **WHEN** a research/evidence role finds a target implementation or route defect outside its allowed writes
- **THEN** the role reports the defect through its result, blocker, or PM Suggestion Item instead of repairing the target artifact.

#### Scenario: FlowGuard Operator corrects model evidence
- **WHEN** a FlowGuard Operator finds a defect in its model, check command, counterexample interpretation, or report evidence
- **THEN** the Operator corrects that model/report output before returning and reports product or process defects to PM for decision.

## ADDED Requirements

### Requirement: Every substantive role reports plan status in the shared self-check
Generic output-contract guidance and role cards SHALL require the common plan/status/evidence subsection for PM, Worker, research/evidence Worker, Reviewer, FlowGuard Operator, and substantive helper outputs without changing Controller authority.

#### Scenario: Generic PM role-work targets any substantive role
- **WHEN** the existing PM role-work packet targets a substantive role
- **THEN** the current handoff SHALL carry the common complete-workstream instruction
- **AND** the role-specific card SHALL preserve that role's write, review, decision, and self-approval boundaries.
