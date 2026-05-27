## Why

FlowPilot's runtime owner modules are now model-code-test aligned, but the broader maintenance surface still needs a final convergence pass so future maintainers can quickly localize bugs across models, tests, scripts, prompts, installation checks, and peer-completed work.

## What Changes

- Validate and adopt the completed peer-agent changes for shared skill maintenance bookkeeping and FlowGuard satellite skill reminders.
- Add an explicit ideal-state maintenance map that records owner modules, facades, script entries, test tiers, large-file pressure, and model-code-test diagnostic status.
- Perform low-risk facade-preserving cleanup only where the model/test/script boundary is clear and current validation can prove behavior did not change.
- Strengthen checks and documentation so future bug localization starts from owner/module/test-tier evidence instead of manually searching large files.
- Sync the installed FlowPilot skill, run the required FlowGuard/OpenSpec/test gates, and commit the validated repository state locally.

## Capabilities

### New Capabilities

- `flowpilot-maintenance-ideal-state`: governs final maintainability convergence across structure maps, peer-completed changes, validation freshness, and local install/git synchronization.

## Impact

- Affected code: targeted `simulations/`, `scripts/`, `skills/flowpilot/assets/`, templates, and tests selected by current evidence.
- Affected evidence: FlowGuard model results, model-test-code diagnostic results, OpenSpec validation, install sync/audit, and adoption log entries.
- No public CLI, skill, prompt, runtime data contract, or GitHub release behavior is intended to break.
