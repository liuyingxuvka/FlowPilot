# Changelog

## v0.11.2 - 2026-07-07

### Changed

- Refreshed the FlowGuard project adoption record for check-engine `0.52.5`.
- Updated the durable FlowGuard adoption log for the project-record upgrade.
- Refreshed generated FlowGuard project-topology freshness metadata after the
  release validation pass.

### Validation

- Verified the FlowGuard project audit after upgrade.
- Verified the project topology check and public release preflight before
  publishing.

## v0.11.1 - 2026-07-04

### Fixed

- Hardened FlowPilot's prompt-first quality chain so PM prompts preserve
  concrete source intent, block generic root-contract wording, and repair
  semantic dilution without adding task-family-specific workflows.
- Strengthened Reviewer prompt cards so review gates compare the current
  artifact against accepted source intent, reject process-only evidence, and
  block ledger-only final replay when delivered-output proof is missing.
- Clarified the FlowGuard operator boundary: FlowGuard evidence supports
  process/model/state confidence, while PM and Reviewer prompts own semantic
  product-quality judgment.

### Validation

- Verified prompt-card instruction coverage, planning-quality FlowGuard
  scenarios, reviewer-active-challenge scenarios, runtime semantic-boundary
  diff review, topology refresh/check, local installed-skill sync, and install
  self-check.
- Verified the OpenSpec change
  `harden-flowpilot-prompt-first-quality-chain` with `9/9` required checks
  passing.
- Verified the router background regression tier with `95/95` commands passing.

## v0.11.0 - 2026-07-03

### Changed

- Strengthened FlowPilot's PM-owned system integration duty so route plans,
  node packets, reviews, FlowGuard checks, and terminal ledgers keep whole-run
  continuity, structure, handoff relationships, and duplicate-control pressure
  visible.
- Added optimization-level Reviewer, FlowGuard operator, and Worker guidance for
  composition review, state continuity, integration touchpoints, and route-wide
  closure without adding new runtime hard blockers, roles, ledgers, packet
  families, or self-stop surfaces.
- Extended planning templates with system integration intent, route composition
  review, node integration touchpoints, and final whole-output composition
  review while preserving the current five-field node context package contract.
- Added full integration Cartesian coverage for FlowPilot planning quality so
  software, writing, research, release, repair, simple, and multi-role paths are
  checked for coherent route-wide behavior instead of isolated local completion.

### Validation

- Verified OpenSpec strict status for the `strengthen-pm-system-integration-duty`
  change and refreshed FlowGuard project topology.
- Verified focused unit coverage, card instruction coverage, planning-quality
  runners, fake-AI replay, ContractExhaustionMesh, Model-Test Alignment,
  Acceptance TestMesh, current-contract Cartesian checks, and a 132,000-cell
  integration Cartesian matrix.
- Verified router child evidence, FlowGuard meta and capability background
  regressions, installed-skill sync/audit/check, install self-check, and local
  source/package consistency before the release candidate.

## v0.10.25 - 2026-07-02

### Changed

- Hardened FlowPilot repair closure so blocker repairs preserve current dossier context, route replacement lineage, reviewer subject alignment, and five-blocker glass-break behavior.
- Clarified ordinary project material visibility while keeping sealed packet, result, report, and mail bodies under runtime authorization.
- Split the material artifact map into a stable facade plus packet/result indexing and ordinary non-sealed material scanning modules.
- Added public-material, identity-owner, final-projection, reviewer-quality, terminal-coverage, and repair-dossier verification meshes for the generalized FlowPilot control plane.

### Validation

- Verified OpenSpec strict checks and verification reports for repair dossier TestMesh, active child lineage, public material closure, and material-map structure closure.
- Verified FlowGuard material-map checks, model-test-code alignment, repair-focused pytest coverage, 240-cell repair dossier TestMesh, topology build/check, installed-skill sync/audit/check, and public release preflight.

## v0.10.24 - 2026-06-27

### Changed

- Added SkillGuard runtime-contract governance for the installed FlowPilot Codex skill materials.
- Synchronized installed skill copies with accepted source material and local git evidence.
- Recorded release-scope validation so route selection, evidence gates, quality floors, and closure boundaries remain visible before completion claims.

All notable changes to FlowPilot will be documented in this file.

## 0.10.23 - 2026-06-26

### Changed

- Hardened FlowGuard evidence review so reviewer packets now explicitly block
  shallow FlowGuard reports that only prove mechanical shape, generic process,
  or packet presence without target-specific inspection depth.
- Made FlowGuard evidence artifact resolution prefer the packet-declared
  evidence output policy path before any derived run-root path.
- Split terminal ledger traceability into focused FlowGuard-coverage and final
  ledger-writer owner modules while keeping the existing facade surface and
  current workflow contract intact.
- Registered the new terminal ledger owners in the structure-maintenance,
  facade-split, and model-test-alignment catalogs so future full diagnostics
  can see the same responsibilities the runtime uses.

### Validation

- Added direct tests for terminal FlowGuard coverage validation and final
  ledger-writer facade export parity.
- Added runtime, reviewer-card, fake end-to-end, and model-test-alignment
  checks for FlowGuard evidence-path authority and shallow FlowGuard review
  blocking.
- Re-ran FlowGuard model-test alignment, structure-maintenance checks,
  facade-split checks, topology checks, install checks, local install-sync
  audit, release tier checks, and the router-terminal background tier.

## 0.10.22 - 2026-06-25

### Fixed

- Hardened runtime-disposition-driven role dispatch so Controller follows the
  runtime's `reuse_existing_role`, `create_new_role`, or `blocked` decision
  instead of choosing whether to reuse or replace role surfaces on its own.
- Rephrased role-surface requirements around host-supported isolated AI
  execution surfaces, such as a background agent, separate thread, new
  conversation, worker, independent AI session, or equivalent host mechanism.
- Made missing or unavailable runtime-named reuse surfaces a recovery/blocker
  condition instead of silently creating a fresh same-role surface.
- Clarified that Controller foreground work cannot substitute for PM, worker,
  reviewer, or FlowGuard-operator role work unless the user explicitly
  authorizes single-agent continuity.

### Validation

- Added prompt-boundary FlowGuard scenarios for reuse replacement, Controller
  foreground role work, and Codex-only backend wording hazards.
- Added prompt-source checks and card-instruction coverage for runtime
  disposition rows, host-neutral isolated surfaces, missing-reuse recovery,
  and no-foreground-role-work behavior.
- Verified the change through OpenSpec, FlowGuard prompt-boundary, meta and
  capability checks, topology refresh, install sync/audit/check, and the
  public release preflight.

## 0.10.21 - 2026-06-25

### Fixed

- Hardened startup intake so a short "start FlowPilot" request still enters
  normal high-quality current-run project work instead of lowering the product
  target or route quality floor.
- Carried that high-quality startup posture through PM product architecture,
  route skeleton, node acceptance, packet, result, and Reviewer route-challenge
  prompt surfaces without adding new fields, launch modes, fallback paths, or
  role-facing rehearsal labels.
- Made Reviewer route challenge block structurally valid but merely passable
  routes that lack concrete user-useful output, acceptance evidence, or proof
  of depth.

### Validation

- Added planning-quality FlowGuard hazards for missing startup-quality
  projection across startup, product architecture, route design, and packets.
- Added Reviewer active-challenge coverage for route quality-floor loss.
- Refreshed prompt marker tests, runtime-card reminder checks, FlowGuard
  topology, OpenSpec verification evidence, and local install sync evidence for
  the source release.

## 0.10.20 - 2026-06-24

### Changed

- Simplified parent backward closure to one Reviewer-owned
  `review.parent_backward_replay` packet. The accepted review result is now the
  parent/module closure evidence; FlowPilot no longer creates a raw
  `task.parent_backward_replay` task followed by a second independent review.
- Made late parent-review gaps a control-plane ordering violation. If terminal
  replay or final closure sees a missing or multiple parent-review gap, the
  runtime hard-blocks instead of dispatching late repair review work.
- Kept the current-contract boundary clean: old task-shaped parent replay
  results are rejected as unsupported, with no migration, fallback translator,
  compatibility alias, or historical-state promotion.

### Validation

- Added the single-parent backward review FlowGuard model and refreshed
  current-contract Cartesian, fake-AI runtime replay, ContractExhaustionMesh,
  field-contract, historical replay, model-hierarchy, model-maturation,
  model-test alignment, and acceptance TestMesh result artifacts.
- Added runtime and fake-AI tests for one parent review packet, old task-family
  rejection, PM absorption, terminal/final hard blocks, and injected corrupt
  multi-gap states.
- Ran current router quality, packets, route, and terminal background tiers;
  all required routine child artifacts completed with exit code 0 before
  Acceptance TestMesh passed.

## 0.10.19 - 2026-06-24

### Fixed

- Added terminal FlowGuard coverage governance to the PM final-ledger path:
  final ledger creation now requires a PM-accepted current
  `flowpilot.flowguard_terminal_coverage_report.v1` and fresh coverage matrix.
- Added the mandatory `flowguard-coverage-governance` segment to terminal
  backward replay and made PM terminal closure require that segment to pass.
- Registered the dedicated
  `flowpilot.output_contract.flowguard_terminal_coverage_report.v1` role-output
  contract for the single `flowguard_operator` role.
- Updated PM, Reviewer, FlowGuard operator, evidence-package, repair, and
  closure cards so missing, stale, progress-only, blocked, or unaccepted
  terminal FlowGuard coverage cannot close the project.

