# AGENTS.md

## Operating Rule

This repository implements the `flowpilot` Codex skill.

Before implementation work, read:

- `HANDOFF.md`
- `.flowpilot/state.json` if this clone is already inside an active
  FlowPilot-controlled route
- `.flowpilot/routes/route-001/flow.json` if present for the active route
- `docs/flowguard_preflight_findings.md`
- `simulations/capability_model.py`
- `simulations/meta_model.py`

## FlowGuard Requirement

Use real FlowGuard. Do not create a fake mini-framework.

## No Compatibility Or Fallback Surfaces By Default

FlowPilot is a current-contract runtime. New planning, repair, prompt,
runtime, and validation work must keep one explicit structured path per
behavior. Do not add compatibility shims, legacy aliases, prose/shape guessing,
missing-field defaults, old-router fallback, newest-run fallback, repo-root
fallback, dual-authority paths, or automatic translation from old field names
unless the user explicitly approves a named migration.

Allowed recovery must stay current-runtime and model-owned: it must name the
single owner, current run, current packet or node, blocking state, required
repair command, and validation evidence. Recovery may reissue, block, or ask
for a current structured result; it must not silently convert old input into a
valid current result or treat historical artifacts as completion evidence.

When fixing a failure, delete or reject the unsupported path rather than
teaching the runtime to accept both old and new forms. Add a negative test for
each removed compatibility surface.

## Minimal Current-Contract Repair Framework

When repairing FlowPilot runtime, route, prompt, card, gate, or recovery
failures, prefer the smallest current-contract change that fixes the observed
state-machine problem. Do not add a new ledger, table, packet kind, prompt
channel, role, or state family when the existing packet/result/gate surfaces
can express the repair.

Use this default ownership split:

- Runtime/router owns mechanical validity: schema, packet kind, route scope,
  current run, current packet/result/node ids, path/hash presence, supported
  command names, and rejection of legacy aliases, wrappers, fallback prose, or
  missing-field defaults.
- FlowGuard owns substantive process and state review: whether the real current
  artifact, evidence, route effect, repair effect, or recovery effect can
  execute without stale evidence, loops, future-state assumptions, or broken
  refinement.
- Reviewer owns substantive quality review: whether the real current artifact
  satisfies the task, evidence is credible, contradictions are handled, and the
  output is good enough for the next gate or user-facing claim.

For gated side effects, prefer one lightweight staged-effect concept over
per-scenario candidate ledgers. A staged effect records only the current result
or gate identity, effect kind, target node/route/blocker when needed, status,
and the command or runtime path that will commit it after review. It must not
copy sealed bodies or recreate a parallel candidate system. Use staged effects
only for effects that are currently blocked by a real timing mismatch, such as
"review must inspect the real submitted artifact before runtime binds it as an
accepted node plan" or "route mutation must be reviewed before active route
version changes."

Before adding new fields or state, require a clear answer to all of these:

- Which observed blocker, loop, stale-evidence hazard, or unsupported path does
  this prevent?
- Can the same repair be represented with existing packet, result, gate,
  blocker, or route-node records?
- Is this mechanical validation better owned by runtime/router instead of
  FlowGuard or Reviewer?
- Does the added state have one owner, one commit point, a negative test, and a
  cleanup/terminal disposition?

If any answer is unclear, first reduce the repair plan instead of expanding the
runtime shape. Avoid recreating old-router complexity through many specialized
candidate records, compatibility surfaces, or role-specific state machines.

For FlowPilot current-contract repairs, also follow
`docs/flowpilot_current_contract_repair_discipline.md`. That document is the
durable rule set for future agents: shrink wrong requirements back to their
owning stage, keep role boundaries clean, cover all package and blocker repair
families, carry repeated-repair lineage, and leave old names only in
forbidden/deleted lists, negative tests, or historical labels.

## FlowGuard Project Topology

This mature FlowGuard project maintains an automatically generated project
topology map:

