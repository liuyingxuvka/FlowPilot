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

Test execution uses the current v4 owner-impact path:

- the repository snapshot fingerprint is provenance only and never a blanket
  run-all trigger;
- after one explicit seed baseline, every background run names the exact prior
  v4 manifest and its SHA-256;
- each owner is independently `reuse`, `execute`, or `blocked` from its exact
  command, inputs, dependencies, environment, obligations, and MTA evidence;
- `reuse` requires the same owner's terminal passing proof and a current
  `TestResultReuseTicket`;
- an unmapped change, stale identity, invalid prior manifest, or interrupted
  process tree blocks and never falls through to full execution;
- generated results, receipts, logs, task checkmarks, line-ending-only
  transport changes, and unrelated FlowGuard package upgrades do not invalidate
  owners unless they are explicit applicability inputs;
- shared execution-wrapper imports belong to the exact test-tier
  infrastructure owner, not to every nested Meta, Capability, model, or test
  payload; a former over-broad payload identity may reuse proof only through a
  strict proper-subset ownership transfer with identical retained inputs,
  command, environment, obligations, and evidence subjects;
- run focused affected checks while source is changing, and reserve one full
  validation for the frozen integration or release snapshot.

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
fixes, refactors, tests, release work, project upgrades, and evidence-sensitive
process changes.

<!-- flowguard-rule:project.repository -->

FlowGuard repository:
https://github.com/liuyingxuvka/FlowGuard

<!-- flowguard-rule:skill_suite.agent_surface -->

FlowGuard agent skill suite:
- Primary agent surface: the current clean consumer projection under
  `$CODEX_HOME/skills/`
- Default entry skill: `$CODEX_HOME/skills/flowguard/SKILL.md`
- Complete AI-agent setup means the agent can read `AGENTS.md` and all
  FlowGuard sibling `SKILL.md` files under `$CODEX_HOME/skills/`.
- An ordinary target project does not copy the FlowGuard suite into its local
  `.agents/skills/` tree and does not own the canonical suite map.
- Project audit and upgrade verify the package-owned clean-consumer authority
  directly against that global projection and its ownership manifest.
- The Python `flowguard` module/CLI is executable check support, not the
  AI-agent skill installation surface.

<!-- flowguard-rule:project.record_locations -->

Project FlowGuard record:
- Manifest: `.flowguard/project.toml`
- Machine log: `.flowguard/adoption_log.jsonl`
- Human log: `docs/flowguard_adoption_log.md`

<!-- flowguard-rule:project.rendered_versions -->

Current adoption record:
- FlowGuard check-engine version: `0.61.0`
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
   `python -m flowguard project-upgrade --root .`
   This updates the project record and scans existing FlowGuard artifacts,
   model evidence, tests, docs, and guidance for deterministic upgrades into
   the current FlowGuard shape. Use `--records-only` only when intentionally
   scoping out artifact/model/test upgrade scanning.
   Then rerun affected models/tests before broad confidence and record the result.
6. If the installed version is older than the project record, stop and connect
   a current FlowGuard check engine before claiming FlowGuard confidence.

<!-- flowguard-rule:runtime.latest_schema_first -->

FlowGuard runtime guidance is latest-schema-first: old artifacts may be
detected and upgraded at project/tool boundaries, but normal route logic should
not keep long-lived old branches for obsolete fields, aliases, or wrappers.

<!-- flowguard-rule:model_system.authority -->

For an existing modeled project, one content-addressed
`observed_implementation` ModelSystemSnapshot selected by the sole
`[model_authority]` head in `.flowguard/project.toml` is current authority.
`normative_target` and `counterfactual_experiment` snapshots remain isolated
candidates. File discovery, names such as `current`, prompt claims, and green
candidate checks never make a model current. Missing/invalid authority or
unresolved required coverage blocks broad current-model confidence.

<!-- flowguard-rule:model_system.revision_transaction -->

A target or experiment may replace the observed model system only through one
accepted ModelRevisionSet bound to the exact base head, candidate snapshot,
changed models/relations/fields/effects/contracts/tests, affected closure,
prediction/replay evidence, and current owner receipts. Persist immutable
records first and update the sole pointer last under the shared project-manifest
compare-and-swap lock. Operational rollback restores or compensates real
implementation effects and revalidates the old snapshot before moving
authority; irreversible effects require forward repair.

<!-- flowguard-rule:lifecycle.default_replacement -->

Default replacement means dispose the old path, old field, alias, wrapper, or
alternate success path. Delete, block, migrate, delegate, repair, replace, or
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
development-process simulator. Record `plan_detailing`, internal
`strategy_selection`, `agent_workflow`, and `execution_freshness` modes in that
order; delegate to PlanDetailing or
AgentWorkflowRehearsal only when explicit or simulator-selected.
DevelopmentProcessFlow owns lifecycle order/freshness; AgentWorkflowRehearsal
owns AI-operation planning. Both may reference product commitments and their
evidence without copying product behavior into their own steps. Internal
`strategy_selection` stays inactive unless `explicit_request`,
`multiple_equivalent_routes`, `material_rework_risk`, or
`diagnostic_boundary_choice` applies. When active, first prove
outcome/obligation-evidence/safety/protected-side-effect/dependency-authority/
execution-owner equivalence, then choose `targeted`, `declared_complete`, or
`budgeted` diagnosis plus `sequential` or isolation-proven `safe_parallel`
execution. Hard blockers stop invalid descendants and material evidence stales
the decision. TestMesh owns diagnostic accounting; relation-backed repair
groups use ordinary primary-owner evidence and affected revalidation.
Estimated comparison may support a preference, never a global optimum.

<!-- flowguard-rule:process.spec_context_read_only -->

When official OpenSpec is in scope, FlowGuard may read only the current
proposal, design, specifications, tasks, and task status as external planning
context. FlowGuard must not write OpenSpec files, execute provider checks,
create provider sessions/caches/receipts, claim provider execution ownership,
or place provider-internal fields in product UI. OpenSpec retains validation
and archive authority.

<!-- flowguard-rule:process.post_change_scan -->

After non-trivial FlowGuard-managed work, let DevelopmentProcessFlow consume
post-change scan signals for changed artifacts, skipped routes, stale evidence,
open obligations, or split/reduction pressure. The scan output routes each gap
to the owning specialist, such as Model-Test Alignment, Architecture
Reduction, StructureMesh, ModelMesh, TestMesh, or AgentWorkflowRehearsal.

<!-- flowguard-rule:claim.no_fake_adoption -->

Do not create a fake local FlowGuard replacement. Do not claim full FlowGuard
completion from an AGENTS/manifest/log update alone; executable model checks,
tests, replay, and closure evidence still need to be current for the claim.

<!-- END FLOWGUARD PROJECT RULES -->