### Validation

- Added the terminal FlowGuard coverage model and runner with 95 Cartesian
  fake-response hazard cases and zero misses.
- Added runtime tests for missing terminal coverage closure, progress-only
  reports, final-ledger segment recording, terminal replay, and PM closure.
- Added output-contract and install-check coverage for the new terminal
  FlowGuard coverage contract, model, runner, and result artifact.

## 0.10.18 - 2026-06-23

### Fixed

- Reused the current packet, result, and lease surfaces to block Reviewer and
  FlowGuard operator self-checks when the same agent produced the target result.
- Added submission-time blocking for already-open illegal checker leases so a
  stale or misassigned role cannot approve its own target output.
- Closed FlowGuard-approved parent backward replay directly instead of opening
  a second Reviewer packet over an already reviewed replay result.
- Aligned repeated blocker escalation so the fifth same-family, same-node
  repair stays in the ordinary PM repair lane and only the sixth attempt enters
  Controller break-glass handling.

### Validation

- Added core runtime and model scenarios for checker self-check blocking,
  independent checker reuse, parent backward replay closure ordering, and the
  corrected repeated-blocker threshold.
- Refreshed focused FlowGuard runtime, complete-system, ContractExhaustionMesh,
  Model-Test Alignment, topology, install sync, and card-instruction evidence
  for the release candidate.

## 0.10.17 - 2026-06-22

### Fixed

- Tightened PM node acceptance guidance so worker-ready nodes must name the
  current executable check surface, status vocabulary, expected failure shape,
  and bounded worker outcome before work is issued.
- Tightened Reviewer node-plan review guidance so abstract worker-ready plans
  are blocked for PM clarification, route deepening, or existing
  `redesign_route` handling instead of pushing boundary discovery to Worker.
- Made Controller user-facing status guidance normally include the
  runtime-owned expanded-node fraction when a status update is already needed,
  while keeping quiet patrol, receipts, ACK bookkeeping, and process-only
  asides internal.

### Validation

- Added prompt coverage for PM/Reviewer node-plan concrete check surfaces and
  Controller progress-fraction status boundaries.
- Added planning-quality model coverage for node plans missing current checker,
  status, failure-shape, or bounded-worker-outcome details.
- Refreshed topology and focused FlowGuard checks for planning quality,
  prework/order gates, and controller patrol behavior.
- Refreshed the controller action-ledger prompt manifest hash so release
  structure checks accept the current runtime-kit prompt asset.

## 0.10.15 - 2026-06-18

### Fixed

- Added a strict text-only Reviewer quality score rubric where `6/10` is the
  minimum user standard, `9/10` is the FlowPilot target, and `10/10`
  substantially exceeds the user's standard.
- Taught PM prompts to interpret Reviewer scores as decision context while
  preserving PM's standing choice to optimize, continue, repair, waive, stop,
  or ask the user even when Reviewer reports no blocker.
- Taught Worker repair guidance and current-scope repair packets to consume
  authorized Reviewer score context, quantitative gaps, and the `9/10` target
  without expanding packet scope.
- Extended review-window fake-AI profiles with high-score pass, soft low-score
  PM optimization, quantitative hard blocker, soft-score overblock, and
  score-context recheck cases.
- Added fake-AI runtime replay coverage that drives generated fake-AI failures
  through runtime rejection, reissue/repair, corrected second retries, and the
  fifth same-lineage break-glass threshold.
- Added a real-issue backfeed registry so newly discovered live failures must
  become a fake-AI profile, contract cell, Cartesian matrix row, and runtime
  reaction test before closure.
- Hardened review-window completeness checks so orphan, missing, mismatched,
  or prose-only Reviewer windows cannot count as covered structured review
  material.
- Tightened singleton live-evidence classification so all required live files
  are needed for full confidence and any missing or malformed file remains
  evidence-insufficient.
- Bridged fake-AI replay mutation families into the existing control-plane
  Cartesian mutation alphabet so matrix coverage keeps one current path.

### Validation

- Refreshed prompt coverage, contract-surface reduction, core runtime
  information-flow, AI contract projection, fake-AI runtime replay,
  real-issue backfeed, singleton identity, contract-exhaustion mesh, synthetic
  agent coverage, model-test alignment, topology, and Cartesian control-plane
  exhaustion tests.

## 0.10.14 - 2026-06-18

### Fixed

- Added a runtime-checkable review-window completeness matrix with stable
  `review_flow_id` rows for every current Reviewer flow.
- Required review packets to expose the declared review flow, required window
  paths, required material classes, authorized read purposes, future-stage
  boundaries, and PM repair return rule in both envelope and handoff body.
- Extended the contract-driven fake AI responder with review-window behavior
  profiles across review flow, material state, behavior profile, and retry
  count class.
- Bridged detailed review-window and fake-AI mutation families back into the
  existing control-plane Cartesian mutation alphabet with explicit canonical
  mapping instead of adding another runtime path.

### Validation

- Refreshed high-standard control-flow, fake-AI projection,
  contract-exhaustion mesh, synthetic coverage matrix, control-plane Cartesian
  matrix, reviewer challenge, reviewer-only gate, model-test alignment,
  topology, install self-check, and local install sync evidence.

## 0.10.13 - 2026-06-18

### Fixed

- Hardened fake-AI rehearsal coverage for malformed result bodies, partial
  repairs, corrected retries, finite-option mistakes, forbidden aliases, and
  hidden projection gaps.
- Surfaced planning acceptance owner coverage and node-acceptance projection
  rules in AI-visible structured contracts before the first role response.
- Added runtime-checkable reviewer windows so review packets carry the current
  subject stage, authorized read scope, forbidden future-stage demands, and PM
  repair return rules outside sealed prose.
- Kept Reviewer hard blockers on the single PM repair work path and returned
  repaired evidence to Reviewer recheck rather than allowing PM prose override.
- Aligned the same-lineage BreakGlass threshold to the fifth repeated blocker
  across runtime behavior, role cards, and card-instruction tests.

### Validation

- Refreshed fake-AI projection tests, high-standard control-flow tests,
  contract-exhaustion mesh, current-contract Cartesian matrix, executable
  matrix coverage, core runtime, card-instruction coverage, reviewer challenge,
  blocker repair information flow, model-test alignment, topology, public
  release preflight, install sync, and Meta/Capability evidence for the
  release.

## 0.10.12 - 2026-06-15

### Fixed

- Hardened parent-scope repair so replacement parent/module nodes must carry
  new active repair child nodes while preserving old children and accepted
  child results as inherited read-only history.
- Required PM parent repair output to include a structured parent repair scope
  contract with repair child specs, and blocked prose-only child routing before
  node acceptance or parent backward replay can loop.
- Hardened FlowGuard result acceptance so subject-bound evidence artifacts,
  blocker findings, missing code contracts, missing obligations, stale
  evidence, or progress-only evidence override a top-level `passed: true`.
- Counted repeated same-problem repair attempts across superseded repair
  lineage nodes so no-in-place repair no longer hides break-glass thresholds.

### Validation

- Refreshed the canonical repair-scope FlowGuard model, model-test alignment,
  fake AI rehearsals, historical replay, synthetic trace replay, topology,
  install sync, and Meta control-plane checks for the repair.
- Added OpenSpec coverage for the FlowGuard semantic recheck evidence chain and
  parent repair inheritance contract.

## 0.10.11 - 2026-06-13

### Fixed

- Hardened the final route-wide gate ledger and final requirement evidence
  matrix so stale, failed, blocked, or old-route review, FlowGuard, and
  validation evidence no longer counts as final proof.
- Tightened terminal backward replay so Reviewer results must match the exact
  runtime-issued active-route segment ids, blocking missing, duplicate, or
  unexpected segment reviews.
- Fixed final confidence aggregation so failed evidence producers cannot be
  hidden by stale green JSON, and control-plane live audits can separate the
  target project root from the FlowPilot source root.
- Updated the known-friction risk ledger to the current FlowGuard
  `RiskEvidenceRow`/`RiskEvidenceGate` contract.
- Kept visible progress and repair control-plane state on the current active
  route by excluding superseded repair history from completion display,
  preserving route hierarchy on redesign, retiring stale repair blockers, and
  strengthening same-node repair-loop and handoff-blocker lifecycle guards.

### Validation

- Refreshed FlowGuard model-test alignment, closure, route hard-gate, card
  coverage, final confidence, topology, local install sync, Meta/Capability,
  fake-project rehearsal, real-router rehearsal, shadow-launcher chaos, E2E
  synthetic chaos, and synthetic trace evidence for the release.

## 0.10.10 - 2026-06-11

### Fixed

- Fixed the node acceptance plan review stage boundary so Reviewer evaluates
  PM's node plan as a planning artifact before Worker dispatch instead of
  demanding Worker-produced evidence too early.
- Kept FlowGuard evidence requirements tied to the current review stage:
  ordinary node-plan review does not require matching FlowGuard evidence, while
  structural route redesigns still require FlowGuard simulation, PM absorption,
  Reviewer review, and system validation before route mutation commits.
- Refreshed fake-AI rehearsal, current-node trunk modeling, Model-Test
  Alignment, topology, install sync, and Meta/Capability evidence for the
  stage-boundary repair.

## 0.10.9 - 2026-06-11

### Changed

