## Why

The first live run of the new FlowPilot formal entrypoint reached terminal
closure, but it exposed an asymmetry in the workflow model. The PM received a
real work packet, while FlowGuard and Reviewer were still represented as
special side commands. That let the run finish, but it left non-PM background
roles with inconsistent lease and status projection behavior.

The new FlowPilot should be clean, not compatible with the flawed side-command
path. Every backend agent role should enter through the same packet lifecycle:
packet -> lease -> ACK -> result -> ledger side effect -> next packet.

## What Changes

- Add a symmetric work-packet lifecycle for PM, explicit FlowGuard operator,
  Reviewer, and requested worker-class responsibilities.
- Add explicit packet kinds so the runtime knows what side effect a packet
  result is allowed to commit.
- Retire public formal-flow guidance for direct FlowGuard/review/validation/
  close commands.
- Add FlowGuard model coverage and tests for the exact live-run miss: explicit
  FlowGuard operator responsibilities must be leaseable through packets, and
  Reviewer must not leave an empty-packet active lease projection.

## Impact

- New formal FlowPilot runs proceed through a chain of role-specific packets.
- FlowGuard operator and Reviewer responsibilities are ordinary work-package
  responsibilities, not command-side exceptions.
- The live-run failure becomes a regression, not an informal note.
