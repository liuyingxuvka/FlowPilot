## Why

`skills/flowpilot/assets/flowpilot_router.py` has grown into a high-risk
runtime monolith. It now owns startup, Controller ledgers, card ACK settlement,
packet orchestration, route/frontier state, gate decisions, daemon behavior,
terminal closure, CLI dispatch, and low-level JSON/path utilities in one file,
which makes future protocol fixes harder to isolate and verify.

The previous ACK/busy-state repair established a stable behavior baseline.
This change preserves that behavior while splitting the router into smaller
runtime-boundary modules with compatibility shims and FlowGuard-backed
verification.

## What Changes

- Preserve the current router script as the public CLI and import facade.
- Extract low-risk constants, path helpers, and JSON/runtime file helpers first.
- Extract Controller action ledger and passive-wait reconciliation helpers.
- Extract card ACK/return settlement while preserving ACK-only versus
  output-bearing work semantics.
- Extract packet/mail orchestration helpers only behind the existing router
  action flow.
- Extract startup/bootloader, daemon/standby, and terminal/gate helpers where
  the seam is behavior-preserving and test-covered.
- Split focused runtime tests by boundary while keeping end-to-end router tests.
- Synchronize the installed local FlowPilot skill after validation.

No breaking CLI, runtime schema, packet schema, or OpenSpec behavior changes are
intended.

## Capabilities

### New Capabilities

- `router-runtime-boundary-modularization`: behavior-preserving modularization
  requirements for the FlowPilot router runtime, compatibility facade, staged
  extraction, and verification evidence.

### Modified Capabilities

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- New helper modules under `skills/flowpilot/assets/`
- Focused tests under `tests/`
- Focused FlowGuard models and result files when affected by extraction
- `scripts/check_install.py` and install/audit checks, if import expectations
  need updating
- Local installed FlowPilot skill under the Codex skills directory after
  repository validation passes