- Machine artifact: `docs/flowguard_project_topology.json`
- Human artifact: `docs/flowguard_project_topology.md`
- Generator/checker: `python scripts/flowguard_project_topology.py build`
  and `python scripts/flowguard_project_topology.py check`

Before non-trivial planning, proposal, coding, prompt/card, model, test,
release, install, or validation work, read the topology Markdown after the
standard FlowGuard package/project audit. Use it as background architecture for
which model families, tests, code surfaces, evidence summaries, and known-bad
signals to inspect next.

The topology is orientation only. It is not a FlowGuard Report, not child model
evidence, not test evidence, and not a release or install pass. Completion
claims still need the owning executable checks, result artifacts, install
audits, and freshness evidence.

When FlowGuard models, runners, result paths, tests, code ownership surfaces,
prompt/card boundaries, AGENTS rules, or readiness checks change, rebuild and
check the topology before claiming done, or explicitly report why it is left
stale.

Long-running FlowGuard checks in this repository use a stable background log
contract. Default to `tmp/flowguard_background/` and use the command base name
for these artifacts:

- `<name>.out.txt` for stdout;
- `<name>.err.txt` for stderr and progress;
- `<name>.combined.txt` for human-readable merged output;
- `<name>.exit.txt` for the process exit code;
- `<name>.meta.json` for command, start/end time, status, and proof-reuse
  metadata.

For the heavyweight project checks, use these base names:

- `run_meta_checks` for `python simulations/run_meta_checks.py`;
- `run_capability_checks` for
  `python simulations/run_capability_checks.py`.

Before reporting a long check as complete, inspect the actual artifacts and
report the log root, stdout/stderr/combined paths, exit code, latest update
time, completion status, and whether a valid proof was reused. A path-only
report, an in-progress log, or a missing exit artifact is not completion
evidence. Progress lines are liveness evidence only; pass/fail still comes from
the executable check result and exit code.

Before changing behavior-bearing protocol, route, or skill logic, verify:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
```

If the change affects the project-control flow, update and rerun:

```powershell
python simulations/run_meta_checks.py
```

If the change affects skill/capability routing, update and rerun:

```powershell
python simulations/run_capability_checks.py
```

## Coordination

Keep edits scoped. This project is expected to be worked on by agents that may
resume from local files rather than chat history.

When this repository is being developed under an active FlowPilot route, update
that workspace's `.flowpilot/` state when changing the plan:

- route structure changes: create a new route version;
- execution progress: update `state.json`, heartbeat records, and node reports;
- capability decisions: update `capabilities.json` and capability evidence;
- major verified milestone: write a checkpoint.

## Documentation Language

Use English for repository files. The project is intended for public GitHub
distribution and cross-agent handoff.

## Hard Gates

Never silently change these without explicit user approval:

- frozen acceptance contract;
- release/publish/deploy actions;
- major technology stack changes;
- destructive or irreversible changes;
- handling secrets or private account data;
- lowering completion standards.

<!-- BEGIN FLOWGUARD PROJECT RULES -->

<!-- flowguard-rule:project.scope -->

## FlowGuard Project Rules

This project uses FlowGuard for non-trivial maintenance, feature work, bug
fixes, refactors, tests, release work, direct current replacement, and evidence-sensitive
process changes.

<!-- flowguard-rule:project.repository -->

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

<!-- flowguard-rule:skill_suite.agent_surface -->

FlowGuard agent skill suite:
- Primary agent surface: `.agents/skills/`
- Default entry skill: `.agents/skills/model-first-function-flow/SKILL.md`
- Complete AI-agent setup means the agent can read `AGENTS.md` and all
  FlowGuard sibling `SKILL.md` files under `.agents/skills/`.
- The Python `flowguard` module/CLI is executable check support, not the
  AI-agent skill installation surface.

<!-- flowguard-rule:project.record_locations -->

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

<!-- flowguard-rule:project.rendered_versions -->

Current adoption record:
- FlowGuard check-engine version: `0.55.0`
- FlowGuard schema version: `1.0`

<!-- flowguard-rule:project.preflight_version_gate -->

Before non-trivial work:
1. Verify the real FlowGuard check engine:
   `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
