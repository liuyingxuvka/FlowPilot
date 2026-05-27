## 1. Model And Target Structure

- [x] 1.1 Run FlowGuard existing-model preflight and architecture-reduction review for the Router IO owner split.
- [x] 1.2 Derive the child-module topology and retained facade boundary from Code Structure and StructureMesh evidence.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Implementation

- [x] 2.1 Split path, timestamp, runtime-kit, bootstrap-state, project-relative, and runtime-entrypoint helpers into an IO paths child owner.
- [x] 2.2 Split runtime JSON write-lock constants, liveness classification, takeover/cleanup logging, and writer-settlement helpers into an IO locks child owner.
- [x] 2.3 Split atomic JSON writes, JSON read variants, daemon-critical read handling, and runtime-scan reads into an IO JSON child owner.
- [x] 2.4 Split JSON and role-output semantic hash helpers into an IO hashes child owner.
- [x] 2.5 Keep `flowpilot_router_io.py` as the compatibility facade and preserve legacy imports.
- [x] 2.6 Update install checks, StructureMesh catalogs, model-test alignment contracts, and focused boundary tests.

## 3. Validation

- [x] 3.1 Run compile/import smoke and focused IO compatibility assertions.
- [x] 3.2 Run focused runtime JSON lock, startup daemon, terminal, and boundary tests.
- [x] 3.3 Run FlowGuard router facade split, StructureMesh, and model-test alignment checks.
- [x] 3.4 Run router/Meta/Capability regressions through the background artifact contract and inspect final logs.

## 4. Sync And Git

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed skill location.
- [x] 4.2 Audit installed-skill freshness and run install checks.
- [x] 4.3 Record FlowGuard adoption and KB postflight notes.
- [x] 4.4 Recheck peer-agent worktree changes and create a local git commit containing only this change.
