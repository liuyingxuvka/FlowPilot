## Why

Recent FlowPilot runs exposed a split packet protocol. The current
`flowpilot_new.py` path already completes packets through a dynamic lease,
ACK, and result submission, while an older strict packet-runtime path still
requires a `controller_relay` signature before packet/result bodies can be
opened. That strict relay field blocked valid FlowGuard work packets even
though the Controller never produces such a relay in the current runtime.

## What Changes

- Make `flowpilot_new.py lease-agent -> ack -> submit-result` the canonical
  FlowPilot work-packet protocol.
- Remove `controller_relay` as a required packet/result field, audit field, and
  body-open precondition.
- Update runtime cards and packet-open authority modeling so roles do not wait
  for Controller relay signatures after current-run assignment/ACK authority.
- Remove user-facing/runtime CLI surfaces that ask Controller to sign a relay
  envelope.
- Keep sealed body and role/hash checks, but do not add compatibility fallbacks
  for the removed relay field.
- Sync the repository-owned FlowPilot skill to the local installed skill after
  validation.

## Capabilities

### Modified Capabilities

- `new-flowpilot-formal-entrypoint`: current runs use lease/ACK/result as the
  only work-packet completion path.
- `flowpilot-prompt-boundary-policy`: role cards must not instruct current
  roles to use `open-packet`, `run-packet`, or Controller relay signatures for
  current work-packet authority.
- `flowpilot-packet-open-authority`: opening or completing a packet must be
  authorized by current assignment plus role/hash checks, not by
  `controller_relay`.

## Impact

- Affected runtime code: packet body/result body open checks, result write
  checks, unified packet runtime CLI dispatch, and packet-chain audit wording.
- Affected prompt cards: PM, Worker, FlowGuard operator, packet identity
  boundary, and related role-card coverage expectations.
- Affected models/checks: packet-open authority and targeted new-only runtime
  checks.
- Affected install flow: repository-owned FlowPilot skill must be synced to the
  local installed skill, then audited for freshness.