2. Check the installed check-engine version:
   `python -c "import importlib.metadata as m; print(m.version('flowguard'))"`
3. Audit the project record:
   `python -m flowguard project-audit --root .`
4. Compare the installed version with `.flowguard/project.toml`.
5. If the installed version is newer, run:
   `python -m flowguard project-adopt --root .`
   This directly replaces the managed project record with the one current
   FlowGuard shape. It does not read, convert, migrate, alias, or preserve an
   older FlowGuard skill/runtime shape. Then rerun only affected models/tests.
6. If the installed version is older than the project record, stop and connect
   a current FlowGuard check engine before claiming FlowGuard confidence.

<!-- flowguard-rule:runtime.current_authority_only -->

FlowGuard skill and runtime guidance has one current authority only.
Former FlowGuard skill, model, check, receipt, and project-control shapes are
blocked and may appear only as exact rejection fixtures. There is no normal
compatibility reader, migration command, upgrade route, converter, alias,
renewal route, or fallback success path. Ordinary software may read historical
documents, data, or interfaces only when an explicit requirement assigns a
bounded FlowGuard owner, accepted and rejected cases, and a claim boundary.

<!-- flowguard-rule:lifecycle.default_replacement -->

Default replacement means dispose the old path, old field, alias, wrapper, or
alternate success path. Delete, block, delegate, repair, replace, or
scope it out with a concrete reason; do not leave it as a second successful
route.

<!-- flowguard-rule:behavior.commitment_ledger -->

Broad behavior work should use or update BehaviorCommitmentLedger before
claiming full coverage: register external behavior promises, map source
surfaces to commitments, assign exactly one primary owner model per
commitment, classify plane and actor kind, record typed relations/evidence,
and hand `path_sensitive=true`
commitments to Primary Path Authority. Do not treat every helper function,
file, field, or model as a behavior commitment.

<!-- flowguard-rule:behavior.plane_partitioning -->

Keep product runtime behavior, AI-agent operations, and development lifecycle
behavior in one BehaviorCommitmentLedger structure but classify every
production commitment as exactly one of `product_runtime`, `agent_operation`,
or `development_process`. `commitment_kind` describes form, not plane.
Before non-trivial work, use the lightweight existing-model/commitment lookup
to select one same-plane primary context; keep other planes separated or
connected only by typed, reasoned relations. A related product commitment is
target context for an AI/process step, not an instruction that the step owns.
Model Miss backfeed searches the affected plane first and creates a gap row
only when no matching promise exists. This is recall guidance, not a universal
requirement to execute a model for every trivial action.

<!-- flowguard-rule:behavior.commitment_ledger_modes -->

Before changing or claiming behavior coverage, classify the behavior-ledger
mode: `bootstrap_ledger`, `add_behavior`, `change_behavior`,
`remove_or_replace_behavior`, `coverage_gap_backfill`, or `model_miss_check`.
Only bootstrap and gap backfill require broad historical source discovery.
Ordinary add/change/remove work updates affected commitments, owner models,
DCAR cases, and TestMesh evidence. Model-miss checks first map the failure to
an existing same-plane commitment and owner model; keep typed related-plane
context separate, and create/backfill a commitment only when the observed
external behavior was not registered in that plane.

<!-- flowguard-rule:lifecycle.field_mesh -->

Field-bearing work should use or update FieldLifecycleMesh: high-level behavior
models include behavior-bearing fields, while child/leaf field rows account all
discovered fields and record owner, readers, writers, projection, lifecycle,
and old-field disposition.

<!-- flowguard-rule:evidence.ui_and_payload -->

UI runnable claims and file/work-package claims need current UI click-through
or artifact-payload evidence gates before broad done/release confidence.

