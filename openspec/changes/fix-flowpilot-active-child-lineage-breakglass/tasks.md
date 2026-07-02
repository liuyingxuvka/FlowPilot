## 1. OpenSpec And FlowGuard Framing

- [x] 1.1 Record the active-child-lineage and break-glass root-cause boundary in OpenSpec.
- [x] 1.2 Validate the change before implementation.
- [x] 1.3 Preserve no compatibility, no fallback, clean restart, and single-path constraints.

## 2. Runtime Mechanics

- [x] 2.1 Add strict active route-child lineage resolution.
- [x] 2.2 Use active child ids when copying child lists during route-node repair replacement.
- [x] 2.3 Use active child ids and active accepted child results when issuing parent backward replay.
- [x] 2.4 Reject missing, cyclic, unresolved, or still-superseded child lineage.
- [x] 2.5 Keep unresolved same-root blockers countable through break-glass until lineage is verified closed.

## 3. Existing Cards And Contracts

- [x] 3.1 Update PM repair guidance to prohibit ordinary repair after runtime threshold evidence.
- [x] 3.2 Update Controller and break-glass guidance so cleared-but-unclosed root causes still count.
- [x] 3.3 Update FlowGuard operator guidance to check route/replay execution effects.
- [x] 3.4 Update parent backward reviewer guidance to require active child lineage and reject superseded child ids.
- [x] 3.5 Update packet/stage contracts only where existing fields need active-lineage visibility.

## 4. Cartesian Coverage

- [x] 4.1 Add active child resolver tests for no replacement, one replacement, chains, missing targets, and cycles.
- [x] 4.2 Add repair replacement tests proving copied parent children resolve to active replacements.
- [x] 4.3 Add parent replay tests proving stale child ids are rejected or resolved to active ids.
- [x] 4.4 Add blocker loop tests for active, cleared-unclosed, verified-closed, retired, and same-root histories.
- [x] 4.5 Add break-glass tests for attempt counts 1, 4, 5, and 6.
- [x] 4.6 Add fake/runtime bad-case coverage for stale child lineage, wrong reviewer pass, and PM-text-only FlowGuard pass.
- [x] 4.7 Add same-class negative coverage for duplicate active child targets, missing active child results, reviewer-submitted superseded child ids, and reviewer-submitted superseded child result refs.

## 5. Validation And Sync

- [x] 5.1 Run focused unit tests for the changed runtime behavior.
- [x] 5.2 Run focused FlowGuard/model checks for blocker repair and project-control information flow.
- [x] 5.3 Run install checks and local install sync audit.
- [x] 5.4 Sync repository-owned FlowPilot files to the installed local skill.
- [x] 5.5 Re-run install check after sync.
- [x] 5.6 Rebuild/check FlowGuard project topology if model, test registry, or card boundaries changed.
- [x] 5.7 Commit or otherwise report the local git state without reverting peer-agent work.
