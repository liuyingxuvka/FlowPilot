## 1. Model And Target Structure

- [x] 1.1 Run FlowGuard existing-model preflight and architecture-reduction review for the lifecycle request owner split.
- [x] 1.2 Derive the child-module topology and retained facade boundary from Code Structure and StructureMesh evidence.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Implementation

- [x] 2.1 Split terminal controller-work fencing into a lifecycle child owner.
- [x] 2.2 Split terminal authority reconciliation and blocker clearance into a lifecycle child owner.
- [x] 2.3 Split lifecycle request record writing and protocol dead-end persistence into a lifecycle child owner.
- [x] 2.4 Split exception blocker fallback into a lifecycle child owner.
- [x] 2.5 Keep `flowpilot_router_lifecycle_requests.py` as the compatibility facade and bind all child owners.
- [x] 2.6 Update install checks, facade export evidence, StructureMesh catalogs, and model-test alignment contracts.

## 3. Validation

- [x] 3.1 Run compile/import smoke and focused lifecycle compatibility assertions.
- [x] 3.2 Run focused terminal, closure, control-blocker, and full-diagnostic contract tests.
- [x] 3.3 Run FlowGuard router facade split, StructureMesh, and model-test alignment checks.
- [x] 3.4 Run router/Meta/Capability regressions through the background artifact contract and inspect final logs.

## 4. Sync And Git

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed skill location.
- [x] 4.2 Audit installed-skill freshness and run install/smoke checks.
- [x] 4.3 Record FlowGuard adoption and KB postflight notes.
- [x] 4.4 Recheck peer-agent worktree changes and create a local git commit containing only this change.
