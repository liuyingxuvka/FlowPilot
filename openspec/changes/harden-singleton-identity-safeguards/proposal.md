## Why

FlowPilot already has strong duplicate-event and replacement-route defenses, but several current risk families still depend on developers mentally separating intended plurality from illegal duplicate authority. This change makes singleton ownership explicit, model-backed, and install-visible so FlowPilot can catch "should be one but two exist" failures before they become stale runtime state or overclaimed confidence.

## What Changes

- Add a singleton identity authority capability that inventories FlowPilot objects by scope, owner, identity key, generation/version, legal replay behavior, conflict behavior, and old-object disposition.
- Add a focused FlowGuard model/checker for duplicate singleton hazards across daemon writers, active packets, PM dispositions, route replacement, material progress generation, ACK/output waits, and final closure evidence.
- Add live-run audit evidence that classifies current `.flowpilot` state as safe, risky, or evidence-insufficient for singleton/duplicate conflicts without rewriting peer-agent work.
- Connect the new evidence to model maturation, model-test-code diagnostics, install readiness, and background regression reporting.
- Refresh the installed FlowPilot skill from repository-owned source after the implementation and verify local install freshness.

## Capabilities

### New Capabilities
- `singleton-identity-authority`: Defines the authority matrix and model-backed checks for singleton-vs-plural FlowPilot state.

### Modified Capabilities
- `parallel-flowpilot-run-isolation`: Clarifies that multiple active/background runs or Flow blocks are legal only when run-targeted authority stays explicit.
- `persistent-router-daemon`: Extends daemon singleton evidence to the shared singleton audit surface.
- `pm-package-disposition-semantics`: Requires package disposition singleton evidence to be represented in the authority matrix and duplicate hazard model.
- `material-progress-generation-projection`: Requires generation-scoped progress ownership to be part of singleton duplicate checks.
- `route-repair-replacement-policy`: Requires replacement-route old-object disposition to be part of singleton duplicate checks.
- `wait-reconciliation`: Requires ACK settlement versus durable output completion to be part of singleton duplicate checks.
- `flowguard-model-maturation-closure`: Consumes singleton duplicate gaps as maturation signals before broad confidence.
- `model-test-code-diagnostic-gap-closure`: Reports singleton authority gaps and stale evidence in diagnostic output.

## Impact

- Adds OpenSpec artifacts under `openspec/changes/harden-singleton-identity-safeguards/`.
- Adds focused FlowGuard model/check/result files under `simulations/`.
- Adds singleton authority documentation under `docs/`.
- Extends install readiness and model-test-code diagnostics to include singleton duplicate evidence.
- Updates targeted tests for singleton duplicate hazards and evidence reporting.
- Runs targeted and heavyweight regressions using repository background artifact conventions.
- Syncs the installed local FlowPilot skill after repository source changes.
