## Context

The prior complete-system runtime work built the new runtime core under
`ai_project_runtime`. The missing piece is the fresh formal entrypoint: the
user should be able to ask for FlowPilot, get the familiar startup panel, and
then have all later authority live in the new ledger.

The old FlowPilot router is not the product model for new runs. It remains
useful as historical source material and diagnostic tooling, but a new run
must not depend on old route state, fixed six-role startup, old agent ids, or
old display projections.

## Decisions

### Decision: New entrypoint, reused startup UI

`flowpilot_new.py start` creates a fresh new run shell, launches the existing
PowerShell/WPF startup intake UI, validates the result, records sealed startup
intake into the new ledger, freezes the contract, creates the first route, and
issues the first PM packet.

The startup UI is the only reused UI. There is no separate monitoring UI
requirement. Status is public projection from the ledger.

### Decision: Headless startup is rehearsal-only

Tests can use the startup UI's existing headless mode to generate artifacts,
but the formal entrypoint rejects headless output as formal launch evidence.
This preserves a real user-facing startup boundary while keeping automated
regression checks deterministic.

### Decision: Dynamic leases replace fixed startup crew

The new entrypoint returns a `lease_agent` next action for the requested
responsibility. The foreground controller or host layer records the real
`agent_id` back into the ledger. It does not spawn a fixed six-agent startup
crew.

### Decision: End-to-end proof has two layers

- Rehearsal proof: deterministic headless startup and fake host run, used by
  tests and FlowGuard regression.
- Formal proof: interactive startup UI and live host agent evidence when a real
  user run is executed.

The final product must not confuse these layers.

## Risks

- If `SKILL.md` still points to `flowpilot_router.py start`, users will keep
  launching the old path.
- If headless startup output is accepted as formal evidence, tests can
  overclaim real launch behavior.
- If a status projection or chat text includes the startup body, prompt
  isolation is broken.
- If the runtime requires fixed six roles, it recreates the old topology
  problem instead of the requested dynamic agent model.
