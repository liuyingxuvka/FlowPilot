## Why

FlowPilot now has working closure, control-plane, and maintenance registries, but some callers still carry local status checks or hand-maintained derived maps. System-card prompts also repeat the same ACK, Router-authority, and runtime-output boundaries across many cards, which makes future prompt fixes require broad manual alignment.

This change folds those remaining duplicate views into shared runtime helpers and prompt-policy assets while preserving the existing ledgers, role authority boundaries, public Router facade, and installed-skill compatibility.

## What Changes

- Route remaining high-risk wait, return, scheduler, and PM-role blocker scans through the shared closure classification boundary instead of local closed/open status lists.
- Move control transaction and route action policy derived maps out of `flowpilot_router.py` into their registry owner modules, keeping compatibility exports for existing imports.
- Move role-output/process binding facts that are still hard-coded in Python toward registry-backed derived views where the existing contract index can own them.
- Add prompt-boundary policy assets for repeated card header rules such as ACK-not-completion, Router-authorized next-step source, runtime-output return path, and live runtime context.
- Add tests and FlowGuard evidence that prove derived views match registries, unknown closure remains blocking, ACK closure does not complete work, and prompt cards stay aligned with the shared policy.
- Synchronize the installed local FlowPilot skill after validation and verify installed content freshness.

## Capabilities

### New Capabilities
- `flowpilot-derived-view-registries`: Runtime code derives compatibility views from registry authorities instead of maintaining separate hand-written maps or local lifecycle predicates.
- `flowpilot-prompt-boundary-policy`: System-card and role-card prompts use shared boundary policy assets for ACK semantics, Router authority, runtime output submission, and live context freshness.

### Modified Capabilities

## Impact

- Affected runtime code: `skills/flowpilot/assets/flowpilot_closure_kernel.py`, card-return/current-work/scheduler/PM-role blocker modules, control transaction registry modules, route action policy registry modules, role-output runtime schema helpers, and the `flowpilot_router.py` compatibility facade.
- Affected prompt assets: `skills/flowpilot/assets/runtime_kit/prompts/`, `skills/flowpilot/assets/runtime_kit/cards/`, and `skills/flowpilot/assets/runtime_kit/manifest.json` or validation scripts that govern prompt/card consistency.
- Affected evidence: focused Python tests, FlowGuard closure/registry/prompt-alignment models, install freshness audit, local installed skill synchronization, and final git commit.
- Out of scope: physical ledger merge, public Router facade removal, remote GitHub push/tag/release, role-authority expansion, sealed-body reads, or treating ACK receipt as semantic work completion.
