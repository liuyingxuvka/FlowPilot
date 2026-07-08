## ADDED Requirements

### Requirement: Prompt Cards Preserve Core Deliverables Without Runtime Semantics
FlowPilot prompt cards SHALL require PM, Reviewer, and FlowGuard operator roles to preserve the user's concrete deliverable, scope, quantity, quality, required material or evidence, and prohibitions without adding runtime semantic enforcement.

#### Scenario: PM prompt preserves concrete target
- **WHEN** PM converts a user request into startup intake, root contract, route skeleton, node acceptance, material handling, research handling, final ledger, or closure content
- **THEN** the prompt SHALL require PM to preserve the concrete source-intent target instead of weakening it into generic completion, reachable-only inventory, status-only reporting, or report-only evidence.

#### Scenario: Runtime stays mechanical
- **WHEN** prompt-card validation inspects runtime/router source
- **THEN** runtime/router source SHALL NOT contain semantic non-downgrade comparison duties, reachable-only keyword matching, or core-deliverable semantic pass/fail logic.
