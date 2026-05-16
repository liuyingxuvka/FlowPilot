## Context

Existing FlowPilot work already has these pieces:

- Card and packet text says ACK is not completion.
- Controller standby exposes Router-authored wait targets and performs
  reminder/liveness cycles.
- Role recovery can settle or reissue obligations after a role is restored.
- Controller action rows support replacement/superseded links.

The new behavior should compose those mechanisms. It must not let Controller
invent work, read sealed bodies, approve progress, or replace roles on its own.

## Decisions

### Universal ACK continuation text

Work cards and packets must say the same thing in operational language:

- ACK is only receipt.
- If the card or packet asks for an output, report, decision, result, or
  blocker, it is a work item.
- After ACK, the role must continue immediately and submit through the
  Router-directed runtime path.
- The task is unfinished until Router receives the expected output or blocker.

Role identity cards remain different: after role-card ACK, the role waits for a
separate authorized work card, packet, event, lease, or output contract.

### No-output is a work-attempt failure, not role death

Controller's wait-target check should not collapse all missing results into
role recovery. If the role is reachable but there is no output and no evidence
that it is still working, Router creates a replacement attempt for the same
wait. The old wait is marked `superseded` only after the replacement row exists.

### Retry budget is bounded

No-output reissue uses a small Router-owned retry budget. If the same wait is
already a no-output retry at the budget limit, Router writes a control blocker
for PM handling instead of looping forever.

### Unavailable still means recovery

Missing, cancelled, unknown, unresponsive, and lost roles still enter the
existing role-recovery path. Ambiguous task semantics still go to PM.

## Flow

```text
role ACKed work
  -> Router waits for report/result
  -> Controller reminder/liveness check due
  -> still working: continue standby
  -> no output and not still working: Router writes replacement attempt
  -> unavailable: existing role recovery
  -> ambiguous/retry budget exhausted: PM/control blocker
```

## Risks

- Duplicate results: replacement rows must link to and supersede originals so
  late old outputs can be treated as stale.
- Infinite retries: no-output reissue has a bounded attempt count.
- Controller role creep: Controller reports observed status only; Router owns
  replacement creation.
