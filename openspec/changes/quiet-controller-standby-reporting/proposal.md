## Why

FlowPilot's foreground Controller currently patrols quiet waits every ten seconds and may surface low-value process chatter to the user. This makes long FlowPilot runs feel noisy even when the background Router daemon is healthy and no user action is needed.

## What Changes

- Change the default quiet foreground Controller patrol interval from 10 seconds to 60 seconds while preserving the Router daemon's one-second internal tick.
- Add an explicit Controller reporting budget: quiet patrol, receipts, ledger cleanup, and process-only asides are silent by default.
- Keep user-facing updates for state changes, required user action, blockers/recovery, terminal summaries, and explicit user status requests.
- Preserve existing anti-exit semantics: Controller must stay attached during nonterminal FlowPilot runs and may not treat patrol timeout, `continue_patrol`, or status display projection as completion.
- Sync runtime prompts, role cards, OpenSpec specs, FlowGuard models, targeted tests, local installed skill, and local git state.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `controller-patrol-timer`: default quiet standby patrol interval changes to 60 seconds without changing daemon tick or stop authority.
- `controller-user-status`: user-visible Controller reports gain an explicit speak/silence budget.
- `controller-user-language-guidance`: plain-language guidance is narrowed so Controller first decides whether a message is needed at all.
- `controller-process-asides`: process asides remain Controller-only operational context and do not require user-visible relays.

## Impact

- Affects FlowPilot Controller role cards, resume cards, generated Controller table prompts, patrol timer defaults, standby payloads, and focused Controller runtime tests.
- Affects FlowGuard patrol/user-status/process-aside model obligations and model check outputs.
- Requires local install sync and install audit because this repository owns the installed `flowpilot` skill assets.
