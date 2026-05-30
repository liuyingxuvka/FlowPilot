## Why

FlowPilot's new runtime already leases role work on demand through
`lease_agent`, but several active prompts, protocol documents, models, and
tests still carry fixed-crew wording. That wording can pull agents back toward
historical startup semantics instead of the current runtime-requested role
binding flow.

## What Changes

- Replace active prompt wording that names fixed role counts with direct
  runtime-requested role binding language.
- Treat concrete host mechanisms as implementation details behind an
  addressable role binding.
- Preserve evidence boundaries: each requested role binding still needs a
  current-run id, ACK, runtime-visible result submission, and sealed-body
  isolation.
- Update protocol docs and reference docs so they do not reintroduce historical
  fixed-crew concepts as active authority.
- Update FlowGuard models and focused tests so they validate current requested
  role bindings instead of fixed startup cohorts.
- Synchronize the installed FlowPilot skill after validation.

## Capabilities

### New Capabilities
- `runtime-requested-role-bindings`: FlowPilot binds only roles requested by the
  current runtime action, using host-supported addressable role mechanisms.

### Modified Capabilities
- `flowpilot-prompt-boundary-policy`: prompt cards must use current requested
  role binding language and must not preserve historical fixed-crew wording as
  active instruction.
- `resume-rehydration-obligation-replay`: resume and recovery checks apply to
  current runtime-required role bindings instead of an unconditional full role
  cohort.

## Impact

- Active FlowPilot skill prompt and runtime kit cards/prompts.
- Public protocol/schema/reviewer docs and skill reference docs.
- FlowGuard development/startup/recovery models and focused tests that
  currently encode historical role topology as active policy.
- Install validation and installed Codex skill synchronization.
