## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Record the proposal, design, and spec deltas for topology generation, prompt integration, and readiness validation.
- [x] 1.2 Verify real FlowGuard package/adoption status and identify existing model, hierarchy, alignment, coverage, and prompt surfaces used by the topology.

## 2. Topology Generator And Artifacts

- [x] 2.1 Add `scripts/flowguard_project_topology.py` with `build` and `check` commands.
- [x] 2.2 Generate `docs/flowguard_project_topology.json` and `docs/flowguard_project_topology.md` from model, test, code, evidence, and known-bad sources.
- [x] 2.3 Add unit tests for topology build/check behavior, stale detection, required layers, and machine-readable findings.

## 3. FlowGuard Model Coverage

- [x] 3.1 Add a focused FlowGuard topology-orientation model and runner.
- [x] 3.2 Add known-bad coverage for skipped topology intake, stale topology, missing model/test/code layers, missing known-bad signals, topology-as-validation overclaim, and role-authority misuse.
- [x] 3.3 Wire topology checks into coverage/smoke/install readiness surfaces without replacing existing evidence gates.

## 4. Agent And Runtime Entry Rules

- [x] 4.1 Update `AGENTS.md` and FlowGuard skill entry instructions so mature FlowGuard projects read and maintain topology before non-trivial work.
- [x] 4.2 Update FlowPilot PM, Officer, and Reviewer runtime cards so topology is read as background architecture and cannot replace file-backed reports or gate evidence.
- [x] 4.3 Add prompt/card coverage checks for topology-reading and topology-maintenance language.

## 5. Validation And Synchronization

- [x] 5.1 Run focused topology generator tests and topology FlowGuard checks.
- [x] 5.2 Run model-test alignment, coverage sweep, smoke/install readiness, and any affected prompt/card tests.
- [x] 5.3 Start heavyweight Meta and Capability regressions in background artifacts and inspect completion evidence before claiming broad confidence.
- [x] 5.4 Synchronize the repository-owned FlowPilot skill to the local installed skill and run install freshness audits serially.
- [x] 5.5 Update FlowGuard adoption records, OpenSpec task status, KB postflight, git status review, and local git commit.
