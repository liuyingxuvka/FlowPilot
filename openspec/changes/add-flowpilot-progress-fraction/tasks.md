## 1. Runtime Progress Contract

- [x] 1.1 Locate the runtime public status/action output assembly and current-run work-node state source.
- [x] 1.2 Add a runtime-owned `progress_fraction` calculation that emits `ended_nodes`, `expanded_nodes`, and `display`.
- [x] 1.3 Ensure control-plane mechanics do not contribute to the progress fraction.

## 2. Controller Guidance

- [x] 2.1 Update Controller-facing guidance so it can relay `progress_fraction.display` when useful.
- [x] 2.2 Explicitly forbid Controller-side progress calculation, percent conversion, sealed-body inspection, or completion decisions based on the fraction.

## 3. Verification And Sync

- [x] 3.1 Add focused tests for zero/active/ended/repair/control-plane progress cases.
- [x] 3.2 Run focused runtime and prompt validation, plus affected FlowGuard/OpenSpec checks.
- [x] 3.3 Sync the local installed FlowPilot skill and verify install parity.
- [x] 3.4 Stage and commit only this feature's scoped changes, preserving unrelated peer-agent changes.
