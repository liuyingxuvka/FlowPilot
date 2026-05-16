## Context

Controller is the foreground role that most often talks to the user while
FlowPilot is running. It also reads technical artifacts such as action ledgers,
packet envelopes, receipts, waits, scheduler barriers, and diagnostic paths.
Those terms are useful inside the control plane, but they are not the best
default language for user status updates.

The current implementation already includes a Controller user-reporting policy.
The weak point is prompt visibility: the policy is easy to miss because it is
nested in action metadata and the table-local prompt is dominated by internal
row-processing rules.

## Goals

- Make the existing plain-language rule harder to miss in the Controller role
  card.
- Add a short table-local reminder to translate internal action/ledger terms
  before mentioning Controller work to the user.
- Keep the language advisory rather than absolute: technical names remain
  allowed when the user asks for detail or when diagnosing a blocker requires
  them.
- Preserve all existing route, display, Mermaid, packet, and authority
  behavior.

## Non-Goals

- Do not add a Router-generated plain summary sentence.
- Do not add a fixed user-report template.
- Do not rewrite Route Sign or Mermaid content.
- Do not hide all internal terms under every circumstance.
- Do not change Controller, PM, worker, or reviewer authority.

## Decisions

- Put the strongest instruction in the Controller core card because it is the
  durable role instruction.
- Repeat a compact version in `controller_table_prompt` because long-running
  foreground Controller work repeatedly reads that generated work board.
- Validate by checking prompt text and extending the existing FlowGuard
  control-plane friction model. This keeps the change aligned with the current
  model instead of creating a separate user-facing framework.