- Replaced the ordinary per-node pre-work FlowGuard gate with a lighter current
  node trunk: PM node-entry self-check, ordinary node-plan Reviewer review,
  Worker execution, post-result FlowGuard, and independent Reviewer review.
- Added the structural PM route-change gate: PM `redesign_route` decisions now
  stage the route effect, require FlowGuard simulation of the current
  route/work/validation/failure/repair path, require PM
  `pm_flowguard_acceptance`, and only then proceed to Reviewer and system
  validation before route mutation commits.
- Tightened FlowGuard Operator, PM, and Reviewer cards so FlowGuard models the
  current packet subject only, cannot mutate routes or release workers, and
  Reviewer must block unabsorbed structural FlowGuard reports.
- Refreshed fake-AI rehearsal, FieldContract, FieldMesh, Model-Test Alignment,
  topology, install sync, and Meta/Capability evidence for the new
  no-fallback route gate.

### Fixed

- Preserved the model-test negative-test anchor for staged-effect formal
  blocker identity so field-contract source alignment stays fresh after test
  refactoring.

## 0.10.8 - 2026-06-09

### Changed

- Added a planning-time route decomposition quality gate: PM must produce one
  executable route tree with small worker-ready leaves, FlowGuard checks for
  worker-decision leakage, and Reviewer blocks broad or overlapping leaves
  before route materialization.
- Hardened recursive route depth and parent/module traversal so broad parent
  nodes do not dispatch directly to workers and route replay keeps current
  branch evidence tied to the active route.
- Integrated the latest current-contract maintenance work for FlowGuard
  evidence consistency and field lifecycle currentness into the same release
  line.

### Fixed

- Updated prompt-card and regression coverage so route decomposition quality is
  judged semantically instead of by adding broad per-node fields.
- Refreshed FlowGuard topology, local install sync, public release checks, and
  targeted model/test evidence for the new planning and review gates.

## 0.10.7 - 2026-06-08

### Changed

- Refreshed the public README startup intake screenshot so the GitHub product
  preview matches the polished WPF startup UI with the compact project request
  field, neutral border treatment, smaller controls, and `Start FlowPilot`
  action.
- Updated visible README version text for the source-package release while
  keeping the runtime behavior unchanged from the current `v0.10.6` contract
  line.

## 0.10.6 - 2026-06-08

### Changed

- Integrated the parallel current-contract maintenance work into one release
  line: runtime contract checks, FlowGuard field/model alignment, fake-AI
  rehearsal, topology evidence, and install validation now describe the same
  strict current FlowPilot path.
- Refreshed the fake-project rehearsal so all 14 declared scenarios run
  through the public current CLI surface while still rejecting old generic
  result shapes instead of translating them.
- Kept terminal backward replay on the current final-closure route, so a
  terminal block issues the current reviewer replay packet instead of falling
  back into planning or replanning.

### Fixed

- Removed the stale fake-AI missing-fields assertion that expected old
  `decision`-style repair requirements; the scenario now checks the current
  handoff contract fields and confirms `decision` is not required where the
  current family forbids it.
- Refreshed Model-Test Alignment, FieldContract, topology, and install evidence
  after the three parallel maintenance threads converged on the same
  no-fallback contract chain.

## 0.10.5 - 2026-06-07

### Breaking

- Replaced the normal public `resolve-role-assignment` plus `lease-agent`
  sequence with one current `dispatch-current-role` path while keeping
  responsibility, liveness, reuse, replacement, and self-review checks owned by
  the runtime.
- Tightened current packet/result branch contracts so conditional outputs such
  as PM route redesign must use the declared branch shape; hidden fields,
  undeclared fake-AI success shapes, and legacy public wrappers are rejected.

### Changed

- Made `flowpilot_new.py open-packet` deliver authorized input materials for
  the assigned role, so sealed result/report bodies still flow through the
  current runtime but no longer require a separate normal-path `open-result`
  micro-step.
- Added branch-specific minimal valid shapes to handoff and reissue metadata so
  roles can repair missing nested fields from the current packet instead of
  relying on hidden runtime knowledge.
- Refreshed FieldContract, project-control information flow, Model-Test
  Alignment, fake-AI rehearsal, topology, install sync, and meta/capability
  evidence for the strict current-contract path.
- Bound the new packet-open material delivery path into FlowGuard
  information-flow alignment, blocker repair modeling, prompt markers, and
  fake-project rehearsal evidence.
- Refreshed strict packet handoff contracts, prompt hashes, fake-AI package
  paths, and runtime regression evidence for the current no-fallback path.
- Updated the FlowGuard project adoption record to the currently installed
  `0.41.7` package during the release preflight.

## 0.10.4 - 2026-06-07

### Breaking

- Made packet/result contracts the single source of truth for current runtime
  mechanical checks; old generic wrappers and legacy field aliases are rejected
  instead of translated.
- Removed the remaining child-skill `skill_decisions` compatibility shape from
  the current router path; current child-skill selection uses `selected_skills`
  only.

### Changed

- Added the shared `packet_result_contracts.py` contract table and bound
  runtime reissue metadata, fake-AI success bodies, negative contract-chaos
  rehearsals, FieldContract, FieldMesh, and Model-Test Alignment to it.
- Kept high-standard contract success on top-level `requirements` while
  mechanically reissuing missing fields and forbidden hidden `decision`/old
  contract rows through the same current packet family.
- Refreshed topology, layered Meta/Capability evidence, install checks, and
  README current-path wording for the strict no-fallback runtime.

## 0.10.3 - 2026-06-04

### Breaking

- Replaced the PM repair decision surface with the canonical five-choice menu:
  `repair_current_scope`, `repair_parent_scope`, `redesign_route`,
  `waive_with_authority`, and `stop_for_user`.
- Removed acceptance of old repair decisions such as `same_node_repair`,
  `sender_reissue`, `collect_more_evidence`, `mutate_route`, and
  `quarantine_evidence`; current FlowPilot now rejects them instead of
  translating or falling back.

### Changed

- Made every nonterminal repair prove that runtime opened a fresh current
  executable packet before the blocker can move to `repair_packet_open`.
- Added current-scope, parent-scope, route-redesign, authorized-waiver, and
  June 3 empty-fresh-packet regression coverage with a dedicated FlowGuard
  repair-scope rotation model.
- Updated PM-facing cards, resume contracts, and control-plane references to
  expose the current repair vocabulary only.

## 0.10.2 - 2026-06-04

### Changed

- Hardened current-contract gates so staged node acceptance plans and route
  mutations stay pending until current FlowGuard and Reviewer gates inspect the
  real submitted artifact.
- Added controller progress-fraction reporting plus stricter role assignment
  resolution and role-continuity memory checks for current-run role bindings.
- Refined `lease_agent` guidance to prefer durable, addressable role surfaces
  without practical parallel-count or model-capability limits when such
  surfaces are available.
- Added focused staged-effect and prompt-coverage tests, refreshed capability
  evidence, and rebuilt the FlowGuard project topology.

## 0.10.1 - 2026-06-02

### Changed

- Reflowed the Windows WPF startup intake UI into a narrower single-column
  layout with the background-collaboration toggle above the work request field.
- Refreshed the README and startup-intake screenshot to match the current UI
  and to state explicitly that FlowPilot is developed with FlowGuard.
- Published the latest no-compatibility FlowPilot runtime cleanup, including
  legacy prompt-surface removal, relay-protocol cleanup, role packet access
  hardening, and refreshed FlowGuard topology/evidence artifacts.
- Added structural convergence gates across FlowPilot PM planning, worker
  packet/result surfaces, reviewer checks, final ledgers, terminal closure, and
  the planning-quality FlowGuard model so long-running routes must dispose of
  structure debt instead of accumulating fallback or compatibility residue.

## 0.10.0 - 2026-05-31

### Breaking

- Removed legacy fixed-topology language from current FlowPilot prompts,
  templates, runtime cards, models, and tests. Current FlowPilot uses the
  single `flowguard_operator` responsibility for FlowGuard work and generic
  requested worker responsibilities instead of Process/Product FlowGuard
  officer split roles or fixed Worker A/B cohorts.
- Made route-node work depend on current requested responsibilities, current
  FlowGuard evidence, and current blocker views rather than old compatibility
  aliases or prose-inferred outcomes.

### Added

- Added OpenSpec change packages for host-neutral role surfaces, mandatory
  route-node pre-work FlowGuard gates, PM-authored node context packages, and
  current-effective packet outcome authority.
- Added a focused pre-work FlowGuard node-gate model and runner covering PM
  node context packages, pre-work FlowGuard checks, worker release, post-result
  FlowGuard, independent review, repair, and stale-evidence hazards.
- Added new FlowGuard operator role/card surfaces and lifecycle templates that
  use the current `flowguard_operator` vocabulary.

### Changed

- Updated README, protocol, schema, HANDOFF, runtime kit cards, templates,
  tests, simulations, prompt manifests, and install checks to describe the
  current new FlowPilot runtime rather than the old fixed-role topology.
- Rebuilt FlowGuard project topology and synchronized the repo-owned installed
  FlowPilot skill with the repository source.

## 0.9.25 - 2026-05-30

### Added

- Added the `add-flowguard-project-topology-map` OpenSpec change.
- Added an automatically generated FlowGuard project topology map at
  `docs/flowguard_project_topology.md` and
  `docs/flowguard_project_topology.json`, covering model runners, model-test
  alignment families, code surfaces, test commands, evidence summaries, and
  known-bad/risk signals.
