# FlowGuard Preflight Record

## Route Decision

- ExistingModelPreflight grounds this change in the existing FlowPilot PM,
  Reviewer, FlowGuard operator, Worker, route, node, parent replay, final replay,
  model-miss, planning-quality, Cartesian, ContractExhaustionMesh, TestMesh, and
  Model-Test Alignment surfaces.
- DevelopmentProcessFlow owns the staged process claim for this upgrade:
  prompt/card edits, model edits, tests, validation, topology, install sync, and
  closure freshness.
- ContractExhaustionMesh owns same-class integration cases across stage, role,
  artifact family, failure class, severity, authority, evidence timing, and
  expected outcome.
- TestMesh owns layered test evidence and regression freshness for focused tests,
  model runners, and broad meta/capability checks.
- Model-Test Alignment owns direct comparison between new FlowGuard obligations,
  generated integration case ids, and executable tests.

## Existing Surfaces Reused

- PM remains the system integration owner. No new PM-like role is introduced.
- Reviewer remains a quality challenger and formal gate reviewer. Reviewer
  reports hard failures only when current gate minimums fail; higher-standard
  improvements remain PM decision support.
- FlowGuard operator remains the model/process/test-risk reviewer. FlowGuard
  reports support PM and Reviewer decisions but do not approve gates, mutate
  routes, close nodes, or replace PM absorption.
- Worker remains packet-scoped. Worker may report integration concerns as PM
  suggestions or blockers allowed by the current packet, but Worker does not
  become the system integrator.
- `node_context_package` remains the current five-field package:
  `purpose`, `acceptance_criteria`, `relevant_references`, `known_risks`, and
  `acceptance_item_projection`.

## Known Preflight Gaps

- `python -m flowguard project-audit --root .` currently reports
  `pass_with_gaps` because `.flowguard/project.toml` is missing. The sync phase
  must adopt or repair the project record before final FlowGuard confidence is
  claimed.
- Topology is orientation only. It cannot close this change without the owning
  focused checks, model runners, install checks, and background regression
  artifacts.

## Current-Contract Boundary

This change must not add a new runtime hard blocker, self-stop, role, ledger,
packet family, state family, compatibility shim, or fallback path. Integration
upgrades are prompt/workflow/model/test upgrades inside the current contract.
Runtime remains responsible only for mechanical validity and existing current
gate mechanics.
