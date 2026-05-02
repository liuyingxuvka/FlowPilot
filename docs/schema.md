# `.flowpilot/` Schema Notes

## Canonical Files

Machine-readable files are the source of truth:

- `state.json`
- `execution_frontier.json`
- `mode.json`
- `crew_ledger.json`
- `crew_memory/*.json`
- `product_function_architecture.json`
- `final_route_wide_gate_ledger.json`
- `contract.md`
- `capabilities.json`
- `routes/*/flow.json`
- `routes/*/nodes/*/node.json`
- `heartbeats/*.json`
- `watchdog/latest.json`
- `watchdog/events/*.json`
- `watchdog/events.jsonl`
- `lifecycle/latest.json`
- `lifecycle/events.jsonl`
- user-level `$CODEX_HOME/flowpilot/watchdog/registry.json`
- user-level `$CODEX_HOME/flowpilot/watchdog/projects/*/latest.json`
- user-level `$CODEX_HOME/flowpilot/watchdog/supervisor/latest.json`
- `checkpoints/*.json`
- `experiments/*/experiment.json`

Markdown files are English summaries for review.

## State

`state.json` records the current pointer:

- active route;
- active node;
- active route version;
- execution frontier path and version;
- visible Codex plan projection version;
- run mode;
- product-function architecture path;
- final route-wide gate ledger path;
- status;
- last heartbeat;
- last checkpoint;
- next node;
- next action.

It should not store the whole history.

## Crew Ledger

`crew_ledger.json` records the persistent six-agent crew for a formal
FlowPilot route:

- project manager;
- human-like reviewer;
- process FlowGuard officer;
- product FlowGuard officer;
- worker A;
- worker B.

For each role, the ledger records the role name, agent id when available,
status, authority boundary, latest report path, role memory path, memory
freshness, recovery or replacement rule, and terminal archive state. It is
loaded before formal route work and before heartbeat recovery.

Role memory packets under `crew_memory/*.json` are the durable continuity
state for the crew. Each packet records:

- role and nickname;
- agent id when available;
- authority boundary and forbidden approvals;
- compact role charter summary;
- frozen contract and current route position;
- latest report path;
- latest decisions, open obligations, open questions, blockers, and
  do-not-redo notes;
- relevant evidence paths;
- latest rehydration result;
- update timestamp.

Live subagent context is not the source of truth. Heartbeat or manual resume
may try to resume a stored agent id, but must replace unavailable roles from
the latest role memory packet. Raw transcripts are optional evidence only; a
compact structured memory packet is required before a replacement role can
approve gates. Heartbeat recovery loads the ledger and memory packets, records
which roles were resumed or replaced, and only then asks the project manager
for a completion-oriented runway from the current route position to project
completion.

## Product Function Architecture

`product_function_architecture.json` is the PM-owned pre-contract product
design package. It is written after startup self-interrogation and six-agent
crew recovery, and before acceptance contract freeze, route generation,
capability routing, or implementation.

It records:

- source inputs from startup self-interrogation and known product context;
- user-task map;
- product capability map;
- feature decisions marked `must`, `should`, `optional`, or `reject`;
- display rationale for every visible label, control, status, card, alert,
  empty state, and persistent text;
- missing high-value feature review;
- negative scope and rejected displays;
- functional acceptance matrix with inputs, outputs, states, permissions,
  failure cases, checks, and evidence paths;
- project-manager synthesis evidence;
- product FlowGuard officer modelability approval or block;
- human-like reviewer usefulness challenge result.

The acceptance contract freezes from this artifact. Later product-function
models check and refine coverage, but they do not substitute for the
pre-contract PM architecture gate.

## Execution Frontier

`execution_frontier.json` is the source of truth for the next jump and current
mainline plan projection. Heartbeat automations load it instead of embedding
route-specific next steps in the automation prompt.

The frontier records:

- schema version;
- active route and route version;
- frontier version, which must match the active route version before work;
- active node;
- current subnode or current gate when the active node is unfinished;
- current mainline node list;
- next node and fallback node;
- current chunk and next chunk;
- user flow diagram metadata: enabled display mode, render policy, highlighted
  current stage, source route/frontier paths, generated Mermaid path, rendered
  route/frontier versions, and staleness after route mutation;
- debug FlowGuard Mermaid metadata, which defaults to disabled and on-request
  only;
- host continuation decision: automated, manual-resume, blocked, or unknown;
- latest PM completion runway, including current gate, downstream steps,
  hard-stop conditions, checkpoint cadence, plan replacement status, and any
  PM stop signal;