- Added `scripts/flowguard_project_topology.py` with `build` and `check`
  commands plus focused unit tests for freshness, required layers, and
  machine-readable findings.
- Added a dedicated FlowGuard project-topology orientation model with
  known-bad coverage for skipped topology intake, stale topology, missing
  layers, topology-as-validation overclaim, source changes without refresh,
  and PM/Reviewer/Controller role-authority misuse.

### Changed

- Updated FlowPilot PM, Process Officer, Product Officer, Reviewer, and phase
  cards so mature FlowGuard projects read the topology map as background
  architecture before non-trivial work.
- Clarified that topology is orientation only: it can guide which models,
  tests, code areas, evidence summaries, and known-bad signals to inspect, but
  it cannot replace FlowGuard Reports, tests, validation evidence, gate
  evidence, route mutation authority, or completion evidence.
- Wired topology generation/checks into smoke, fast-tier, install-readiness,
  coverage-sweep, and maintenance registry surfaces.

## 0.9.24 - 2026-05-30

### Added

- Added the `add-new-flowpilot-lifecycle-guard` OpenSpec change.
- Added a metadata-only lifecycle guard for the new formal runtime, including
  current-run guard snapshots, stop authority, patrol history, resume
  rehydration, repeated-action detection, and stale result quarantine.
- Added public `patrol` and `resume` commands for the new runtime path.
- Added lifecycle FlowGuard checks, model-test alignment rows, and focused
  lifecycle guard tests.

### Changed

- Updated fake AI black-box rehearsal to cover lifecycle resume and patrol
  recovery paths without restoring the old monitor UI or fixed-role topology.
- Updated run-shell persistence so ordinary repeated saves refresh the latest
  guard snapshot without appending fake lifecycle progress events.
- Upgraded the project FlowGuard adoption record to package `0.39.0`.

## 0.9.23 - 2026-05-30

### Added

- Added the `adopt-high-standard-flowpilot-control-flow` OpenSpec change.
- Added high-standard pre-planning gates for PM outcome contracts, current
  material discovery, local skill inventory, and selected skill obligations.
- Added node acceptance plans, same-node repair generations, parent backward
  replay, and final requirement-evidence matrix support to the new formal
  runtime.
- Added focused high-standard runtime tests and recursive FlowGuard hazards for
  planning before gates, node work before acceptance planning, manifest-only
  skill evidence, default route mutation on quality gaps, missing parent replay,
  and final closure without requirement evidence.

### Changed

- Updated the fake-host rehearsal so it drives the new high-standard gate chain
  before traversing route nodes.
- Updated run-shell projections and public status output to expose
  high-standard gate status, repair generation, parent replay, and final matrix
  metadata without exposing sealed bodies.

## 0.9.22 - 2026-05-29

### Added

- Added the `restore-recursive-route-execution-runtime` OpenSpec change.
- Added recursive route execution FlowGuard checks for PM-plan terminal
  overclaim, missing node closure, wrong FlowGuard target, stale evidence,
  dead lease advancement, and route mutation without frontier rewrite.
- Added focused runtime tests for route materialization, node packet loops, PM
  disposition, route mutation, closure blockers, and public route/frontier
  status projection.

### Changed

- Updated the new formal FlowPilot runtime so PM planning materializes route
  nodes instead of completing the project after the first PM packet chain.
- Expanded the black-box fake-project rehearsal to run a multi-node route
  through the public CLI and report explicit recursive-route bad-case rows.
- Split the fake-project rehearsal runner into CLI and scenario child modules
  after model-test diagnostics flagged the parent runner as oversized.
- Upgraded the project FlowGuard adoption record to package `0.38.0`.

## 0.9.21 - 2026-05-29

### Changed

- Hardened the new formal FlowPilot runtime so fixed-value operator fields
  list their allowed values directly, including `--host-kind live|fake|dry_run`.
- Updated FlowGuard operator packets to require run-local evidence output under
  the current `.flowpilot/runs/<run-id>/evidence/flowguard/...` tree.
- Added `--json-out` and proof override support to Meta and Capability runners
  so formal run evidence no longer dirties tracked simulation baselines.

### Added

- Added the `harden-flowpilot-enum-prompts-and-run-evidence` OpenSpec change.
- Added FlowGuard hazards and tests for missing host-kind menus, invented host
  kinds, and formal FlowGuard evidence written to tracked baselines.
- Added model-test alignment evidence for enum menu guidance and run-local
  FlowGuard evidence isolation.

## 0.9.20 - 2026-05-29

### Changed

- Reworked the new FlowPilot formal runtime so PM, FlowGuard operator,
  Reviewer, Validator, and Closure officer all use the same packet lifecycle:
  issued packet, lease, ACK, sealed result, packet-owned ledger side effect,
  and next packet.
- Removed the unsupported formal side-command surface from `flowpilot_new.py`;
  fresh formal operation now advances through `dispatch-current-role`, `ack`,
  `open-packet`, and `submit-result` only after startup.
- Updated fake-host rehearsal, runtime scenario runners, and complete-system
  runtime checks to exercise the full role-packet chain instead of injecting
  FlowGuard/review/validation/closure evidence directly.
- Reordered the fast smoke check so model hierarchy proof consumes fresh
  meta/capability parent proofs instead of stale files.

### Added

- Added the `unify-new-flowpilot-work-packet-lifecycle` OpenSpec change.
- Added a focused FlowGuard symmetric work-packet lifecycle model with hazards
  for non-packet role leases, ACK-only completion, PM-only terminal closure,
  side-command completion, dirty reviewer/FlowGuard projections, and lingering
  active leases.
- Added regression tests for the live-run miss: FlowGuard operator cannot be
  leased against the PM packet, Reviewer status must carry packet id and ACK,
  and completed role packets must leave no active dirty lease rows.
- Added a real black-box fake-project rehearsal that starts through the
  startup intake script, drives only public CLI packet commands, and covers
  normal completion plus wrong-role, missing-ACK, ACK-only, and unsupported
  side-command error flows.
- Added model-test alignment obligations and source-audited evidence for the
  symmetric packet lifecycle, black-box fake-project rehearsal, and unsupported
  side-command surface.

## 0.9.19 - 2026-05-29

### Added

- Added the `generate-new-flowpilot-formal-entrypoint` OpenSpec change for a
  fresh FlowPilot entrypoint that reuses only the native startup intake UI and
  then runs through the new current-run ledger.
- Added `skills/flowpilot/assets/flowpilot_new.py` with start, status,
  dynamic lease, ACK, result, FlowGuard, review, validation, closure, and
  fake end-to-end rehearsal commands.
- Added a focused FlowGuard model and tests for the new startup UI -> sealed
  intake -> new ledger -> dynamic lease -> FlowGuard -> review -> closure path.

### Changed

- Updated `Use FlowPilot` skill instructions so new formal starts enter
  `flowpilot_new.py start`; the old router is reference/diagnostic material
  for old runs, not fresh-run authority.
- Made public console projection explicitly report that sealed bodies are not
  visible and made router cutover-gate handling tolerate unevaluated new-run
  ledgers.

## 0.9.18 - 2026-05-29

### Added

- Added the `complete-black-box-flowpilot-system` OpenSpec change for the
  full new FlowPilot system contract: current-run ledger authority, dynamic
  leases, modeled FlowGuard work orders, startup intake, Cockpit/status,
  review/repair/closure, migration/cutover, historical replay, install sync,
  background regression, and live-host evidence gates.
- Extended `flowpilot_core_runtime` with current-run shell persistence,
  append-only event projection, startup-intake import, dynamic host evidence,
  route mutation records, FlowGuard proof boundaries, review metadata,
  Cockpit fallback, migration gates, and materialized run artifacts.
- Added complete-system FlowGuard development-process, code-structure,
  UI-flow, TestMesh, and model-test-alignment models plus focused runtime,
  historical replay, live-host readiness, and implementation tests.
- Added local live host-agent evidence from real Codex multi-agent sidecar
  runs, with the claim boundary kept local to this machine and not treated as
  a remote deployment or public release.

### Changed

- Updated install checks so complete-system OpenSpec files, runtime modules,
  simulations, result artifacts, live-host evidence, and tests are covered by
  source/install parity.
- Kept the old FlowPilot runtime as reference/diagnostic material; old state,
  stale projection, stale proof artifacts, and completion-report-only claims do
  not become current-run authority.

## 0.9.17 - 2026-05-29

### Added

- Added the `build-black-box-flowpilot-runtime` OpenSpec change for the clean
  black-box runtime that turns the protocol kernel into executable ledger,
  lease, packet, review, FlowGuard, closure, and console behavior.
- Added `skills/flowpilot/assets/flowpilot_core_runtime/` with a serializable
  project ledger, dynamic agent leases, sealed task/result packets,
  FlowGuard work-order scheduling, independent review, final backward closure,
  and safe public console projection.
- Added a FlowGuard development-process model and runtime scenario runner for
  replacement-worker success, ACK-only timeout, closed-lease late output, wrong
  FlowGuard targets, self-review, stale route output, stale evidence, and
  console body isolation.
- Added focused runtime tests and TestMesh-style routine/release evidence rows
  so routine checks cannot overclaim background or install parity.

### Changed

- Updated install checks so the clean runtime assets, simulations, result
  artifacts, and tests are part of local source/install parity.
- Kept the clean runtime additive: unsupported historical FlowPilot remains reference material,
  while old runtime state and fixed runtime-role startup are not accepted as new
  runtime authority.

## 0.9.16 - 2026-05-29

