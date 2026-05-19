## 1. Scope And Model Boundary

- [x] 1.1 Record OpenSpec scope for lock-boundary ownership and local-only sync.
- [x] 1.2 Verify real FlowGuard is importable.
- [x] 1.3 Update StructureMesh ownership evidence for shared process liveness.

## 2. Implementation

- [x] 2.1 Add a shared process-liveness owner helper.
- [x] 2.2 Route runtime JSON write-lock and Router daemon lock liveness through the helper without changing lock semantics.
- [x] 2.3 Add a maintainer-facing lock/lease boundary map.
- [x] 2.4 Keep active-holder lease code in packet runtime and do not merge it into file-lock ownership.

## 3. Validation

- [x] 3.1 Run focused compile checks for touched Python files.
- [x] 3.2 Run focused owner-boundary/router daemon tests.
- [x] 3.3 Run FlowGuard StructureMesh and model-test alignment checks.
- [x] 3.4 Run background Meta and Capability regressions and inspect final artifacts.

## 4. Local Sync And Git

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed skill.
- [x] 4.2 Run install freshness and public release checks. Full `check_public_release.py` validation timed out in `smoke_autopilot.py --fast`; decomposed install, release-tooling, and public-release boundary checks passed, with the smoke timeout recorded as a validation gap.
- [x] 4.3 Commit only this change's files locally; do not push, tag, deploy, or publish a GitHub Release.
