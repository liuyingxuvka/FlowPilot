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
- Required capability evidence written.
- Formal chunks verified.
- Subagent work, if any, merged by the main agent.
- Final verification passed.
- Final report emitted.

## Approved Contract Changes

Record only explicit user-approved changes here. Do not silently reinterpret the
contract during route updates.
