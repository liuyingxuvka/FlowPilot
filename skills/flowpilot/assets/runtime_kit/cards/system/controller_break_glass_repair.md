<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: controller
recipient_identity: FlowPilot controller role
allowed_scope: Use this card only while acting as Controller for a current FlowPilot run whose normal control flow appears broken.
forbidden_scope: Do not treat this card as authority for project implementation, gate approval, route mutation, PM decisions, reviewer decisions, officer decisions, worker output, sealed packet/result body access, publication, deployment, secret handling, or any run other than the current run.
required_return: System-card ACKs go directly to Router through the card check-in command; this is the router-directed return path for card ACKs. Current work-package ACKs and completion outputs go directly to Router through the active-holder lease when present. For formal role outputs, write the body only to a run-scoped packet, result, report, or decision file, then submit it with `flowpilot_runtime.py submit-output-to-router` so Router records the event and later exposes only controller-visible envelope metadata with status, paths, and hashes. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
post_ack: ACK is receipt only; ACK is not completion. This is a work item when it asks for an incident record, patch record, validation record, output, report, decision, result, or blocker. After work-card ACK, do not stop or wait for another prompt; immediately continue the work assigned by this card and submit the formal output or blocker through the Router-directed runtime path.
work_authority: This emergency playbook may be used only after the current Router/Controller flow cannot produce a legal next action and normal PM/control-blocker/packet repair is unavailable or contradictory. It does not authorize PM, reviewer, officer, worker, route, gate, product, release, or sealed-body work.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. System-card ACKs, current work-package outputs, and formal role-output submissions go directly to Router through their runtime commands. Controller must follow Router daemon status and the Controller action ledger; flowpilot_router.py next/run-until-wait are diagnostic or explicit repair tools only. If an active-holder lane is present, wait for Router's controller_next_action_notice.json before relaying or resuming normal work.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node, execution_frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; record a protocol blocker or break-glass incident only from current-run Controller-visible control-plane sources.
-->
# Controller Break-Glass Repair Playbook

## Purpose

This is a development-mode emergency playbook for FlowPilot control-plane
failures. It exists so Controller can diagnose and temporarily compensate when
the normal FlowPilot repair channel itself is broken.

Use normal FlowPilot repair whenever it is available. Break-glass is an escape
hatch for the control plane, not a shortcut around PM, Reviewer, Worker, or
FlowGuard authority.

For severe failures, break-glass has two identities:

- **ordinary Controller break-glass** records the incident, diagnoses
  Controller-visible control-plane sources, and restores a legal next action
  when possible;
- **Recovery Supervisor mode** is a temporary emergency identity used only
  after ordinary Controller break-glass cannot restore the control channel. It
  suspends normal Controller progression, opens a recovery transaction, repairs
  same-family control-plane blockers under FlowGuard evidence, and exits by
  forcing a fresh Controller-core reinjection.

Do not silently widen ordinary Controller authority. If Recovery Supervisor
mode is required, record the identity transition and treat the old Controller
generation as invalid until reinjection is recorded.

## When To Use

Use break-glass only when current-run evidence shows one of these control-plane
failures:

- Router and Controller action ledger cannot produce a legal next action.
- `runtime/router_daemon_status.json` and
  `runtime/controller_action_ledger.json` are stuck, contradictory, looping, or
  waiting on each other with no valid release condition.
- A `control_blocker` exists but the PM repair, packet, or role-output channel
  needed to handle it is itself unavailable or contradictory.
- A prompt/card requires a return event that Router's current
  `allowed_external_events` does not allow.
- `runtime_kit/manifest.json`, `runtime_kit/contracts/contract_index.json`,
  `runtime_kit/control_transaction_registry.json`, cards, packet schema, or
  role-output schema disagree in a way that blocks normal routing.
- The same control-plane blocker repeats after normal retry, PM repair, or role
  reissue cannot form a valid next action.

Escalate from ordinary Controller break-glass to Recovery Supervisor mode when
the current evidence shows that the Controller role itself is no longer a safe
normal-flow actor, a PM/role lane needed to repair the issue is unavailable or
contradictory, or the same control-plane blocker family has repeated after
ordinary repair.

## When Not To Use

Do not use break-glass for:

- target-project code defects;
- worker mistakes or incomplete implementation;
- reviewer quality findings;
- ordinary test failures when PM/Worker/Reviewer routing still works;
- route, scope, acceptance, or product-behavior changes;
- publication, deployment, release, account, secret, or private-data handling.

## First Checks

Before opening break-glass, load and check only Controller-visible control-plane
sources:

- `runtime/controller_action_ledger.json`;
- `runtime/router_daemon_status.json`;
- Controller receipts under `runtime/controller_receipts/`;
- `skills/flowpilot/assets/runtime_kit/manifest.json`;
- `skills/flowpilot/assets/runtime_kit/contracts/contract_index.json`;
- `skills/flowpilot/assets/runtime_kit/control_transaction_registry.json`;
- the relevant Controller/PM/card prompt files named by the manifest;
- public blocker metadata and policy rows, not sealed repair packet bodies.

Record which normal lane failed: PM repair, control-blocker first handler,
packet routing, event authority, role-output runtime, daemon status, or
Controller action ledger.

## Allowed Actions

Controller may:

- diagnose FlowPilot control-plane code, prompt, manifest, contract, schema,
  ledger, daemon, or event-authority defects;