- PM-owned child-skill gate manifest status: route-design discovery,
  loaded child-skill files, initial manifest path, current-node refined
  manifest path, required approver assignments, reviewer/officer/PM approval
  evidence, and whether all current child-skill gates have assigned-role
  approval;
- PM-owned final route-wide gate ledger status: ledger path, built route
  version, current-route scan, effective-node resolution, child-skill gate
  collection, human-review gate collection, product/process model gate
  collection, stale-evidence check, superseded-node explanation, unresolved
  count, reviewer backward check path, PM ledger approval path, and whether
  completion is allowed;
- whether the current node is unfinished;
- the concrete `current_subnode` or `next_gate` that the next continuation turn must
  execute while the node is unfinished;
- current-node completion status, required evidence, evidence paths, and
  `advance_allowed`;
- checks required before the next jump;
- visible Codex plan projection for the current mainline;
- crew ledger path, role memory root, rehydration status, restored/replaced
  role lists, and latest project-manager decision, including the PM repair
  strategy interrogation evidence path when a review failure mutates the route;
- route mutation status;
- stable heartbeat launcher metadata when automated continuation is supported;
- paired watchdog lifecycle metadata when automated continuation is supported,
  or manual-resume no-automation evidence when unsupported;
- controlled-stop and completion notice metadata: whether the current route is
  complete, whether a resume notice must be shown on controlled nonterminal
  stop, whether heartbeat wakeup can be waited for, and the exact manual resume
  prompt;
- update timestamp.

If the route structure changes, FlowPilot writes a new route version, reruns
FlowGuard checks, rewrites the execution frontier, and syncs the visible Codex
plan from the latest PM completion runway. When the host has a native visible
plan/task-list tool, such as Codex `update_plan`, the sync must call that tool
and record the method, timestamp, route version, PM runway id, item count, and
completion-tail coverage. It does not rewrite the heartbeat automation prompt
unless the host continuation itself needs repair.

`next_node` is not executable while `unfinished_current_node` is true or
`current_node_completion.advance_allowed` is false. In that state, the next
continuation turn, whether automated heartbeat or manual resume, resumes
`active_node`, obtains a PM completion runway, replaces the visible plan
projection from that runway, selects the persisted `current_subnode` or
`next_gate`, and must execute at least that gate when it is executable before
continuing along the runway. A continuation record that only says "continue to
next gate" without an executed gate or blocker is invalid no-progress evidence.

On any controlled stop before terminal completion, the frontier or heartbeat
record stores a `controlled_stop_notice` packet. Automated mode may set
`can_wait_for_heartbeat` true and include both heartbeat and manual resume
instructions. `manual-resume` mode sets `can_wait_for_heartbeat` false and
instructs the user to type `continue FlowPilot`. Terminal completion stores a
completion notice instead of a resume prompt.

The execution frontier stores the native plan sync status separately from the
PM runway evidence. `synced_to_visible_plan` requires either native plan tool
evidence when available or an explicit no-native-tool fallback. It also records
whether the projection includes downstream runway depth; a current-gate-only
projection is invalid for formal continuation.

Child-skill gate manifests live in the frontier because they determine the
next legal gate. The initial manifest is PM-owned route-design evidence; the
current-node manifest is a contextual refinement. Each gate record names its
source skill, source step, gate type, evidence required, `draft_owner`,
`execution_owner`, `required_approver`, `forbidden_approvers`,
`approval_status`, and `approval_evidence_path`. Parent resume is invalid
until every current child-skill gate is approved by its assigned role or
blocked/waived with evidence from the responsible role.

## Final Route-Wide Gate Ledger

`final_route_wide_gate_ledger.json` is the PM-owned terminal closeout ledger.
It is rebuilt from current `.flowpilot/` state before final completion, after
route mutations, repairs, standard raises, and child-skill loop closures have
settled. It is not a static checklist copied from the initial route.

The ledger records:

- active route id and route version;
- source paths used to build the ledger;
- current-route scan and effective-node resolution status;
- child-skill, human-review, product-model, process-model, verification,
  lifecycle, and completion gate entries;
- generated-resource lineage for concept images, visual assets, screenshots,
  route diagrams, model reports, and other generated artifacts;
- required approver, approval status, evidence paths, waiver reasons, blocked
  reasons, superseded-by links, and unresolved reasons for each entry;
- stale evidence count, generated-resource count, unresolved-resource count,
  and unresolved count;