### Added

- Added the `stress-test-ai-project-protocol-kernel` OpenSpec change for
  deterministic multi-round fake-AI stress testing of the clean AI project
  protocol kernel.
- Added protocol stress-testing documentation covering fake actors, replacement
  workers, historical bad-case replay, seeded long-run checks, FlowGuard target
  discipline, and TestMesh evidence rows.
- Added `simulations/flowpilot_protocol_kernel_stress_model.py` and
  `simulations/run_flowpilot_protocol_kernel_stress_checks.py` to rehearse multi-round
  leases, stale route returns, weak/self review, stale evidence, progress-only
  background evidence, wrong FlowGuard targets, and final closure gaps.
- Added focused tests for the stress harness, historical replay, random
  reproducibility, replacement-worker success, and routine/release TestMesh
  evidence boundaries.

### Changed

- Updated install checks so the new stress assets, runner, result artifact, and
  tests are part of local source/install parity.
- Kept release-level stress confidence gated on inspected background Meta and
  Capability artifacts plus local install parity; routine stress checks do not
  overclaim those rows before they run.

## 0.9.15 - 2026-05-29

### Added

- Added the `introduce-ai-project-protocol-kernel` OpenSpec change for a clean
  AI project execution protocol that uses a black-box ledger, dynamic
  runtime-role leases, sealed task/result packets, independent review,
  FlowGuard route scheduling, and final backward closure.
- Added a unsupported historical source snapshot under
  `backups/ai-project-protocol-unsupported historical-snapshot-20260529/` so old FlowPilot
  assets and failure cases remain read-only references instead of the new
  protocol foundation.
- Added `skills/flowpilot/assets/flowpilot_protocol_kernel/` with the protocol
  contract, schema examples, and FlowGuard route scheduler table.
- Added `simulations/flowpilot_protocol_kernel_model.py` and
  `simulations/run_flowpilot_protocol_kernel_checks.py` to rehearse fake-agent
  success and failure paths before runtime integration.
- Added focused tests for the AI project protocol kernel assets, route table,
  model checks, and false-completion hazards.

### Changed

- Kept this as a local protocol-kernel version: it does not replace the current
  FlowPilot runtime, launch a new full UI, push, tag, deploy, or release.
- Documented that ACK, progress, stale evidence, closed-agent output,
  self-review, weak review, wrong FlowGuard target, and missing final backward
  closure are blockers rather than completion evidence.

## 0.9.14 - 2026-05-27

### Added

- Added the `complete-flowpilot-maintenance-convergence` OpenSpec change for
  local maintenance convergence, archive cleanup, read-only runtime retention
  evidence, targeted StructureMesh contraction, and install-sync closure.
- Added a maintenance convergence report at
  `docs/flowpilot_maintenance_convergence_20260527.md` and refreshed the
  generated maintenance map.
- Added phase-owned external event data modules, PM package disposition helper
  modules, and process-contract helpers while preserving existing import
  facades.

### Changed

- Archived completed OpenSpec backlog items under `openspec/changes/archive/`
  so only the current maintenance convergence change remains active.
- Updated model-test-code alignment metadata for the new child modules; the
  current alignment report covers 857 surfaces with 0 gaps and 0 deferred
  structure splits.
- Kept `.flowpilot` runtime cleanup read-only because another agent-owned
  active run is present; live-run audit findings are reported but not repaired
  by mutating peer runtime state.
- Kept this as a local-only maintenance version; GitHub push, tag, and remote
  release remain intentionally out of scope.

## 0.9.13 - 2026-05-18

### Added

- Added the `harden-flowpilot-daemon-lock-terminal-fence` OpenSpec change for
  Router daemon write-lock recovery and terminal lifecycle fencing.
- Added the `harden-router-reconciliation-gate` OpenSpec change for
  Router/Controller receipt reconciliation, stateful postcondition replay, and
  duplicate-dispatch prevention.
- Added focused runtime regressions for fresh dead-owner JSON write-lock
  takeover, live-writer deferral, immediate terminal daemon fencing, terminal
  startup scheduling, and terminal heartbeat no-ops.

### Changed

- Hardened runtime JSON write-lock classification so fresh locks owned by dead
  processes are taken over with durable diagnostics, while live or uncertain
  writer contention remains daemon-deferrable instead of becoming a fatal
  Router daemon error.
- Made user stop/cancel requests write an immediate terminal fence that closes
  daemon mode, marks daemon lock/status terminal, and refreshes terminal
  projections from one terminal fact before best-effort nonterminal
  Controller/startup cleanup runs.
- Guarded Router daemon start/tick, startup daemon scheduling, startup
  bootloader heartbeat handling, Controller receipt effects, and heartbeat
  binding actions so terminal runs cannot schedule or bind new active work.
- Replayed or reclaimed Router-owned stateful postconditions for already
  reconciled Controller rows before new dispatch decisions; missing evidence now
  routes to bounded retry/control-blocker handling instead of reissuing the same
  ordinary Controller command.

## 0.9.12 - 2026-05-18

### Added

- Added the `final-owner-module-polish` OpenSpec change for the final
  StructureMesh-guided owner-module polish pass.
- Added focused owner modules for packet control-plane transitions, action
  factory reconciliation/dispatch/envelope helpers, PM role-work
  gates/writes/lifecycle/actions, terminal ledger summary/traceability/closure
  recovery, Controller scheduler receipt writes/effects/pending/scheduled
  reconciliation, and facade export manifest shards.

### Changed

- Reduced the remaining heavy unsupported historical facades to small import surfaces
  while preserving router exports, bound-router behavior, and packet
  control-plane model behavior.
- Updated StructureMesh/TestMesh/model-alignment evidence, install required
  files, and PromptStore manifest hashes for the new owner boundaries.
- Split the router background regression parent into smaller TestMesh child
  commands for startup, foreground/controller, and packet domains so slow
  validation can run with bounded parallelism and clearer failure ownership.
- Kept this as a local-only maintenance version; GitHub push, tag, and remote
  release remain intentionally out of scope.

## 0.9.11 - 2026-05-18

### Added

- Added maintainer documentation for the current runtime clarity split,
  including router facade export manifest notes, focused packet/card runtime
  helpers, user-flow diagram helpers, and packet control-plane model helpers.
- Added prompt-store documentation for packet prompt fragments under
  `runtime_kit/prompts/packets/` and their hash-managed manifest entries.

### Changed

- Refreshed unsupported historical prompt/card and system-card bundle maintenance notes so
  future work targets the new facades and helper modules instead of stale
  monolithic runtime files.

## 0.9.10 - 2026-05-17

### Added

- Added the `final-router-skeleton-cleanup` OpenSpec change for the final
  StructureMesh-guided router skeleton and owner-module cleanup pass.
- Added second-level owner modules for startup bootloader/intake/display,
  role recovery, startup closure, startup fact-boundary checks, protocol
  catalogs, work packets, event repair, route artifacts, controller
  scheduling/repair, route frontier, system cards, and action handlers.

### Changed

- Reduced `flowpilot_router.py` to a public skeleton with an explicit
  owner-export registry and no behavior-bearing top-level function bodies.
- Split the largest router owner modules by cohesive behavior boundaries while
  preserving CLI/runtime behavior, prompt asset hashes, install checks, and
  FlowGuard StructureMesh/TestMesh evidence.
- Prepared local v0.9.10 maintenance materials only; GitHub push, tag, and
  remote release are intentionally deferred.

## 0.9.9 - 2026-05-17

### Added

- Added the `continue-router-facade-slimming` OpenSpec change for the next
  StructureMesh-guided router facade maintenance wave.
- Added focused router owner modules for self-interrogation,
  Controller repair, action factory/dispatch gates, payload contracts,
  lifecycle requests, route artifacts, system-card delivery, and expected-wait
  helpers.

### Changed

- Reduced `flowpilot_router.py` to a much smaller unsupported historical facade while
  preserving public names, imports, persisted JSON shapes, and CLI behavior.
- Updated StructureMesh/TestMesh evidence, card-instruction coverage scanning,
  handoff notes, and local version metadata for the new router owner modules.
- Prepared local release materials for v0.9.9; GitHub push, tag, and remote
  release are intentionally deferred.

## 0.9.8 - 2026-05-17

### Added

- Added the `adopt-structuremesh-target-split-and-slim-router` OpenSpec change
  for the upgraded StructureMesh target-structure workflow.
- Added model-derived `CodeStructureRecommendation` target structures to the
  router facade and structure-maintenance FlowGuard gates.
- Added model-derived TestMesh target split derivations so parent validation
  gates explicitly cover child suites and partitions before release confidence
  is claimed.
- Added `flowpilot_router_protocol_catalog.py` as the owner for router schema,
  action, event, system-card, gate-contract, and protocol catalog tables.

### Changed

- Reduced `flowpilot_router.py` further by moving the large declarative
  protocol/catalog band behind the unsupported historical facade.
- Updated StructureMesh ownership evidence for the new protocol catalog owner
  while preserving the public router import and CLI paths.
- Prepared local release materials for v0.9.8; GitHub push and remote release
  are intentionally deferred.

## 0.9.7 - 2026-05-17

### Added

- Added the `simplify-python-structure` OpenSpec change and a structural
  FlowGuard guard for the second Python maintainability pass.
- Added focused helper modules for packet runtime schema, paths, contracts,
  ledgers, relay, active-holder, session, and reviewer responsibilities.
