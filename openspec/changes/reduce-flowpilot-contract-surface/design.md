## Context

FlowPilot has a current-contract runtime with PM, FlowGuard operator, Reviewer,
Runtime, repair, parent replay, and terminal replay responsibilities. The
successful WorldGuard run `run-20260613-140526` demonstrates that the mainline
packet order can work when each role does one clear job:

`PM packet -> Runtime mechanical validation -> FlowGuard model/report ->
Reviewer quality review -> PM absorption/repair/disposition -> next packet`.

Later hardening correctly added acceptance items, final replay, stricter
review, repair evidence, installed self-check receipts, and stage/evidence
matrix rows. The failure is not those capabilities themselves. The failure is
that some of their fields and blocker language became global. Early packets can
now be judged as if they were terminal closure packets, and PM can be asked to
pre-fill FlowGuard's own model/test fields.

The design therefore uses the historical run as the process baseline, not as a
field baseline. Field contracts are reduced more aggressively than the
historical run when a field is not necessary for the current stage.

## Goals / Non-Goals

**Goals:**

- Keep one explicit current path for every packet family.
- Apply exactly three dispositions to contract fields: keep, move, or delete.
- Make the stage/evidence matrix the authoritative lifecycle map for all
  packet families, including allowed blocker classes and fixed next actions.
- Keep Runtime mechanical: schema, ids, packet/result scope, currentness, field
  shape, blocker enum membership, and fixed next-action mapping only.
- Keep FlowGuard modeling: model evidence is owned by FlowGuard and stored in a
  packet-owned run-local evidence file, not spread across the result body.
- Keep Reviewer blocking authority for current-stage quality and evidence
  failures.
- Keep PM absorption and repair decisions as the single semantic routing point
  after FlowGuard/Reviewer reports.
- Keep necessary newer capabilities: acceptance items, parent/child route
  ownership, node acceptance planning, parent replay, terminal replay, and
  portable installed self-check receipts.
- Remove fallback, compatibility, and old-evidence surfaces from current
  contracts and cover each removal with negative tests.

**Non-Goals:**

- Do not weaken terminal direct-evidence closure.
- Do not remove Reviewer blocking authority.
- Do not remove FlowGuard model evidence.
- Do not add optional fields, advisory fields, alternate paths, legacy aliases,
  or dual result shapes.
- Do not require arbitrary target projects to contain FlowPilot development
  repository scripts.
- Do not rewrite unrelated router architecture or revert peer-agent work.

## Decisions

### Decision 1: The stage matrix owns lifecycle contracts

`packet_stage_evidence_matrix.py` will define one row per packet/result family
with:

- `current_required_fields`
- `moved_fields`
- `deleted_fields`
- `allowed_blocker_classes`
- `blocker_class_to_next_action`
- `required_evidence_owner`

The old phrasing `not_required_until_stage` is replaced or supplemented by
explicit `moved_fields` and `deleted_fields`. This avoids a soft "optional"
reading. If a field is listed in `moved_fields`, it is not part of the current
packet contract. If it is listed in `deleted_fields`, it is not part of the
current contract at all.

Alternative considered: keep the existing matrix as explanatory metadata and
add role-card warnings. Rejected because it leaves prompt conflicts in place.

### Decision 2: Runtime validates blocker shape, not blocker truth

Runtime will not judge whether a Reviewer or FlowGuard blocker is semantically
right. Runtime only checks:

- the `blocker_class` is one of the current family row's allowed classes;
- the `next_action` matches the fixed action mapped from that class;
- the target packet/result/node ids are current;
- the required fields for the blocker object exist and have the right type.

Quality, model truth, evidence sufficiency, and severity remain role/PM
responsibilities.

Alternative considered: let Runtime reject "wrong-stage" blocker reasons by
semantic text. Rejected because that would make Runtime a semantic reviewer.

### Decision 3: FlowGuard model detail leaves the result body

FlowGuard result bodies retain only the PM-facing decision surface:

