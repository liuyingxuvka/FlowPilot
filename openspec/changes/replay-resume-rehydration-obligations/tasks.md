## 1. Contract And Model

- [x] 1.1 Create the OpenSpec proposal, design, specs, and task list for resume rehydration obligation replay.
- [x] 1.2 Extend the FlowGuard resume model so heartbeat/manual rehydration must run obligation replay before default PM resume when replay is mechanically clear.
- [x] 1.3 Confirm role-recovery model coverage remains compatible with the shared replay mechanism.
- [x] 1.4 Run the focused FlowGuard resume and role-recovery checks.

## 2. Runtime

- [x] 2.1 Refactor or wrap role-recovery replay so `rehydrate_role_agents` can invoke it after successful heartbeat/manual resume rehydration.
- [x] 2.2 Preserve daemon attach, visible plan restore, six-role liveness, and existing mid-run liveness recovery behavior.
- [x] 2.3 Set PM resume decision as satisfied only when replay completes without escalation; otherwise keep PM escalation.
- [x] 2.4 Ensure replacement rows and original wait superseding preserve the durable-before-supersede ordering.

## 3. Tests And Validation

- [x] 3.1 Add runtime tests proving resume rehydration settles existing evidence without PM.
- [x] 3.2 Add runtime tests proving resume rehydration reissues missing work before PM.
- [x] 3.3 Add runtime tests proving ambiguous resume still reaches PM.
- [x] 3.4 Run focused pytest suites for resume, role recovery, and no-output recovery.
- [x] 3.5 Run OpenSpec validation for the new change and relevant existing changes.

## 4. Sync And Local Git

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed skill.
- [x] 4.2 Run local install/source-fresh checks.
- [x] 4.3 Inspect the final worktree for compatible parallel-agent changes and include them in the local commit when safe.
- [x] 4.4 Commit the synchronized local git version without pushing or releasing.