- Added install-check helper modules for file, manifest, runtime, docs, result,
  and runner responsibilities.
- Added Meta and Capability model phase helper modules while preserving the
  parent model entrypoints.
- Added router runtime domain entrypoints for bootstrap/CLI, foreground,
  PM role work, material/modeling, control blockers, and quality gates.
- Added event-contract FlowGuard coverage for explicit event envelopes
  submitted outside the current Router wait state.
- Added the `final-flowpilot-structure-convergence` OpenSpec change and
  verification matrix for the final local structure-maintenance pass.
- Added the `structuremesh-router-model-cleanup` OpenSpec change and an
  executable StructureMesh/TestMesh maintenance gate for router structure,
  split child-model facades, and background validation evidence.
- Added focused helper modules for role-output runtime schema, contracts,
  progress records, envelopes, and CLI handling.
- Added split helper modules for control-plane friction, router-loop, and
  daemon reconciliation FlowGuard child models.
- Added split helper modules for prompt-isolation, cross-plane friction, and
  persistent router daemon FlowGuard child models.
- Added a FlowGuard Model-Test Alignment runner and documentation that map
  major model obligations to ordinary test evidence and reject missing, stale,
  progress-only, orphan, duplicate, and overclaimed evidence.
- Added a PromptStore-backed prompt asset manifest for selected Router prompts,
  with strict hash checks and no inline fallback when a prompt asset is missing
  or stale.
- Added a router-facade split FlowGuard check for PromptStore, prompt-delivery,
  card-delivery, Controller-ledger, and role-output protocol ownership.

### Changed

- Converted `scripts/flowpilot_user_flow_diagram.py` and
  `scripts/check_install.py` into unsupported historical entrypoints backed by smaller
  source-of-truth modules.
- Reduced `packet_runtime.py`, `meta_model.py`, and `capability_model.py` into
  facade-style modules that delegate cohesive work to focused helpers.
- Moved selected router external-event intake and controller action helper
  logic behind smaller module boundaries without changing public event names,
  command arguments, imports, or persisted JSON shapes.
- Converted the aggregate router runtime test file into a unsupported historical loader
  backed by direct domain-owned test modules.
- Moved low-risk external-event finalization and additional Controller action
  bodies behind focused router helper modules.
- Converted prompt-isolation, cross-plane friction, and persistent router
  daemon models into unsupported historical facades backed by state, transition,
  invariant, hazard, audit, and strategy helpers where applicable.
- Split the router validation tier into smaller packet/card/ACK, route,
  terminal/closure/resume, and supporting child suites while keeping release
  regressions background-oriented.
- Split the slow route-mutation runtime oracle into focused child suites for
  draft activation, model-miss triage, acceptance repair, preconditions,
  repair transactions, topology, sibling replacement, and parent backward
  replay.
- Hid Windows subprocess windows for the test-tier runner so background and
  foreground child checks no longer interrupt desktop work while still writing
  the stable background artifact set.
- Cleared stale background artifacts before relaunching a child suite so a
  previous failed `.exit.txt` cannot be counted as the current run result.
- Moved selected Controller prompt, card delivery, Controller action-ledger, and
  role-output protocol helpers out of `flowpilot_router.py` while preserving the
  router facade and public CLI/import contract.

### Fixed

- Rejected explicit runtime event-envelope submissions before startup/current
  scope reconciliation can turn an event outside the current wait into a
  recoverable wait.
- Restored complete one-to-one router runtime domain-test coverage: every
  aggregate `test_*` method is owned by exactly one split domain entrypoint.

## 0.9.6 - 2026-05-16

### Added

- Added focused FlowGuard coverage for sibling branch replacement, replay-scope
  declaration, old current-node packet disposition, stale sibling evidence, and
  final-ledger blocking after route mutation.
- Added route-sign coverage for sibling replacement edges and replay-scope
  projection.

### Fixed

- Allowed `sibling_branch_replacement` route mutations to explicitly replace
  affected sibling nodes without forcing a return edge to the old node.
- Marked old current-node packets as superseded by route mutation so stale PM
  packet obligations no longer block the fresh route recheck path.
- Kept final route-wide ledgers blocked until pending route mutations are
  rechecked, activated, and same-scope replay has run.

## 0.9.5 - 2026-05-16

### Added

- Added focused FlowGuard coverage for recursive parent/module route entry and
  terminal closure reconciliation.
- Added final-ledger and terminal-closure reconciliation records for defect
  ledgers, role memory, and continuation quarantine/imported artifacts.

### Fixed

- Prevented recursive route traversal from skipping a sibling parent/module and
  jumping directly into its child leaf after the previous parent closes.
- Blocked terminal closure when a present defect ledger, role-memory packet, or
  continuation quarantine record is dirty.

## 0.9.4 - 2026-05-16

### Added

- Added runtime-closure guards for officer request lifecycle tracking,
  continuation quarantine, final user-report metadata, and route-display
  refresh evidence.
- Added focused FlowGuard coverage and runtime tests for those closure
  boundaries.

### Changed

- Updated install checks, templates, OpenSpec artifacts, and maintenance docs
  so the local installed skill can be synchronized from the hardened source.

## 0.9.3 - 2026-05-16

### Changed

- Split router runtime helper boundaries into focused modules for Controller
  reconciliation, ACK/return settlement identity, startup/daemon liveness,
  dispatch gating, terminal summary helpers, router protocol tables, IO, and
  runtime errors while preserving the existing router facade.
- Added focused runtime test entrypoints so ACK/return, Controller,
  startup/daemon, dispatch/packet gate, and terminal closure behavior can be
  checked without rerunning the full monolithic runtime suite every time.
- Added OpenSpec records for the ACK busy-clearance repair and both router
  boundary maintenance passes, with FlowGuard adoption notes and verification
  evidence.

### Fixed

- Kept ACK-only wait settlement separate from output-bearing work completion so
  stale ACK waits stop blocking roles without prematurely completing semantic
  PM or role work.
- Preserved the router facade import surface after helper extraction, including
  the role-output envelope helper used by dispatch paths.
- Recovered terminal closure approval when durable terminal authorities prove a
  unsupported historical run is already closed.
- Synchronized local installed FlowPilot skill freshness after the main-branch
  merge so the installed skill matches the repository source.

## 0.9.2 - 2026-05-14

### Fixed

- Fixed startup intake icon packaging so the local skill install receives the
  current repo-owned icon asset.
- Kept Controller execution alive when a role-output RouterError carries a
  control blocker, returning the Router-selected next action instead of
  dropping the chain until a later resume.
- Reconciled valid direct card ACKs at Router event ingress before blocking a
  later role report for an unresolved card return.
- Added same-role missing-ACK report recovery: premature dependency-matched
  role reports are quarantined as audit-only, the role is sent back through the
  card ACK path, and only a fresh post-ACK report is accepted.

### Changed

- Expanded FlowGuard control-plane coverage for direct ACK races, control
  blocker handoff recovery, and missing-ACK report quarantine hazards.

## 0.9.1 - 2026-05-13

### Changed

- Simplified the route-skeleton default speed profile so PM-accepted Process
  route models now flow directly to Reviewer route challenge without a second
  Product Officer route fit review.
- Kept Product protection upstream through the Product Officer product behavior
  model and PM product-model acceptance, while Process route checks now verify
  route coverage against that product model.
- Reduced final-closure role slices to PM and Reviewer while preserving all
  unsupported historical completion obligations, final ledger, and backward replay checks.
- Marked Product route check events as unsupported historical unsupported historical paths instead of
  default route-skeleton gates.

### Fixed

- Updated FlowGuard route hard-gate, next-recipient, barrier equivalence,
  optimization proposal, and control-plane friction models so reintroduced
  hidden Product route waits, missing product-model coverage, missing PM
  process acceptance, and missing Reviewer route challenge are detected.
- Refreshed route cards, runtime source-path requirements, and router tests to
  match the reviewer-only route challenge handoff.

## 0.9.0 - 2026-05-13

### Added

- Added FlowGuard models and check runners for model-driven recursive route
  governance, legal next-action selection, PM package absorption, parent-child
  lifecycle checks, dynamic return paths, terminal summaries, and expanded
  model-mesh evidence.
- Added route action policy coverage and runtime cards for PM-owned process
  route model decisions, product behavior model decisions, parent backward
  targets, reviewer gates, and terminal replay expectations.
- Added role-output authority coverage for terminal summary emission and
  explicit PM/reviewer/worker output routing through runtime-generated
  envelopes and receipts.

### Changed

- Upgraded the FlowPilot router so PM package-result disposition, route
  mutation, terminal summary generation, and model-driven next-action
  selection stay tied to current route/frontier evidence and registry-backed
  actions.
- Simplified the root-contract and child-skill-manifest default gates to the
  reviewer-only speed profile: PM-authored artifacts plus human-like reviewer
  approval now unblock those pre-route steps without mandatory Product or
  Process Officer detours.
- Strengthened PM, reviewer, officer, and worker runtime cards so role
  authority, output contracts, stale-evidence handling, and source/route
  version boundaries are explicit in formal packets and reviews.
- Refreshed route sign helpers, templates, packet ledgers, heartbeat/manual
  resume records, and review-release templates to match the current run-scoped
  control-plane model.

### Fixed

- Fixed resume priority so PM resume decisions can take precedence over stale
  control-blocker handling only after current-run state, frontier, packet, and
  role-memory evidence are loaded.
