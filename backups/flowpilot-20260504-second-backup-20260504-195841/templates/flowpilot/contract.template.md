# Frozen Contract

## Task

<task-summary>

## Acceptance Criteria

- <criterion-1>
- <criterion-2>
- <criterion-3>

## Explicit Constraints

- Keep the original completion standard intact.
- Stop for hard gates listed in `mode.json`.
- Treat skipped checks as skipped, not passed.
- Preserve user-owned changes outside the active scope.

## Pre-Freeze Product Function Architecture

- Product function architecture: `.flowpilot/runs/<run-id>/product_function_architecture.json`
- Root acceptance contract: `.flowpilot/runs/<run-id>/root_acceptance_contract.json`
- Standard scenario pack: `.flowpilot/runs/<run-id>/standard_scenario_pack.json`
- PM synthesis: `<path-or-null>`
- Product FlowGuard officer modelability approval: `<path-or-null>`
- Human-like reviewer usefulness challenge: `<path-or-null>`

The acceptance criteria below are frozen from the approved product-function
architecture. Later route updates may refine models or evidence, but they must
not silently remove PM-approved functional requirements, missing-feature
decisions, display rationale, or negative scope.

## Evidence Required For Completion

- Active route checked by FlowGuard.
- Product-function architecture evidence written and approved before contract
  freeze.
- Root-level hard requirements, high-risk proof obligations, and standard
  scenarios selected before contract freeze.
- Node-level acceptance plans written before each implementation chunk or node
  checkpoint.
- Required capability evidence written.
- Formal chunks verified.
- Subagent work, if any, merged through an authorized integration/review packet.
- Final verification passed.
- Residual risk triage completed with zero unresolved residual risks.
- Terminal closure suite passed after final state/evidence refresh.
- Final report emitted.

## Approved Contract Changes

Record only explicit user-approved changes here. Do not silently reinterpret the
contract during route updates.
