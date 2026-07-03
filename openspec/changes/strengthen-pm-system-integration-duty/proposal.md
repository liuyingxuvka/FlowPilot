## Why

FlowPilot already has PM ownership, FlowGuard process review, Reviewer replay, and terminal closure, but the integration responsibility is distributed too weakly across those stages. This allows locally complete work packages to pass while the final software, writing, report, or workflow feels scattered, repetitive, under-connected, or structurally unfinished.

## What Changes

- Add a PM-owned system integration duty that starts at product architecture and continues through route skeletons, node plans, PM result absorption, parent backward replay, final backward replay, and model-miss triage.
- Strengthen existing FlowGuard and Reviewer prompt cards so they challenge "locally complete but globally incoherent" work without becoming a second PM or a new runtime authority.
- Keep integration findings optimization-level by default: Reviewer and FlowGuard recommendations become PM decision support unless they expose an existing hard failure class.
- Preserve the current low-floor/high-ceiling quality posture: minimum gate failures still block, while 9/10-style quality, concision, and elegance improvements stay advisory unless they prove the current artifact cannot satisfy the root intent.
- Add full-domain Cartesian coverage for integration failure classes across stage, role, artifact family, severity, authority, evidence timing, and outcome, including both under-blocking and over-blocking cases.
- Update reusable FlowPilot templates and prompt/card instruction coverage so future runs carry the integration thread without adding new runtime self-stop gates, compatibility shims, or alternate contract paths.

## Capabilities

### New Capabilities

- `flowpilot-system-integration-duty`: PM-owned integration thread across product architecture, route composition, node integration touchpoints, result absorption, parent/final replay, and model-miss triage.
- `flowpilot-integration-cartesian-coverage`: finite Cartesian coverage for scattered local-pass/global-incoherence defects and for overblocking of advisory integration suggestions.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: prompt/card text must express the integration duty inside existing role boundaries without granting new runtime authority or adding compatibility surfaces.
- `formal-gate-review-standards`: Reviewer and FlowGuard integration findings must be classified as PM decision support unless they prove an existing hard gate failure.
- `flowpilot-closure-kernel`: parent and final backward replay must judge whether accepted child/node results compose into the parent or root goal, not just whether each child has local evidence.
- `flowguard-modeling-coverage`: FlowGuard planning-quality models must include scattered local-pass/global-incoherence as a modelable process miss.
- `hard-gate-coverage-matrix`: hard-gate coverage must include both missed hard integration failures and forbidden promotion of advisory integration improvements into hard blockers.
- `tiered-flowpilot-test-validation`: validation tiers must include focused prompt/template/model tests, Cartesian coverage, fake-AI replay, install sync, and long background model regressions for this change.

## Impact

- Runtime kit role and phase cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- Reusable FlowPilot templates under `templates/flowpilot/`.
- FlowGuard planning and capability/meta simulation models under `simulations/`.
- Focused tests under `tests/`, especially planning quality, card instruction coverage, current-contract Cartesian matrix, contract exhaustion mesh, fake-AI runtime replay, and acceptance TestMesh coverage.
- OpenSpec artifacts for this change, FlowGuard adoption records, topology artifacts, local installed FlowPilot skill sync, and local git version history.