- Fixed gate-block reset handling so Product Officer block events preserve
  their freshly recorded blocked state, and aligned router runtime validation
  with the active-holder packet-result fast lane.
- Hardened PM result routing so worker and reviewer outputs cannot bypass PM
  disposition, output-contract catalog checks, or terminal authority gates.
- Expanded install and coverage checks to catch missing PM result-routing
  coverage and stale FlowGuard result evidence before release.

## 0.8.0 - 2026-05-12

### Added

- Added recursive route decomposition coverage, route replanning policy checks,
  event contract checks, event capability registry checks, model mesh checks,
  and the unified control transaction registry for route progression,
  packet dispatch, result absorption, reviewer gates, control blockers,
  route mutation, and unsupported historical reconciliation.
- Added direct Router paths for FlowPilot role outputs, startup fact reports,
  ACK/check-in handling, and FlowPilot output envelopes so the Controller stays
  on envelope relay rather than informal body interpretation.
- Added card/runtime coverage for active-holder packet fast lanes, handoff
  artifact protocol enforcement, role-output contract bindings, and
  reviewer/PM user-perspective checks.

### Changed

- Strengthened runtime cards, PM/reviewer/officer prompts, packet templates,
  and role-output contracts so route nodes, child-skill bindings, worker
  results, and control-plane blockers route through explicit registry-backed
  events.
- Updated FlowPilot route signs and display helpers to support committed-only
  route visibility, recursive decomposition, and route-placeholder contracts.
- Expanded installation, smoke, and coverage sweep checks to include the new
  control-plane, model-mesh, recursive-decomposition, and registry surfaces.

### Fixed

- Fixed route replanning so planning/root/parent entry gaps are handled as
  replanning or node expansion rather than being misclassified as repair work.
- Fixed gate-outcome blocker routing, ACK/check-in loops, packet active-holder
  progress, resume liveness, and stale or false-prerequisite control events.
- Hardened public release hygiene by keeping local `tmp/` validation output out
  of the tracked release boundary.

## 0.7.0 - 2026-05-10

### Added

- Added installer dependency bootstrap output so FlowPilot explains required,
  optional, and host-capability dependencies before reporting install status.
- Added public GitHub FlowGuard installation support behind
  `--install-flowguard`, with post-install import verification.
- Added `skills/flowpilot/DEPENDENCIES.md` and a short skill-level dependency
  bootstrap reminder so direct skill-directory installs still expose required
  dependencies.
- Extended the release-tooling FlowGuard model to catch missing dependency
  notices, unauthorized FlowGuard installs, optional companion auto-installs,
  and required-dependency readiness without FlowGuard verification.

### Changed

- Moved PM-authored material-scan and current-node work packet dispatch from
  reviewer pre-approval to router direct-dispatch preflight; reviewers now
  stay on worker-result, stage-gate, and PM-decision review.
- Replaced the external `grill-me` dependency wording with FlowPilot-owned self-interrogation gates.
- Updated the recommended install path to
  `python scripts\install_flowpilot.py --install-missing --install-flowguard`.
- Updated public release checks to validate GitHub-backed Python package
  dependencies such as FlowGuard.

## 0.6.1 - 2026-05-09

### Changed

- Required startup and resume background role-agent records to carry an
  explicit strongest-available model policy and highest-available reasoning
  effort policy instead of relying on foreground/controller model inheritance.
- Added router action payload guidance for startup live-role spawn, heartbeat
  resume rehydration, manual resume rehydration, and missing-role replacement
  so background role intelligence policy is visible in the control plane.
- Added a generic role-output runtime for formal PM decisions, reviewer
  reports, officer reports, and GateDecision bodies. It generates contract
  skeletons, validates mechanical fields, writes receipts and role-output
  ledger entries, and returns controller-visible envelopes without exposing
  body content.
- Added a compact role-output envelope shape using `body_ref` and
  `runtime_receipt_ref` so roles no longer hand-author derived path/hash and
  receipt metadata.
- Added a repository CLI wrapper, `scripts/flowpilot_runtime.py`, that provides
  one entry point for packet open/complete flows and formal role-output
  prepare/submit/verify flows.
- Added a data-only quality-pack catalog and generic `quality_pack_checks`
  runtime rows so route-declared quality obligations are recorded without
  making the report runtime judge UI, desktop, localization, or other
  pack-specific semantics.

### Fixed

- Hardened role open and resume normalization so missing or downgraded
  background role model/reasoning policy is rejected before PM startup or
  resume decisions can depend on that role record.
- Reduced friction from missing hand-written report fields by moving fixed
  fields, explicit empty arrays, hashes, and runtime receipt metadata into the
  role-output runtime while keeping semantic judgement with the owning role and
  downstream gates.
- Updated router, output-contract, and protocol-conformance checks to accept
  compact role-output envelopes while preserving unsupported historical with unsupported historical
  top-level role-output path/hash pairs.
- Changed the public release preflight to use the fast smoke path so the
  release gate reuses valid FlowGuard meta/capability proofs instead of
  exhausting memory on full graph exploration during publication.

## 0.6.0 - 2026-05-09

### Added

- Added unified packet runtime session entrypoints so packet recipients can
  open assigned sealed packet bodies, record minimal open receipts, submit
  result bodies, and receive runtime-generated result envelopes through one
  controlled path.
- Added result review session support so reviewers and PM-authorized result
  readers can record sealed-result open receipts without exposing result bodies
  to the Controller.
- Added regression coverage for runtime-generated packet/result receipts,
  result ledger absorption, protocol-contract conformance, repair transaction
  handling, and router recovery from mechanical metadata gaps.

### Changed

- Changed router classification so missing mechanical receipts and role-key
  agent-id metadata gaps can be reissued to the responsible role instead of
  escalating to PM repair by default.
- Updated worker, officer, reviewer, PM, and Controller cards so normal role
  work uses the runtime session path and returns controller-visible envelopes
  instead of hand-written packet/result metadata.
- Kept reviewer quality findings as PM decision-support unless they expose a
  hard blocker, preserving PM ownership of route choice, waiver, repair, and
  completion decisions.

### Fixed

- Prevented valid-looking worker results from being blocked solely because the
  prompt path failed to write runtime receipt metadata.
- Preserved sealed-body boundaries while reducing audit noise: the runtime now
  records minimal positive proof of authorized opens rather than persistent
  access-attempt histories or first-open counters.
- Hardened protocol and repair models so same-class packet reissue and repair
  transaction failures are covered before release.

## 0.5.5 - 2026-05-09

### Added

- Added FlowGuard planning-quality model coverage for planning profiles,
  Skill Standard Contracts, skill-standard route/work-packet projection, and
  reviewer hard-blindspot blocking.
- Added FlowGuard reviewer active-challenge model coverage for checklist-only
  review passes, generic challenge actions, missing evidence or waiver,
  hard-issue residual downgrades, unverified core commitments, and blockers
  without reroute requests.
- Added required reviewer `independent_challenge` report fields so reviewer
  pass decisions include scope restatement, explicit and implicit commitments,
  failure hypotheses, task-specific challenge actions, findings, pass/block
  status, reroute requests, and waivers.

### Changed

- Updated PM planning, child-skill manifest, node-acceptance, packet, and
  result templates so compiled skill standards are projected into routes,
  work packets, reviewer gates, artifacts, and result matrices.
- Updated reviewer cards so PM packets are treated as the review floor rather
  than the review boundary.
- Registered the planning-quality and reviewer active-challenge runners in
  install, smoke, output-contract, card-coverage, and coverage-sweep checks.

### Fixed

- Repaired FlowPilot runtime cross-plane drift from the post-0.5.4 local
  source so repository and installed-skill audits can converge after sync.
- Fixed the FlowGuard coverage sweep to recognize result files declared with
  `Path(__file__).resolve().with_name(...)`.

## 0.5.4 - 2026-05-08

### Added

- Added output-contract model coverage for the PM model-miss triage decision
  and FlowGuard officer model-miss report contracts.

### Changed

- Gated reviewer-block repair behind PM model-miss triage so
  FlowGuard-modelable bug classes require officer same-class findings, candidate repair
  comparison, and a minimal sufficient repair recommendation before normal
  repair starts.
- Kept PM as the repair owner while making non-modelable cases record an
  explicit FlowGuard incapability reason before using the ordinary repair path.

## 0.5.3 - 2026-05-08

### Added

- Added FlowGuard resume-model coverage for router wake recording, visible plan
  restoration, runtime-role liveness preflight, and timeout-unknown handling.

### Fixed

- Changed heartbeat and manual mid-run wakeups to always re-enter the router
  resume path instead of trusting an old `work_chain_status=alive` claim.
- Required resume role rehydration receipts to record host liveness status,
  liveness decision, bounded wait result, and an explicit
  timeout-not-treated-as-active receipt.
- Added PM resume, parent-segment, and terminal-closure output contracts,
  router-delivered payload contracts, and copyable JSON templates so PM
  decisions cite current route memory without repair retries.
- Allowed fatal protocol control blockers to absorb PM-recorded corrected
  follow-up replay while preserving the fatal lane requirement for explicit PM
  recovery.
- Aligned smoke validation with the model gate by skipping the current live-run
  audit for control-plane friction checks.

## 0.5.2 - 2026-05-08

### Added

- Added a FlowGuard route-display lifecycle model covering startup, route draft,
  activation, node transition, repair return, Cockpit, and chat fallback display
  paths.

### Fixed

