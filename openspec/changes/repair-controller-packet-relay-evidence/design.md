## Context

FlowPilot packet security already requires a target role to verify a Controller relay signature before opening a sealed packet body. The low-level packet runtime can write that signature through `controller_relay_envelope`, but the unified Controller runtime surface does not expose an explicit relay command, and Router relay actions currently describe the relay intent without giving Controller a concrete runtime operation list. A Controller can therefore send envelope paths in chat and write a `done` receipt while the envelope and packet ledger still lack relay evidence.

The observed failure was a model miss in the control plane: the safety check correctly blocked Worker open, but the liveness/recovery path treated the missing relay evidence as a postcondition failure that retried and escalated instead of a Controller-owned mechanical repair.

## Goals / Non-Goals

**Goals:**

- Make packet/result relay a first-class Controller runtime operation.
- Make Router relay rows carry concrete runtime relay operations and expected evidence.
- Ensure relay `done` receipts close only from verified envelope/ledger/lease evidence.
- Route missing relay evidence to Controller mechanical repair before PM/control-blocker escalation.
- Preserve the sealed-body boundary and Worker open strictness.
- Add FlowGuard and ordinary regression coverage for the observed bad path and a same-class generalized bad case.

**Non-Goals:**

- Do not let Controller read, summarize, repair, or execute sealed packet/result bodies.
- Do not make Worker accept path-only chat handoffs.
- Do not convert normal Controller relay actions into Router-internal hidden delivery.
- Do not change the semantic PM repair policy except for the routing boundary around mechanical missing-relay evidence.

## Decisions

### Decision 1: Add a unified Controller runtime relay command

Add a `flowpilot_runtime.py` command for Controller relay instead of requiring Controller to know the lower-level `packet_runtime.py relay` surface. The command will load a packet or result envelope, call the existing packet runtime relay helper, and print compact JSON evidence. It will not read sealed bodies.

Alternative considered: only update prompts to call the lower-level CLI. That leaves the common FlowPilot runtime surface incomplete and keeps the same ambiguity that caused the miss.

### Decision 2: Put executable relay operations into Router action payloads

Relay action builders will add a structured list such as `runtime_relay_operations` for each envelope. Each operation names the envelope path, target role, source role, packet id, expected relay evidence, and active-holder lease expectation where relevant.

Alternative considered: rely on `allowed_reads`/`allowed_writes` and prose summaries. That is not enough because Controller needs a concrete operation, not only a permission boundary.

### Decision 3: Treat missing relay evidence as Controller repairable when packet files are otherwise valid

Receipt reconciliation will keep verifying evidence from Router-visible files. If a `done` receipt lacks relay evidence but the packet/result envelope exists and is otherwise relayable, Router will schedule a Controller mechanical relay repair row or replay operation before materializing a PM/control blocker.

Alternative considered: keep the retry-then-blocker path. That is too coarse: a missing relay signature is usually a mechanical omission, not a PM route decision.

### Decision 4: Preserve Worker open strictness

Worker `open-packet` continues to reject envelopes with missing Controller relay signatures. The repair happens before Worker open authority, not by weakening Worker verification.

Alternative considered: let Worker open from Controller chat context. That breaks sealed packet authority and would hide the root cause.

## Risks / Trade-offs

- New runtime command duplicates lower-level relay CLI semantics -> mitigate by delegating to existing `packet_runtime.controller_relay_envelope`.
- Relay action payloads may need similar changes across material, research, current-node, and PM role-work packet families -> mitigate by using a shared builder/helper where practical and adding registry/diagnostic coverage.
- Repair scheduling may mask truly invalid packets if it is too broad -> mitigate by allowing Controller repair only when the envelope can be loaded, target role is known, and relay readiness checks pass; otherwise keep PM/control-blocker routing.
- Background regression evidence can look alive before it is complete -> mitigate by inspecting exit artifacts and logs before reporting completion.