<!-- flowguard-rule:behavior.primary_path_authority -->

Path-sensitive behavior commitments need Primary Path Authority evidence before
broad confidence: one primary runtime authority per business intent, visible
primary failure, no automatic alternate success, ContractExhaustionMesh
coverage, TestMesh shards, and Risk Evidence Ledger gates.

<!-- flowguard-rule:behavior.exact_intent_reuse -->

Treat one exact external user purpose as one stable `business_intent_id`, one
active Behavior Commitment, and one singular `primary_path_id`. UI, API, CLI,
aliases, adapters, wrappers, helpers, and compatibility surfaces for that same
purpose delegate to the selected commitment and path; they do not become
independent successful implementations.

<!-- flowguard-rule:ui.product_language -->

Use the existing UI Flow Structure route to review one product-wide design
language across declared surfaces: typography hierarchy, components,
navigation, interaction, feedback, recovery, and transition semantics. Equal
semantic roles reuse the same rule or token; any exception is bounded,
presentation-only, and cannot change the business intent, commitment, path,
visibility class, or user-visible result.

<!-- flowguard-rule:ui.content_admission -->

Classify UI content exactly once as `user_visible`, `user_on_demand`, or
`internal`. Ordinary UI renders only admitted user content; on-demand content
needs an explicit reveal and return path, while internal identities, audit
fields, evidence metadata, diagnostics, and routing state stay internal by
default.

<!-- flowguard-rule:process.development_process_flow -->

Non-trivial rough-plan discussion, multi-skill/tool workflow setup, staged
execution, install/sync, release/archive/publish, post-change owner scans, and
final process claims enter `flowguard-development-process-flow` first as the
development-process simulator. Record `plan_detailing`, `agent_workflow`, and
`execution_freshness` modes; delegate to PlanDetailing or
AgentWorkflowRehearsal only when explicit or simulator-selected.
DevelopmentProcessFlow owns lifecycle order/freshness; AgentWorkflowRehearsal
owns AI-operation planning. Both may reference product commitments and their
evidence without copying product behavior into their own steps.

<!-- flowguard-rule:process.spec_work_package_reconciliation -->

When OpenSpec, Spec Kit, or another supported specification provider is in
scope, keep provider tasks native and reconcile them bidirectionally with
FlowGuard obligations/checks through one development-process Spec Work
Package. Begin and close one immutable input session, reuse only exact terminal
receipts within an explicit boundary, and block archive when mappings,
post-snapshot evidence, provider verification, or receipt freshness is
missing. Internal work-package fields never become product UI content.

<!-- flowguard-rule:process.post_change_scan -->

After non-trivial FlowGuard-managed work, let DevelopmentProcessFlow consume
post-change scan signals for changed artifacts, skipped routes, stale evidence,
open obligations, or split/reduction pressure. The scan output routes each gap
to the owning specialist, such as Model-Test Alignment, Architecture
Reduction, StructureMesh, ModelMesh, TestMesh, or AgentWorkflowRehearsal.

<!-- flowguard-rule:validation.native_owner_receipts -->

Keep every native test with exactly one existing owner. Before validation,
list the affected native checks, owner, exact functional input components, and
receipt order. SkillGuard/TestMesh may request a missing owner receipt and
aggregate current receipts, but a consumer must not copy, wrap, or carry the
owner command. Only a declared functional input change invalidates that owner;
reports, receipts, logs, timestamps, task checkmarks, and install bookkeeping
are outputs and must not trigger native retesting. Run one final full gate only
after source and tool identities freeze, under one explicit owner, never through
`--resume`, a scheduled task, a background retry, or an unattended helper. If
a launcher times out or is interrupted, confirm the whole descendant process
tree is absent before accepting evidence or starting another validation.

<!-- flowguard-rule:claim.no_fake_adoption -->

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.

<!-- END FLOWGUARD PROJECT RULES -->