- human-like reviewer backward-check evidence path;
- PM ledger approval evidence path;
- `completion_allowed`.

Terminal completion requires `unresolved_count` to be zero, reviewer backward
check to pass, and PM ledger approval to be recorded. If route mutation occurs
after the ledger is built, the ledger is stale and must be rebuilt.

## Inspection Evidence

Human-like inspection evidence includes a neutral observation before the
pass/fail decision. The observation records what the artifact, screenshot,
output, or exercised feature actually appears to be, including visible content,
window or desktop artifacts, responses to operations, and any required behavior
that was not observable.

For generated UI concept targets, the observation also records whether the
candidate appears to be an independent concept, an existing screenshot, an
existing-image variant, a desktop/window capture, old route UI evidence, or
prior failed evidence with cosmetic changes. The later authenticity decision
must cite this observation.

## Watchdog

`watchdog/latest.json` records the latest external stale-heartbeat check. Event
records under `watchdog/events/` and `watchdog/events.jsonl` preserve notable
stale checks and official automation reset results.

The watchdog schema records:

- checked time;
- stale threshold;
- active route, node, and last heartbeat;
- lifecycle pairing: heartbeat automation id, watchdog automation id or task
  name, watchdog automation kind, whether it was created with the heartbeat,
  active state, hidden/noninteractive execution state, visible window risk,
  stopped-before-heartbeat state, terminal frontier writeback state, and the
  required terminal shutdown order;
- heartbeat timestamp, source, and age;
- host automation metadata when available;
- whether the official Codex app reset was required, attempted, accepted, or
  failed;
- the decision, such as `healthy`, `stale_official_reset_required`,
  `stale_official_reset_invoked`, `stale_official_reset_failed`,
  `inactive_terminal_route`, or `config_error`.

`stale_official_reset_invoked` is not a successful recovery by itself. It means
the watchdog detected the gap and FlowPilot invoked the official automation
reset. The proof is a later heartbeat with a newer timestamp.

The local watchdog record also contains `global_record`, unless global
recording is explicitly disabled for a test. Global records are stored under
`$FLOWPILOT_GLOBAL_RECORD_DIR` when set, otherwise under
`$CODEX_HOME/flowpilot/watchdog`. The global schema contains:

- `registry.json`: project key, project root, latest local watchdog path,
  latest global watchdog path, route/node, last decision, heartbeat automation
  id, manual-stop flag, and registration-active flag;
- `projects/<project-key>/latest.json`: compact copy of the latest local
  watchdog decision and project metadata;
- `events/events.jsonl` and event JSON files: notable global watchdog poll
  events;
- `supervisor/latest.json`: singleton supervisor processing result, reset
  requirements, and local writeback status.

The global registry is an index, not the authority. Before recording or
performing a reset requirement, the singleton Codex global automation must
reread project-local `.flowpilot/state.json` and
`.flowpilot/watchdog/latest.json`. Repository scripts may scan and summarize
the records, but the official reset-capable supervisor must run inside Codex so
it can use the Codex app automation interface.

For routes with real continuation, terminal closure must update lifecycle
evidence so the watchdog is stopped or deleted before the heartbeat automation
is stopped, and so the inactive lifecycle snapshot is written back to
`state.json`, `.flowpilot/execution_frontier.json`, and watchdog evidence.

## Lifecycle

`lifecycle/latest.json` is the unified inventory snapshot for pause, restart,
and terminal cleanup. It records the status seen across:

- Codex app automation records for FlowPilot heartbeat and global supervisor
  automations;
- user-level global watchdog registry and supervisor records;
- Windows scheduled tasks whose names or actions identify FlowPilot;
- `.flowpilot/state.json`;
- `.flowpilot/execution_frontier.json`;
- `.flowpilot/watchdog/latest.json`.

Lifecycle closure is valid only when the snapshot records either no required
actions or explicit waived actions with reasons. Disabled Windows scheduled
tasks still count as residual lifecycle objects until unregistered or waived.
For restart, stale disabled tasks must be unregistered/recreated or explicitly
adopted into the current route before the route is considered protected.

The lifecycle helper does not call Codex automation APIs. It records required
actions so the controller can use the official Codex app automation interface.

## Route

`flow.json` records:

- route id;
- status;
- superseded route if any;
- nodes;
- allowed transitions;
- required gates;
- rollback targets;
- invariants.

## Capability Evidence

Capability evidence should name:

- capability id;
- source skill;
- reason it was invoked;
- inputs;
- outputs;
- verification status;
- dependent route nodes.
