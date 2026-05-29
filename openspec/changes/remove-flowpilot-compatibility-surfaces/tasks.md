## 1. Modeling And Inventory

- [x] 1.1 Verify FlowGuard importability, worktree cleanliness, and OpenSpec status before implementation.
- [x] 1.2 Add or update a FlowGuard new-only compatibility-removal model that treats old runtime inputs as rejected, not migrated.
- [x] 1.3 Generate a focused compatibility inventory covering commands, startup payloads, event aliases, schema aliases, prompts, migrations, install checks, tests, and facade exports.

## 2. Startup And Invocation Cleanup

- [x] 2.1 Remove fresh-invocation compatibility aliases from FlowPilot user-facing instructions and CLI parsing.
- [x] 2.2 Remove legacy startup chat-payload reconciliation from startup/runtime helpers and tests.
- [x] 2.3 Ensure current `start` startup and explicit resume/inspect/stop paths remain intact.

## 3. Event, Schema, And Transaction Cleanup

- [x] 3.1 Remove legacy Router, Product Officer, Process Officer, and Reviewer event aliases from external event registries.
- [x] 3.2 Remove output-type aliases, deprecated transaction kinds, and compatibility-only policies from runtime contracts.
- [x] 3.3 Update role-output and control-plane tests to assert old inputs are rejected instead of canonicalized.

## 4. Migration, Recovery, Prompt, And Documentation Cleanup

- [x] 4.1 Remove legacy material packet, terminal closure, old layout, and startup daemon migration/recovery helpers from active runtime paths.
- [x] 4.2 Remove active prompt/card language that offers old compatibility paths or deprecated repair flows.
- [x] 4.3 Remove legacy equivalence and legacy-full checks from install requirements and current test tier release gates.
- [x] 4.4 Update HANDOFF and maintenance docs so they describe the new-only FlowPilot contract and archived historical evidence boundary.

## 5. StructureMesh Facade Contraction

- [x] 5.1 Scan public facade exports and import sites to separate current owner APIs from compatibility-only re-exports.
- [x] 5.2 Remove compatibility-only facade exports that no production or test owner still needs.
- [x] 5.3 Preserve or rename safety quarantine state that protects against prior/superseded authority without accepting legacy inputs.

## 6. Validation, Install Sync, And Git Finalization

- [x] 6.1 Run focused unit/integration tests for startup, external events, role-output contracts, repair transactions, prompts, and install checks.
- [x] 6.2 Start heavyweight FlowGuard meta and capability regressions in background logs and inspect completion artifacts before claiming their result.
- [x] 6.3 Run OpenSpec strict validation for the change and all specs.
- [x] 6.4 Sync the repository-owned installed FlowPilot skill, then run install check and installed freshness audit serially.
- [x] 6.5 Commit the intended local git result without pushing, tagging, releasing, or deploying.
