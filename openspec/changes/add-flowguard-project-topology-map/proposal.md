## Why

FlowPilot already has deep FlowGuard model, test, hierarchy, maturation, and
coverage evidence, but those artifacts are scattered across runner results,
docs, OpenSpec records, and source modules. Agents entering this mature
FlowGuard project need an automatically maintained project topology map so the
existing model/test/code structure becomes background architecture before
non-trivial work begins.

## What Changes

- Add a repository topology generator that builds machine-readable and
  reviewable FlowGuard project topology artifacts from existing model runners,
  result files, tests, code ownership, evidence tiers, and known-bad signals.
- Add a topology check mode that detects stale or malformed topology artifacts
  after model, runner, test, prompt, or code-structure changes.
- Add tests and a focused FlowGuard model for topology maintenance risks,
  including missing model/test/code layers, stale topology, evidence overclaims,
  and topology being misused as validation evidence.
- Update agent and FlowPilot entry instructions so mature FlowGuard projects
  read the topology map before non-trivial work and refresh it when topology
  sources change.
- Integrate the topology artifacts into local validation and install readiness
  without replacing existing ModelMesh, Model-Test Alignment, StructureMesh,
  TestMesh, or runtime replay evidence.

## Capabilities

### New Capabilities
- `flowguard-project-topology`: Automatically maintained project-level
  topology for mature FlowGuard projects, covering model, test, code, evidence,
  and known-bad architecture relationships.

### Modified Capabilities
- `flowpilot-prompt-boundary-policy`: FlowPilot and FlowGuard-facing prompts
  must require topology reading and maintenance when a mature FlowGuard project
  provides topology artifacts.
- `flowguard-model-hierarchy`: Hierarchy/readiness validation must expose the
  topology artifacts and prevent topology freshness from being silently ignored
  in install/smoke readiness.

## Impact

- New script and tests under `scripts/`, `tests/`, and `simulations/`.
- New generated topology artifacts under `docs/`.
- Updates to `AGENTS.md`, FlowGuard skill entry instructions, FlowPilot runtime
  cards, local install checks, smoke validation, and adoption records.
- No breaking command-line changes; topology is an additional orientation and
  maintenance gate, not a replacement for existing FlowGuard evidence.
