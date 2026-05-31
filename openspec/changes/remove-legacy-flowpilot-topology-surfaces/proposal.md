## Why

FlowPilot now uses the new `flowpilot_new.py` runtime with on-demand requested responsibilities, lifecycle guard authority, native startup intake, and a single `flowguard_operator` responsibility for FlowGuard work. Several active specs, prompts, templates, docs, and runtime/test surfaces still describe the older fixed topology, Process/Product-scope FlowGuard operator split, validator/Closure Officer packet path, and old Router daemon as current behavior.

## What Changes

- **BREAKING** Remove the current-authority concept of a fixed six-role or fixed worker runtime roles from active FlowPilot prompts, templates, docs, models, and tests.
- **BREAKING** Replace old Process/Product-scope FlowGuard operator role names with the single requested `flowguard_operator` responsibility where FlowGuard work is needed.
- **BREAKING** Remove Validator and Closure Officer as current role/packet responsibilities; validation and closure remain system/router/PM-governed ledger outcomes.
- **BREAKING** Treat old Router daemon, Controller action ledger, `controller-standby`, and `flowpilot_router.py` patrol wording as old-run diagnostics unless a current file is explicitly documenting the legacy Router path.
- Update active OpenSpec change artifacts that still teach the older topology as current behavior.
- Update runtime API/test/model wording and expectations without adding compatibility aliases for the old responsibility names.
- Synchronize the installed FlowPilot skill and commit the local repository result after validation.

## Capabilities

### New Capabilities

- `flowpilot-topology-language-contract`: Active FlowPilot surfaces describe only the new requested-responsibility runtime topology and reject old fixed-role topology as current authority.

### Modified Capabilities

- `runtime-requested-role-bindings`: requested responsibilities are not backed by a fixed startup cohort or old role aliases.
- `flowpilot-prompt-boundary-policy`: active prompts and docs must not present old Router daemon, fixed runtime roles, Process/Product-scope FlowGuard operator, Validator, or Closure Officer language as current instructions.
- `resume-rehydration-obligation-replay`: resume restoration applies only to currently required requested responsibilities.
- `FlowGuard operator-packet-lifecycle`: FlowGuard work routes to the explicit `flowguard_operator` responsibility instead of old Process/Product-scope FlowGuard operator responsibilities.

## Impact

- Affected files include `skills/flowpilot/SKILL.md`, runtime kit prompts/cards, protocol reference docs, public README/docs, `templates/flowpilot`, OpenSpec active changes, `flowpilot_core_runtime`, tests, simulations, generated result artifacts, and install sync checks.
- This intentionally changes current local runtime/test behavior for old role names. No old compatibility aliases will be added.
- Historical archive artifacts may keep old terminology only when clearly archival and not used as current runtime, prompt, install, or validation authority.
