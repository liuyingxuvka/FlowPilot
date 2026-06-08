## Design

### Existing Path To Reuse

The implementation reuses the current packet/result path. A role receives one
current packet, opens authorized materials, submits a result through
`flowpilot_new.py submit-result`, and runtime validates the current packet
family before downstream routing.

The existing role output contracts remain the semantic source for Reviewer and
FlowGuard operator report shape. The packet-result family table becomes the
mechanical bridge that tells `submit-result`, fake AI, handoff contracts, and
reissue packets which role-report fields must exist.

### Contract Chain To Tighten

This change does not add another workflow. It tightens the current chain:

1. `high_standard_contract` freezes the root completion floor, including hard
   user intent, forbidden scope, evidence rules, and report-only boundaries.
2. The strict route plan binds nodes to hard requirement ids, required outputs,
   and current `deliverable_checks`.
3. The PM node acceptance plan returns a `node_context_package` that projects
   inherited hard requirements, low-quality-success risks, semantic downgrade
   risks, proof obligations, and role-specific packet obligations.
4. Worker, FlowGuard operator, Reviewer, and PM disposition packet results
   submit current rich report fields through the existing packet/result path.
5. Final route-wide ledger and final requirement evidence matrix close hard
   requirements from current evidence and explicit waivers, not accepted-node
   existence alone.
6. Terminal backward replay confirms the delivered result still satisfies the
   frozen user intent before broad completion can be claimed.

### Runtime Ownership

Runtime checks only mechanical facts:

- result body is strict JSON;
- required field paths are present and non-empty where required;
- explicit array fields are arrays;
- forbidden old top-level fields are absent;
- declared route deliverable check kinds have the fields needed to evaluate
  them inside the current project root;
- final ledgers have the current required semantic rows before closure;
- `pm_visible_summary` is non-empty when required;
- current packet family metadata is included in blockers and reissues.

Runtime does not decide whether the independent challenge is wise or whether a
FlowGuard model is substantively sufficient.

Runtime also does not decide product excellence. It only makes it impossible to
claim closure while the declared current evidence chain is missing, stale,
forbidden, or unabsorbed.

### Semantic Ownership

Reviewer remains responsible for human-like quality, evidence credibility,
final-user fit, hard-part proof, and PM-actionable blocking or suggestions.
FlowGuard operator remains responsible for model boundary, command evidence,
counterexamples, skipped checks, missing test kinds, confidence boundary, and
residual blindspots.

PM remains responsible for absorbing current role evidence. A PM disposition is
not merely a pass flag; it is the commit point that names which hard
requirements are now covered, which Reviewer/FlowGuard findings were absorbed,
what risks remain, and why no semantic downgrade or forbidden output remains.

### Current-Only Contract

Reviewer and FlowGuard packet families do not accept generic minimal bodies as
success. The current result body must carry the role report fields named by the
current contract. Old wrappers, aliases, fallback evidence, and generic
minimal bodies are mechanical failures or model/test negative evidence.

Hard user-intent and route-deliverable checks are also current-only. Old root
contracts, old UI evidence, stale reports, historical run artifacts, and
report-only completion claims remain evidence only when a current node or final
closure row explicitly admits and validates them.