- Updated FlowPilot route-sign generation to read real route nodes from
  `flow.json`, `flow.draft.json`, or `route_state_snapshot.json`, including
  `node_id`, `active_route_id`, and `active_node_id` aliases.
- Changed display-plan sync to keep `display_plan.json` as the host/native plan
  projection while using the canonical Mermaid route sign as chat fallback once
  real route data exists.

## 0.5.1 - 2026-05-07

### Added

- Added a focused packet lifecycle FlowGuard model for envelope/ledger hash
  identity, packet/result open receipts, result ledger absorption, agent-id
  authority, and PM control-blocker follow-up resolution.

### Fixed

- Hardened packet runtime and router gates so forged envelope-only open
  markers, missing packet-ledger receipts, result envelopes without ledger
  absorption, role-string `completed_by_agent_id` values, and PM repair
  decisions without corrected follow-up events cannot advance packet work.
- Required PM research absorption to reference a passed packet-group runtime
  audit instead of only the reviewer report file.

## 0.5.0 - 2026-05-07

### Added

- Added a first-class GateDecision contract, router event, mechanical
  validation path, run-state record, and gate-decision ledger for PM,
  reviewer, and FlowGuard officer gate decisions.
- Added final-ledger collection of accepted GateDecision records.
- Added FlowGuard and unit-test coverage for GateDecision prompt fields,
  router mechanical validation, output-contract propagation, and card
  instruction coverage.

### Changed

- Updated PM, reviewer, process officer, product officer, and PM output
  contract catalog cards to require file-backed GateDecision bodies while
  keeping semantic sufficiency with PM/reviewer/officers instead of the router.
- Expanded the output-contract model to include valid GateDecision propagation.

### Fixed

- Preserved and released the post-0.4.1 control-plane fixes already in this
  checkout, including startup repair-cycle handling, startup fact ownership,
  material dispatch friction handling, live card context delivery, user-visible
  route signs, and control-blocker repair decision handling.

## 0.4.1 - 2026-05-06

### Added

- Added a command-refinement model and release checks for FlowPilot command
  folding candidates.
- Added CLI parsing coverage for all active router subcommands and explicit
  absence checks for unsupported high-risk folding commands.

### Changed

- Restored the unfolded router baseline and kept only the narrow
  `run-until-wait` startup fold that advances through internal router loading
  before stopping at the startup questions boundary.
- Updated the FlowPilot launcher guidance and smoke checks to use the safe
  startup fold instead of broader command-bundling shortcuts.

### Fixed

- Added copyable display-confirmation payload templates to router actions that
  require user-dialog display evidence, reducing rejected startup/display
  payload retries.
- Removed incomplete high-risk command folds that could break startup before
  FlowPilot reached the three-question pre-banner gate.
- Prevented unsupported fold commands such as `deliver-card-bundle-checked`,
  `relay-checked`, `prepare-startup-fact-check`, and
  `record-role-output-checked` from remaining exposed as CLI commands.

## 0.4.0 - 2026-05-06

### Added

- Added router artifact validation for node acceptance plans, packet
  envelopes, result envelopes, and role-output envelopes so PM and worker roles
  can repair missing fields in one pass before returning artifacts.
- Added controller-visible skill-observation reminders on router control
  blockers and router errors, with expanded observation categories for schema,
  router-state, ledger, heartbeat, display-projection, and controller
  compensation gaps.
- Added proof-backed `--fast` reuse for the slow FlowGuard meta and capability
  checks. Proof reuse is valid only when the model file, runner file,
  FlowGuard schema version, and result file still match a successful proof.
- Added focused tests for proof freshness, artifact validation, envelope alias
  handling, reviewer result-card gating, and display-plan advancement.

### Changed

- Tightened current-node review flow so reviewer pass/block decisions require
  the worker-result review card after the worker result is relayed to the
  reviewer.
- Normalized safe packet/result envelope aliases in the packet runtime,
  including `packet_body_path`, `packet_body_hash`, `body_path`, `body_hash`,
  `to_role`, and `next_holder`.
- Updated display-plan projection so completed nodes stay completed when the
  frontier advances to the next active node.
- Updated smoke checks to support proof-backed fast mode without changing the
  default full validation path.

### Fixed

- Prevented duplicated local background result snapshots from being published
  by ignoring `simulations/*.background_latest.json`.

## 0.3.1 - 2026-05-06

### Fixed

- Allowed PM-owned material understanding, product architecture, and root
  acceptance contract events to accept file-backed role payload envelopes using
  memo, architecture, contract, manifest, route, draft, plan, package, or
  ledger paths.
- Preserved role-output envelope metadata when PM file-backed material,
  architecture, and contract artifacts are written into the run directory.
- Added router runtime coverage for file-backed PM material understanding
  payloads.

## 0.3.0 - 2026-05-06

### Added

- Added the prompt-isolated FlowPilot router runtime, route-sign/user-flow
  diagram helpers, explicit next-recipient modeling, and broader router
  regression coverage.
- Added the physical packet runtime, barrier bundle support, packet envelope
  templates, and role-origin/holder checks for controller relay boundaries.
- Added route process/product officer cards, route challenge review, stronger
  role cards, and updated route templates for packet-driven execution.

### Changed

- Changed the `flowpilot` dependency source from repository-copy semantics to
  the public GitHub skill source while keeping a local checkout sync mode for
  development and self-checks.
- Reworked README positioning around FlowGuard models, packet mail, role
  authority, and router rhythm as the current source package shape.
- Expanded public release diagnostics to cover dependency source URLs,
  repository-owned local sync freshness, and active protocol residue checks.

### Fixed

- Removed machine-specific local paths from release-facing tracked files so
  public release checks pass without leaking workstation paths.
- Tightened install tooling so GitHub-sourced repo-owned skills can still be
  refreshed from the active checkout during local development.

## 0.2.1 - 2026-05-04

### Added

- Added PM-owned research packages so material, mechanism, source, validation,
  reconciliation, and experiment gaps must be assigned, reviewed, and absorbed
  before they can support route or product decisions.
- Added controller packet-gate evidence, including the run-local
  `packet_ledger` template and packet-control FlowGuard checks.
- Added repository backup artifacts for the previous installed `flowpilot`
  skill so rollback remains possible without deleting the new version.

### Changed

- Hardened the controller authority boundary: the controller relays PM,
  reviewer, officer, and worker packets but may not execute worker packets or
  self-approve role gates.
- Tightened PM product-function quality gates, high-standard node rechecks, and
  UI iteration budget guidance.
- Updated heartbeat/manual resume so continuation loads the packet ledger,
  requires PM `controller_reminder`, requires reviewer dispatch policy before
  worker execution, and blocks ambiguous worker state for PM recovery.
- Updated local install sync checks to require the unsupported historical Cockpit prototype to
  be absent from the active tree before a clean UI restart.
- Updated install and local-sync audits to fail if unsupported external recovery
  scripts, prompts, or templates reappear in the active source tree.

### Removed

- Removed the previous native Cockpit prototype from the active source tree so
  the next Windows desktop UI can be rebuilt from scratch without reusing old
  UI assets or implementation code.
- Removed the unsupported external recovery scripts, Windows task helper, prompt,
  template, and obsolete findings page from the active source tree.

### Fixed

- Corrected README release/version language and the Chinese Cockpit section so
  both languages describe the current source package consistently.
- Removed post-`v0.2.0` changes from the `0.2.0` changelog section so the
  changelog matches the actual git tag boundary.
- Replaced the accumulated preflight findings page with the current effective
  FlowPilot continuation and startup boundaries so old recovery notes are not
  mistaken for live protocol.

## 0.2.0 - 2026-05-04

### Added

- Added the native Windows-oriented FlowPilot Cockpit package with a live route/task view, multi-task tabs, English/Chinese UI strings, settings, and support entry.
- Added `scripts/audit_local_install_sync.py` to verify repository-owned installed skills are source-fresh, installed skill names are not duplicated, and Cockpit source files are tracked before release.
- Added a `VERSION` file so release checks and documentation have a single current version marker.
- Added autonomous UI design rules for native desktop screenshot verification, concept/resource traceability, and real app icon realization checks.

### Changed

- Updated FlowPilot startup protocol from three questions to four by adding a display-surface choice: open Cockpit UI or continue with chat route signs.
- Updated the installer with `--sync-repo-owned` so repository-owned skills can be refreshed without pulling optional companion skills by default.
- Tightened release modeling so local install sync, duplicate installed skill names, and tracked Cockpit source are release gates.

### Fixed

- Made optional companion skill availability warning-only unless explicitly requested for installation.
- Removed stale release-version references and local absolute path leakage from release-facing documentation.

## 0.1.0 - 2026-05-02

Initial public source release.

### Added

- Published the `flowpilot` Codex skill.
- Added reusable `.flowpilot/` project-control templates.
- Added FlowGuard-backed simulations for process, capability, startup, and release-tooling checks.
- Added install, smoke, public-release, lifecycle, heartbeat, watchdog, busy-lease, and user-flow helper scripts.
- Added bilingual README positioning FlowPilot as FlowGuard-based finite-state project control.
- Added companion skill source metadata for FlowGuard, `model-first-function-flow`, and `frontend-design`.
- Added minimal example material under `examples/minimal/`.

### Release Notes

- This is a source release. No binary assets are included.
- FlowPilot requires the real `flowguard` Python package; it does not vendor FlowGuard.
- Companion skills are referenced by source URL, but FlowPilot release tooling does not publish companion skill repositories.
