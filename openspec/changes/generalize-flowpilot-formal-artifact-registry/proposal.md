## Why

The previous hardening closed the concrete `flowguard_evidence.json` miss, but
it still left the coverage claim too easy to overstate. FlowPilot needs one
runtime-owned registry for AI-submitted formal artifacts so every such file can
be projected into fake-AI Cartesian coverage and executable reissue feedback.

## What Changes

- Add a current-contract formal artifact registry for files that an AI role
  must submit alongside a result body and runtime must mechanically validate.
- Generate synthetic fake-AI formal-artifact cells from that registry instead
  of relying on helper-written happy-path files or hand-copied artifact names.
- Require runtime reissue feedback for every registered formal artifact to name
  the artifact id, current packet-owned target root/path, required internal
  field path, allowed value/type, and body-only insufficiency.
- Keep logical subject artifact ids separate from file-backed formal
  artifacts; they remain current-contract ids, not filesystem fallbacks.
- Preserve current-contract rejection: no old-path promotion, no body-only
  substitute, no wrapper alias, and no compatibility path.

## Capabilities

### New Capabilities

- `formal-artifact-contract-registry`: Registry and closure rules for
  runtime-known AI-submitted formal file artifacts.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: Derive formal-artifact fake-AI cells from
  the registry and fail when a registered artifact lacks required cells.
- `flowpilot-artifact-authority`: Require executable current-contract feedback
  for every registered formal artifact failure.
- `controller-break-glass-repair`: Apply the existing fifth-attempt threshold
  to repeated same-family registered formal artifact failures.

## Impact

- Runtime formal artifact constants and result validation.
- Contract-driven fake-AI responder and ContractExhaustionMesh.
- Focused tests for registry closure, formal artifact feedback, retry behavior,
  topology freshness, install sync, and local git evidence.
