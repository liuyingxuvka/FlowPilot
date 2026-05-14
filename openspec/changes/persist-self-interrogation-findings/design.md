## Context

FlowPilot already performs several grill-me/self-interrogation passes:

- startup self-interrogation before product architecture;
- PM ratification of startup self-interrogation;
- reviewer challenge reports;
- officer modelability reports;
- focused node and completion self-interrogation.

The current protocol makes those steps visible, but it does not give every
meaningful finding a durable run-scoped destination. A finding can be mentioned
in prose, ratified in the moment, and then disappear from later gates unless a
role manually copies it into another artifact.

## Goal

Make self-interrogation findings persist as first-class evidence and force PM
to explicitly decide what each meaningful finding does to the rest of the run.

This is intentionally mechanical:

- Router checks existence, ownership, schema shape, and unresolved status.
- PM owns interpretation, prioritization, rejection, waiver, or downstream
  binding.
- Reviewers, workers, and officers surface findings as structured PM suggestion
  candidates rather than silently changing route authority.

## Non-Goals

- Do not make Router judge whether a grill-me answer is insightful.
- Do not add a second reviewer framework beside the existing reviewer/officer
  gates.
- Do not require every minor thought to become a blocker.
- Do not relax the existing PM suggestion ledger or final ledger gates.

## Design

Add a `flowpilot.self_interrogation_record.v1` artifact contract. Each record is
run-scoped and names:

- `scope`: startup, product_architecture, node_entry, repair, completion, or
  role_result;
- `owner_role`: the role that performed the self-interrogation;
- `source_event` and `source_artifact_path`;
- `findings`: stable ids, severity, category, summary, downstream obligation,
  and PM disposition;
- `unresolved_hard_finding_count`;
- `pm_disposition_summary`;
- `downstream_artifact_paths` and `pm_suggestion_ledger_ids`.

PM-owned records are required at protected PM gates. Non-PM roles do not gain
route authority; they emit hard blockers or useful nonblocking discoveries as
`flowpilot.pm_suggestion_item.v1` candidates and cite their self-interrogation
source.

Add a run index, `self_interrogation_index.json`, under the route/run evidence
area. The index gives Router a stable way to verify that protected gates saw
the relevant records without scanning arbitrary prose.

## Protected Gates

The minimum protected gates are:

- root acceptance contract freeze;
- current-node packet dispatch / packet registration;
- final route-wide ledger;
- terminal closure.

At those gates, Router rejects progress when the relevant index entries are
missing, malformed, stale for the current route/node, or contain unresolved hard
findings.

## Data Flow

1. A role performs self-interrogation.
2. The role writes or cites a self-interrogation record.
3. PM dispositions meaningful findings into one of:
   - incorporated into the current protected artifact;
   - bound to a named later node/gate;
   - entered into the PM suggestion ledger;
   - rejected with a reason;
   - waived with owner, reason, and residual risk.
4. Router checks only that hard/current findings are no longer unresolved before
   protected gates advance.
5. Final ledger cites the self-interrogation index and proves zero unresolved
   hard/current findings.

## FlowGuard Model

The FlowGuard model should fail routes where:

- startup/product architecture self-interrogation happens but no durable record
  is written before root contract freeze;
- a node starts without a current node-entry self-interrogation record or with
  unresolved hard findings;
- final ledger or terminal closure occurs while self-interrogation findings are
  unresolved or uncited.

The model should treat the record as a living artifact:

`Input x State -> Set(Output x State)` changes route state by writing records,
PM-dispositioning findings, and proving clean index state before protected
outputs.

## Rollout

Keep the first implementation narrow and compatible with existing artifacts:

- add template/contract fields rather than replacing existing ledgers;
- update PM/reviewer/officer/worker cards to point findings into the record or
  suggestion ledger;
- add Router helper validation for the new record/index;
- wire the helper into existing gate functions;
- add focused tests and model checks;
- sync the installed local `flowpilot` skill only after tests pass.
