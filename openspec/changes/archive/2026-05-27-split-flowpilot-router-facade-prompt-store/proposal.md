## Why

`skills/flowpilot/assets/flowpilot_router.py` is still too large to maintain
confidently. The current file has about 37k lines and 940 top-level functions,
even after prior cleanup. Several behavior families have already been split,
but prompt text, card-delivery helpers, card-return settlement, controller
ledger logic, bootloader/startup routing, external event dispatch, repair
transactions, PM role-work, route frontier, and terminal ledgers still share one
large module.

The next maintenance pass needs an explicit target map instead of opportunistic
line shaving. It should keep the public router facade stable, move prompt text
and behavior families behind clear modules, and use FlowGuard to reject splits
that lose entrypoints, duplicate state ownership, omit prompt assets, or
overclaim progress-only validation.

## What Changes

- Add a PromptStore boundary backed by `runtime_kit/prompts/` for prompt-like
  control text that is currently embedded in Python.
- Split the router in waves by behavior family while keeping
  `flowpilot_router.py` as the public facade and compatibility entrypoint.
- Treat modules as domain owners, not one-function files; the target is roughly
  18-24 cohesive modules rather than hundreds of tiny scripts.
- Add FlowGuard checks for the router split hazards: missing facade,
  duplicate state owner, micro-module explosion, missing prompt asset, stale
  prompt hash, unsafe inline fallback, and incomplete background evidence.
- Update install checks, docs, local installed skill copy, and git history after
  validation.

## Impact

- Public behavior: intended to remain compatible.
- Prompt storage: prompt content moves from Python literals into versioned
  runtime-kit assets where practical.
- Test behavior: focused tests should cover PromptStore and each split family;
  long router and Meta/Capability checks run through background artifacts.
- Release behavior: no publish/release action is included in this change.
