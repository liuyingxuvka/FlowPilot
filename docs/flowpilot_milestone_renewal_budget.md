# FlowPilot Milestone-Renewal Lightweight Budget

This is an execution-shape budget for the current direct renewal loop. It is
not a second route authority, a score, or a planning level.

## Accepted shape

- One top-level milestone boundary creates one fresh audit and one fresh
  remaining route plan.
- The normal gate path has six role handoffs: PM, FlowGuard review, PM
  absorption, Reviewer, system validation, and commit.
- A failed gate reopens the same current obligation with a fresh packet. It
  does not copy the old plan forward or create another plan hierarchy.
- Nested child work stays on the existing parent-composition path and does not
  trigger the global renewal gate.

## Measured local envelope

The current contract projection was measured with compact JSON encoding:

| remaining nodes | serialized renewal shape |
| ---: | ---: |
| 1 | 903 bytes |
| 3 | 1,473 bytes |
| 8 | 2,898 bytes |
| 16 | 5,202 bytes |

The 16-node row is an observation boundary for review, not a new runtime
hard gate. A reviewer should request decomposition when the audit transport
becomes materially larger than this envelope instead of adding another plan
level.

The focused PPA maintenance proof completed in 10.33 seconds locally (14
tests passed). This is test-run latency, not a promise about model-provider
latency. Provider latency remains governed by the existing liveness and
current-receipt rules.

## Regression guard

The budget is considered preserved when the current model and affected tests
continue to show: one direct renewal loop, no L0-L4 language or modes, one
current audit/plan pair, exact owner bindings for remaining obligations, and
no fallback or historical-plan continuation.
