## Why

FlowPilot already has extensive FlowGuard models and validation evidence, but a passing model/test result can still leave the model too coarse, stale, or only safe for a scoped claim. FlowGuard 0.27 now provides a model maturation loop, so FlowPilot should promote post-evidence model gaps into explicit model-upgrade, evidence-refresh, or confidence-downgrade obligations before broad confidence claims.

## What Changes

- Add a first-class FlowGuard model maturation closure gate for FlowPilot maintenance and release confidence.
- Convert post-evidence findings into concrete model actions: add state fields, add transition cases, add invariants or obligations, add code-boundary observations, split child models, reattach parent evidence, refresh stale evidence, or downgrade claims.
- Strengthen ACK and role-output reconciliation so ACK wait settlement is modeled separately from durable semantic output completion.
- Strengthen route replacement modeling so old active packets and superseded branch evidence have explicit disposition before a replacement route can become current.
- Treat prompt/card assets and manifests as executable contract inputs for model/code/test alignment.
- Require final background artifacts before long-running model and test checks can count as evidence.
- Add parent/child maturation visibility for oversized parent model families such as Meta, Capability, and control-plane friction.
- Keep peer-agent work safe by preserving dirty worktree boundaries and making validation freshness explicit.

## Capabilities

### New Capabilities
- `flowguard-model-maturation-closure`: FlowPilot maintenance and release confidence must consume FlowGuard model maturation signals before broad confidence claims.

### Modified Capabilities
- `wait-reconciliation`: ACK settlement and role-output completion become separate modeled obligations.
- `route-repair-replacement-policy`: Replacement activation must explicitly dispose old active packets and parent/child reattachment evidence.
- `flowpilot-prompt-boundary-policy`: Prompt/card assets and manifests become model-visible contract inputs.
- `flowguard-background-observability`: Background model/test evidence must be final artifact-bound proof, not progress-only liveness.
- `flowguard-model-hierarchy`: Oversized parent models must expose child-level maturation and stale-evidence status.
- `model-test-code-diagnostic-gap-closure`: Diagnostics must feed model maturation actions instead of stopping at coverage rows.

## Impact

- Affected model and check scripts under `simulations/`.
- Affected OpenSpec specs under `openspec/specs/`.
- Affected installed skill/runtime validation surfaces under `skills/flowpilot/`, `scripts/check_install.py`, and sync/audit scripts when needed.
- No frozen acceptance contract, publication, deployment, or destructive operation is changed by this proposal.
