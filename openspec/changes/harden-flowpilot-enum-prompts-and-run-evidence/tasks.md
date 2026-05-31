## 1. Contract And Model

- [x] 1.1 Create OpenSpec requirements for fixed-value prompt menus and run-local FlowGuard evidence paths.
- [x] 1.2 Extend the new-entrypoint FlowGuard model with hazards for missing host-kind menus, invented host-kind values, and tracked-baseline formal evidence.

## 2. Implementation

- [x] 2.1 Update FlowPilot skill guidance and CLI help so `--host-kind` allowed values are explicit and `live` is the real Codex/multi-agent choice.
- [x] 2.2 Update formal FlowGuard packet bodies with run-local evidence output policy and concrete runner command hints.
- [x] 2.3 Add `--json-out` / proof override support to Meta and Capability check runners without changing default baseline behavior.

## 3. Validation

- [x] 3.1 Add focused tests for host-kind value-menu guidance and invalid host-kind rejection.
- [x] 3.2 Add focused tests that custom Meta/Capability runner output paths do not target canonical tracked result files.
- [x] 3.3 Add focused tests that FlowGuard officer packets include run-local evidence policy.
- [x] 3.4 Run the new-entrypoint FlowGuard checks, focused unit tests, model-test alignment where affected, install checks, and run-local Meta/Capability regressions.

## 4. Completion

- [x] 4.1 Update version, changelog, install inventory, and FlowGuard adoption notes.
- [x] 4.2 Sync the installed local FlowPilot skill and verify local install audit.
- [x] 4.3 Commit the local git result without push, tag, release, or deploy.
