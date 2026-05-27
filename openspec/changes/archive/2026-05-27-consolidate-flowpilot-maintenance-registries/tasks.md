## 1. OpenSpec And FlowGuard Boundaries

- [x] 1.1 Record the OpenSpec proposal, design, specs, and implementation tasks.
- [x] 1.2 Verify real FlowGuard import and review current router/model structure recommendations.
- [x] 1.3 Confirm pre-existing dirty worktree files and avoid unrelated scopes.

## 2. Maintenance Surface Registry

- [x] 2.1 Add a canonical maintenance surface registry for install, diagnostic, facade, model, script, and runtime-kit surfaces.
- [x] 2.2 Add derived inventory helpers for install-required and model-test-code diagnostic surfaces.
- [x] 2.3 Add parity tests proving derived inventories preserve current required surfaces and deferred findings.

## 3. Gate Outcome Registry

- [x] 3.1 Add a canonical gate outcome registry.
- [x] 3.2 Generate existing gate outcome compatibility exports from the registry.
- [x] 3.3 Add parity tests for reset flags, block specs, pass-clear mappings, and pass-clears events.

## 4. External Event Registry

- [x] 4.1 Add a canonical external event registry with phase/family, legacy, and canonical-alias metadata.
- [x] 4.2 Generate existing external event shard maps and merged `EXTERNAL_EVENTS` from the registry.
- [x] 4.3 Add parity tests for event names, flags, legacy markers, and shard membership.

## 5. Contract And Process Binding Consolidation

- [x] 5.1 Add contract-index lookup helpers for task-family and output-contract identity.
- [x] 5.2 Derive low-risk process binding identity fields from `contract_index.json` while keeping Python-only policy explicit.
- [x] 5.3 Add focused tests for contract binding parity and role information-isolation fields.

## 6. Router Facade And Manifest-Driven Tests

- [x] 6.1 Move remaining low-risk router policy constants to catalog modules while keeping old facade exports.
- [x] 6.2 Convert class-wide card/path coverage tests to read runtime kit manifests where appropriate.
- [x] 6.3 Keep specific identity tests hand-written where the exact file is the contract.

## 7. Validation And Background Regressions

- [x] 7.1 Run compile/import and focused unit checks for touched modules.
- [x] 7.2 Run model-test alignment and StructureMesh checks.
- [x] 7.3 Run router tier in background if runtime router behavior is touched.
- [x] 7.4 Run meta and capability FlowGuard regressions in the repository background log contract before release-readiness claims.

## 8. Local Sync And Git Completion

- [x] 8.1 Synchronize the local installed FlowPilot skill from repo-owned source.
- [x] 8.2 Run install check and freshness audit; clear cache noise if needed.
- [x] 8.3 Stage and commit only this OpenSpec change's files and intentional source edits.
- [x] 8.4 Do not push, tag, or publish unless separately requested.