`pm_visible_summary`, `reviewed_by_role`, `passed`, `modeled_boundary`,
`blockers`, `pm_suggestion_items`, and `contract_self_check`.

Detailed model commands, invariants, test gaps, ordinary evidence, skipped
checks, and consistency rows move to the single packet-owned evidence file:

`.flowpilot/runs/<run-id>/evidence/flowguard/<packet-id>/flowguard_evidence.json`

FlowGuard must self-repair small model/test coverage gaps in that evidence
surface when it can do so inside its own role authority. PM receives the
summary, blockers, and fixed next actions.

Alternative considered: keep the current broad result body with stage-specific
empty arrays. Rejected because "empty but allowed" fields are still a
maintenance surface.

### Decision 4: Reviewer result bodies remain compact but blocking

Reviewer result bodies retain:

`pm_visible_summary`, `reviewed_by_role`, `passed`, `findings`, `blockers`,
`pm_suggestion_items`, and `contract_self_check`.

Reviewer can block current-stage quality or evidence failures by selecting a
fixed blocker class. Reviewer does not repeat Runtime mechanical checks or
FlowGuard model details.

Alternative considered: keep `independent_challenge` as a structured contract
inside every review. Rejected because the field made every review carry a
large diagnostic sub-protocol. Reviewer prompts can still require strong
thinking, but the result contract stays compact.

### Decision 5: PM repair and disposition use one table/one route

PM repair has the minimal common shape:

`decision`, `reason`, `target_blocker_id`, `next_action`.

Branch-specific payloads are only valid for the matching branch:

- `redesign_route` stages a route replacement plan before fresh repair work;
- `repair_parent_scope` stages a parent-scope replacement with active repair
  child specs before fresh repair work;
- terminal supplemental repair uses `supplemental_repair_contract` on the
  chosen continuing repair branch;
- `waive_with_authority` requires authority evidence.

Node PM disposition replaces four acceptance-item id arrays with one
`acceptance_item_disposition[]` table containing `acceptance_item_id`,
`decision`, `reason`, and `evidence_refs`.

Every blocker class also owns one handling route and one repair packet
contract. For substantive PM-owned blockers, that route is the current
`pm_repair_decision` packet; the blocker class does not preselect PM's repair
branch. The repair contract names the required current source files or ids, the
required opened-body receipts, the common repair payload fields, the owner role,
and the return gate after PM's selected branch is checked. A repeated repair for
the same repair lineage must carry the prior repair packet materials forward,
including the original blocker, prior repair packet id, prior blocking report,
the previous repair attempt's evidence, the reason it did not close, and the
new evidence or decision that changes the next attempt.

Alternative considered: keep four arrays because they are easy to validate.
Rejected because parallel arrays hide mismatches and force PM to maintain
several surfaces for one semantic table.

### Decision 6: Parent/child and terminal strictness are kept, but staged

Route planning owns parent/child structure and acceptance-item assignment.
Node acceptance planning owns node goal, acceptance projection, evidence
projection, risk projection, and handoff notes. Node execution owns current
evidence. Parent replay owns composition. Terminal replay owns final closure.

Final closure remains strict. The contraction only moves final evidence out of
earlier stages where it does not belong.

## Risks / Trade-offs

- Contract changes may invalidate existing tests and fake-AI fixtures.
  → Update fixtures through the new packet family tables and add negative
  tests for removed fields.
- Other agents may be editing adjacent runtime/prompt files.
  → Keep edits scoped, inspect diffs before patching, and do not revert
  unrelated modifications.
- Removing broad FlowGuard result fields could hide model details from PM.
  → Preserve PM-facing summaries and blockers in the result body; write model
  details to the single packet-owned evidence file.
- Compact Reviewer result bodies could reduce review rigor if prompts are not
  updated.
  → Update Reviewer role and child cards to require current-stage challenge
  work before choosing a fixed blocker class.
- Historical successful run replay may not match new compact fields exactly.
  → Use it as process-route evidence, not exact field-shape evidence; tests
  should prove the mainline is not blocked by moved/deleted future fields.
