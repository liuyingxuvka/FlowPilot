## Context

The new formal runtime is now packet-symmetric for requested PM, FlowGuard operator, Reviewer, and worker-class responsibilities. System validation and system closure are runtime ledger outcomes. The latest live-style exercise found two remaining weak spots outside that symmetry.

First, the `lease-agent` CLI already constrains `--host-kind` to `dry_run`, `fake`, or `live`, but the prompt guidance did not spell out that menu in the place where an AI operator needed it. The operator guessed `codex_subagent`, which the CLI correctly rejected.

Second, the FlowGuard operator used the default Meta runner output path. That path is a tracked baseline result file under `simulations/`, so a formal run changed a timestamp in the repository instead of leaving evidence under the run that requested it.

## Goals / Non-Goals

**Goals:**

- Make fixed-value command fields self-contained for AI operators by listing allowed values beside the command guidance.
- Keep the CLI as the final enforcement layer: invalid enum values still fail loudly.
- Give formal FlowPilot FlowGuard packets a run-local evidence location and concrete `--json-out` command pattern.
- Let Meta and Capability runner invocations write results/proofs outside tracked baseline paths when requested.
- Prove the two bug classes through FlowGuard model hazards and ordinary unit tests.

**Non-Goals:**

- Do not reintroduce old FlowPilot compatibility paths.
- Do not add a monitoring UI or change the startup UI.
- Do not make formal runtime packets depend on a fixed six-agent crew.
- Do not stop developers from intentionally updating canonical simulation baselines during repository maintenance.

## Decisions

### Decision: Prompts Carry Explicit Value Menus

FlowPilot skill guidance will include a compact "fixed value menus" section. The first menu covers `--host-kind`:

- `live`: real Codex/multi-agent/background host work.
- `fake`: deterministic fake AI or rehearsal wrapper.
- `dry_run`: no real role agent, diagnostic placeholder.

The prompt also states that `codex_subagent` is not a valid value. That keeps the operator instruction close to the exact command and avoids relying on the user to infer choices from argparse errors.

### Decision: Runtime Packets Carry Evidence Output Policy

FlowGuard operator packet bodies will include an evidence output policy. The policy names `.flowpilot/runs/<run-id>/evidence/flowguard/<packet-id>/` as the normal formal-run evidence root and forbids writing formal-run evidence into tracked `simulations/*_results.json` paths unless the task explicitly says to update baselines.

### Decision: Runner Output Paths Are Optional Overrides

Meta and Capability runners will keep their canonical default paths for normal repository baseline updates. They will also accept `--json-out` and `--proof-out`; full runs can additionally derive or accept run-local thin-parent output paths. This keeps existing workflows working while giving formal packets a clean evidence path.

### Decision: Model The Miss Directly

The new-entrypoint FlowGuard model will include two new obligations:

- a dynamic agent lease cannot be safely bound until the host-kind menu has been presented and the chosen value comes from that menu;
- FlowGuard evidence cannot be safely counted for a formal packet unless it uses a run-local evidence path rather than a tracked simulation baseline.

The model will also include hazards for missing value menus, invented host-kind values, and tracked-baseline FlowGuard evidence.

## Risks / Trade-offs

- [Risk] More prompt text can become stale. -> Keep the menu short and validate it with tests.
- [Risk] Custom output paths might hide intended baseline refreshes. -> Defaults remain canonical; only formal packet guidance and explicit `--json-out` runs use run-local paths.
- [Risk] Full Meta/Capability runs write both layered and thin outputs. -> The override design derives run-local thin output paths when `--full --json-out` is used, so both artifacts stay together.
