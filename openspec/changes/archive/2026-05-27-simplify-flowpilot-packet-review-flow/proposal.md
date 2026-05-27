## Why

FlowPilot's packet loop already moved toward Router direct dispatch and PM-owned result disposition, but older reviewer-dispatch wording and duplicated PM release states still make the live process look heavier than it is. The change clarifies and enforces one simpler packet review path without weakening PM ownership, Reviewer independence, Controller sealed-body isolation, or final gate evidence.

## What Changes

- Make PM-authored material, research, current-node, and PM role-work packets follow one visible path: PM issues the package, Router performs mechanical direct-dispatch validation, Controller relays only envelopes, the assigned role works, and results return to PM disposition before any Reviewer gate.
- Treat an absorbed PM package-result disposition that writes a formal gate package path, hash, scope, and content boundary as the PM release for Reviewer review.
- Keep Reviewer gates focused on formal PM gate packages and direct quality/source/fact checks, not on pre-dispatch approval or Router-computable envelope/hash checks.
- Retire reviewer-dispatch cards/events from the new packet flow by marking them legacy/compatibility-only until old fixtures and archived references can be removed safely.
- Rename or alias misleading "reviewer relay" result checks to recipient-neutral wording while preserving compatibility for existing callers.
- Update FlowGuard models, focused tests, install checks, and local install sync so the simplification is executable, not prose-only.

## Capabilities

### New Capabilities

- `flowpilot-packet-review-flow`: PM-issued packet execution, PM package-result disposition, formal gate package release, Reviewer package review, and legacy reviewer-dispatch compatibility boundaries.

### Modified Capabilities

- `dispatch-recipient-gate`: Router direct dispatch is the normal pre-worker gate for PM-authored work packets; Reviewer pre-dispatch approval is legacy-only.
- `router-internal-mechanical-actions`: Router-owned mechanical proof replaces Reviewer rechecking only for envelope/hash/ledger facts, while semantic review remains Reviewer-owned.
- `settled-router-next-action`: result-return notices use the result recipient, so PM-bound results direct Controller to PM disposition instead of Reviewer review.
- `packet-open-authority-exits`: addressed roles, PM, and Reviewer open only the packets/results authorized for their role and stage; legacy relay names do not create extra authority.

## Impact

- Affected runtime code: packet relay checks, packet runtime facade exports, PM package-result disposition writers, current-node/material/research/PM-role packet action handlers, reviewer cards, and event compatibility labels.
- Affected models and verification: FlowGuard PM package/result flow, router loop, control-plane friction, Meta/Capability PM-review-release invariants, focused packet/runtime tests, OpenSpec validation, install checks, local install audit, and background model regressions.
- Affected docs/cards: protocol wording, direct-dispatch and PM package absorption plans, runtime kit phase cards, Reviewer formal package cards, and stale legacy dispatch references.
- Out of scope: removing PM ownership, removing Reviewer quality gates, allowing Controller to read sealed bodies, publishing a release, pushing to a remote, or changing unrelated UI/README/autonomous redesign work currently modified by other agents.