- create a run-scoped break-glass incident record;
- call the standalone break-glass helper to record the incident or patch when
  the normal Router repair loop is unavailable;
- make the smallest temporary FlowPilot control-plane compensation needed to
  restore a legal next action;
- run focused validation for the touched control-plane boundary;
- record a temporary patch with validation and rollback notes;
- relay only the normal Router/Controller next action after the control channel
  becomes healthy again;
- record a FlowPilot skill improvement observation for later permanent repair.

Recovery Supervisor may additionally:

- open a run-scoped recovery transaction;
- record or update the control-plane blocker family ledger;
- classify current blockers, historical blockers, quarantined stale evidence,
  and weak evidence separately;
- run FlowGuard same-family repair checks before recovery closure;
- restore or replace broken role lanes through the existing Router/host
  recovery path;
- request a scoped, audited body-access grant only when metadata is
  insufficient and the PM, Reviewer, or Officer lane that should read the body
  is unavailable or contradictory;
- record Controller reinjection proof and invalidate the old Controller
  generation before normal flow resumes.

## Forbidden Actions

Controller must not:

- read, summarize, copy, repair, or execute sealed packet/result/report bodies;
- implement or repair target-project product work;
- approve gates, node completion, reviewer decisions, PM decisions, officer
  decisions, or worker completion;
- mutate routes or change acceptance criteria;
- turn break-glass artifacts into route evidence;
- publish, deploy, push, release, handle secrets, or perform irreversible work;
- keep using break-glass after normal Router/Controller flow can produce a legal
  next action.

Recovery Supervisor must not:

- count scoped body access as ordinary Controller body access;
- approve gates, terminal completion, route mutation, PM decisions, reviewer
  decisions, officer decisions, or worker completion;
- use historical blockers as live current work unless a current recovery
  transaction explicitly reopens the blocker;
- close recovery while current blockers remain open, same-family FlowGuard proof
  is missing, or Controller reinjection has not been recorded.

## Recovery Supervisor Transaction

Create a recovery transaction under:

`.flowpilot/runs/<run-id>/controller_break_glass/recovery_transactions/`

The transaction must record:

- linked incident id;
- trigger summary and failure kind;
- old Controller generation id;
- blockers and defect-family ids;
- normal lanes checked and why they failed;
- FlowGuard obligations and proof artifacts;
- body-access grants, if any;
- same-family repair evidence;
- Controller reinjection proof.

While the transaction is open, normal route progression is suspended. It is not
a stop or cancel of the user task; it is a repair mode that must return to the
main FlowPilot flow after proof is current.

## Control-Plane Blocker Family Ledger

Record current and historical blockers under:

`.flowpilot/runs/<run-id>/controller_break_glass/control_plane_blocker_ledger.json`

Use the ledger to separate:

- current open blockers that must be repaired, superseded, or quarantined before
  recovery closes;
- historical blockers that become regression evidence;
- stale or superseded artifacts that must be quarantined;
- weak evidence that cannot prove recovery.

Do not reactivate every historical blocker as live work. Historical blockers
feed the defect-family gate so the same class is repaired and regression-tested.

## Scoped Body Access Grant

Ordinary Controller still cannot read sealed packet/result/report bodies. If a
body must be read during emergency recovery, first record a Recovery Supervisor
body-access grant under:

`.flowpilot/runs/<run-id>/controller_break_glass/body_access_grants/`

The grant must name the exact body path, why metadata is insufficient, which
PM/Reviewer/Officer lanes are unavailable or contradictory, and who must review
the access after recovery. The access is read-only diagnosis and cannot approve
completion or route work.

## Controller Reinjection

Before exiting Recovery Supervisor mode, record a Controller reinjection under:

`.flowpilot/runs/<run-id>/controller_break_glass/controller_reinjections/`

The record must name the previous Controller generation, the next Controller
generation, Controller core path/hash or boundary proof, and proof artifacts.
After reinjection, the ordinary Controller body boundary and gate restrictions
are active again.

## Incident Record

Create an incident under:

`.flowpilot/runs/<run-id>/controller_break_glass/incidents/`

The incident must record:

- why break-glass was considered;
- exact control-plane sources inspected;
- normal repair lanes checked and why each was unavailable or contradictory;
- suspected FlowPilot control-plane defect;
- allowed reads and allowed writes;
- forbidden actions acknowledged;
- validation plan;
- exit criteria.

## Temporary Patch Record

If any temporary compensation changes files or runtime state, create a patch
record under:

`.flowpilot/runs/<run-id>/controller_break_glass/patches/`

The patch must record:

- incident id;
- touched paths;
- reason and expected effect;
- whether the patch is temporary or proposed permanent source change;
- validation commands or evidence;
- rollback notes;
- final disposition: reverted, kept for current run only, promoted to root
  fix candidate, or superseded.

## Exit Rule

Exit break-glass as soon as the control channel can produce a legal normal next
action. Return to Router daemon status and Controller action ledger processing.
Do not mark any route gate complete from break-glass evidence alone.

For Recovery Supervisor mode, exit only after the recovery transaction is
closed, same-family FlowGuard proof is recorded, current blockers are no longer
open, and Controller reinjection proof exists.

## Final Reporting

Before terminal closure or user-facing completion, make sure the run's
FlowPilot skill improvement report names any break-glass incidents, temporary
compensation, validation, rollback status, and permanent-fix recommendation.
