## Context

FlowPilot has accumulated a mature FlowGuard ecosystem: many specialized
models, model hierarchy and mesh gates, model-test alignment, coverage sweep
results, runtime-path evidence, prompt/card validation, install readiness, and
known-bad hazard checks. These artifacts are strong individually, but an agent
entering the repository still has to reconstruct the project architecture from
many files before it can reason with the existing model structure.

The user goal is not another task-specific search helper. The goal is a
project-level topology that is automatically generated and maintained from the
existing FlowGuard/model/test/code evidence, then read by agents before
non-trivial work so FlowGuard becomes background architecture in mature
FlowGuard projects.

## Goals / Non-Goals

**Goals:**
- Generate `docs/flowguard_project_topology.json` and
  `docs/flowguard_project_topology.md` from repository evidence.
- Cover model areas, model runners, result artifacts, coverage tiers,
  model-test alignment families, code owner surfaces, test tiers, evidence
  freshness, known-bad labels, and validation/maintenance commands.
- Add a `check` mode that fails when generated topology is missing, malformed,
  stale relative to topology sources, or missing required model/test/code
  layers.
- Make mature FlowGuard projects read the topology before non-trivial work and
  refresh it after topology-affecting changes.
- Keep topology as orientation evidence only; it must never replace executable
  FlowGuard checks, tests, conformance replay, or install validation.

**Non-Goals:**
- Do not replace ModelMesh, Model-Test Alignment, TestMesh, StructureMesh,
  Risk Evidence Ledger, or runtime replay.
- Do not add a keyword-only task classifier that decides current task ownership.
  Agents use the topology as background and then apply existing-model preflight
  and route-specific FlowGuard skills.
- Do not introduce external dependencies.
- Do not require full Meta or Capability regressions in foreground to generate
  the topology.

## Decisions

### Generate topology from existing evidence

Add `scripts/flowguard_project_topology.py` with `build` and `check`
subcommands. `build` reads current repository evidence and writes both JSON and
Markdown. `check` rebuilds in memory, compares required fields and source
freshness, and reports actionable gaps.

Alternative considered: hand-maintained topology docs. Rejected because the map
would drift from model/test/code reality and would not satisfy the automatic
maintenance goal.

### Use lightweight registry heuristics plus existing diagnostics

The script will derive most rows from existing sources:
- `scripts/run_flowguard_coverage_sweep.py` tier sets and sweep result shape;
- `simulations/*_model.py`, `simulations/run_*_checks.py`, and
  `simulations/*_results.json`;
- model-test alignment result/family data;
- full diagnostic surfaces for code and tests when available;
- test-tier command registry under `scripts/test_tier/`;
- known-bad labels from result JSON sections.

It may use a small local area classifier for readable group names such as
startup, packet, route, controller, reviewer, closure, model mesh, hierarchy,
and prompt/card boundaries. This classifier only labels topology rows; it does
not decide current task routing.

Alternative considered: AI-generated summaries. Rejected for the canonical JSON
because generated prose is hard to check and easy to overclaim. Markdown may be
rendered from the JSON.

### Topology is a first-read artifact, not validation evidence

Prompts and AGENTS rules will instruct agents to read the topology before
non-trivial work in mature FlowGuard projects. The topology can guide which
model, tests, and code surfaces to inspect, but completion claims still require
the owning FlowGuard route, tests, result artifacts, install checks, and
freshness evidence.

Alternative considered: make topology a new FlowGuard satellite skill. Deferred.
The first implementation should prove the repository-local map and maintenance
rule before extracting a generic skill wrapper.

### Add a focused FlowGuard model for topology maintenance

Add a small model/check under `simulations/` that rejects common false
confidence paths:
- topology missing one of model/test/code/evidence layers;
- topology stale after source changes;
- known-bad labels absent from a mature project;
- topology accepted as validation evidence;
- topology skipped in a mature project before non-trivial work;
- topology used by Controller or Reviewer to exceed role authority.

This protects against the topology becoming a new checkbox.

## Risks / Trade-offs

- [Risk] Topology becomes too large for quick orientation. -> Mitigation:
  JSON carries full rows while Markdown groups by area and shows compact
  summary tables plus paths.
- [Risk] Source freshness checks are too strict and force noisy rebuilds. ->
  Mitigation: check only topology source files and result artifacts that the
  generator actually consumes.
- [Risk] Task routing is delegated to brittle keyword matching. -> Mitigation:
  do not implement authoritative task-lens routing; keep only general search or
  area labels as optional orientation.
- [Risk] Agents overclaim topology as proof. -> Mitigation: prompt rules,
  tests, and focused FlowGuard known-bad cases explicitly forbid this.
- [Risk] Install audit races install sync. -> Mitigation: run sync before
  install audit/check, never in parallel.

## Migration Plan

1. Add OpenSpec specs and tasks for the topology capability and prompt/readiness
   integration.
2. Implement the generator, generated artifacts, and focused tests.
3. Add topology maintenance checks to local validation surfaces without
   requiring heavyweight parent regressions in foreground.
4. Update AGENTS, FlowGuard skill entry instructions, and FlowPilot runtime
   cards to consume and maintain the topology.
5. Run focused checks, then background heavyweight regressions where required.
6. Sync the installed FlowPilot skill, audit install freshness, review git
   state, and commit the completed change.

## Open Questions

- None blocking. A future generic Codex skill may wrap the repository-local
  topology generator after this implementation proves the workflow.
