## ADDED Requirements

### Requirement: Field-Bearing Changes Have Lifecycle Ownership
FlowPilot SHALL review every behavior-bearing runtime, prompt, packet, result,
contract, or OpenSpec field surface with field lifecycle ownership before
claiming the field-bearing change complete.

#### Scenario: New or disputed field is present
- **WHEN** a maintenance change adds, preserves, reclassifies, or disputes a field such as `pm_visible_summary`, `recent_role_report_summary`, or `authorized_result_reads`
- **THEN** the change SHALL name the field owner, readers, writers, lifecycle, behavior projection, old-field disposition, and downstream validation route.

#### Scenario: Field is not necessary
- **WHEN** an existing packet, result, gate, blocker, route node, or run-local evidence surface can express the same repair without a new field
- **THEN** FlowPilot SHALL shrink or reject the field proposal instead of expanding the runtime contract.

### Requirement: Field Review Does Not Create Compatibility
FlowPilot SHALL NOT preserve old fields, aliases, generated substitutes,
fallback wrappers, or optional alternate shapes unless explicit compatibility
intent and current evidence are recorded.

#### Scenario: Unsupported field is submitted
- **WHEN** a role result, packet, prompt contract, or fixture submits an unsupported old or alternate field
- **THEN** runtime or validation SHALL reject it through the current contract path
- **AND** it SHALL NOT silently map the field to a supported current field.

### Requirement: Authorized Read Surfaces Stay Mechanical
If authorized result-read surfaces remain canonical, FlowPilot SHALL treat them
as mechanical access gates, not semantic summary or review-quality gates.

#### Scenario: Required read is missing
- **WHEN** a packet result is submitted before a required authorized result body was opened
- **THEN** runtime may mechanically reject or block the submission using current packet/result/receipt evidence
- **AND** runtime SHALL NOT infer whether the PM, Reviewer, or FlowGuard operator semantically understood the body.
