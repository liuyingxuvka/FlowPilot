## Why

Recent strict FlowPilot runs exposed a remaining information-flow gap: runtime
can enforce the current packet contract, but a role can still receive only the
base required fields while a selected branch requires a stricter nested shape.
That makes live agents learn by repeated mechanical reissue even though the
single current path is correct and should be executable from the packet itself.

## What Changes

- Tighten current handoff contracts so every packet family exposes the fields,
  branch-specific child shapes, authorized input reads, downstream consumer, and
  missing-information exit needed to complete the current packet without hidden
  runtime knowledge.
- Add branch-valid-shape metadata for conditional outputs such as
  `redesign_route.route_plan`, including strict route-plan node fields.
- Make mechanical reissue packets carry the failed branch, exact correction
  contract, and branch-specific minimal valid shape instead of only a generic
  family shape.
- Collapse normal role dispatch into one public current-runtime path while
  preserving runtime-owned checks for packet responsibility, role reuse,
  replacement, liveness failure, and self-review prevention.
- Fix staged-gate status projection so accepted source packets for pending PM
  gates are not reported as current-target violations while their FlowGuard,
  reviewer, or system-validation gate is active.
- Extend FlowGuard field, information-flow, model-test alignment, and fake-AI
  rehearsal evidence so similar packet-contract drift is caught before live
  agents encounter it.
- **BREAKING**: old role-dispatch prompt wording that teaches
  `resolve-role-assignment` followed by `lease-agent` as the normal public work
  path is replaced by a single current role dispatch action. Diagnostic or
  internal runtime mechanics may remain, but public wrappers and role command
  helpers must not expose a second current workflow.
- **BREAKING**: packet success evidence that depends on undeclared branch
  fields, hidden fake-AI fields, old wrappers, legacy aliases, or status
  projection from historical accepted packets is invalid current evidence.

## Capabilities

### New Capabilities

- `flowpilot-current-information-flow`: Covers current packet handoff
  sufficiency, branch-specific output contracts, mechanical reissue correction,
  single visible role dispatch, staged-gate status projection, and fake-AI
  rehearsal parity for the new-only FlowPilot runtime.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: Runtime kit prompts and role cards must
  describe the single current handoff contract and single visible dispatch path.
- `flowguard-boundary-test-alignment`: Model-test alignment must include
  branch-specific contract sufficiency and staged-gate projection evidence.
- `synthetic-agent-trace-replay`: Fake AI rehearsals must exercise
  contract-blind success, branch-shape failures, corrected reissues, and role
  dispatch reuse/replacement without hidden-field success.
- `current-work-owner`: Current role ownership must be dispatched through one
  runtime-owned public action rather than a user-visible resolve/commit pair.

## Impact

- Runtime contract code under
  `skills/flowpilot/assets/flowpilot_core_runtime/`.
- Public `flowpilot_new.py` CLI wrappers and role command helpers.
- Runtime kit role cards and packet identity/action-ledger prompts.
- FlowGuard models and runners under `simulations/`, especially field
  contract, field mesh, project-control information flow, information-flow
  alignment, model-test alignment, and fake rehearsal runners.
- Unit, integration, fake-AI, install, topology, and local install sync checks.
