## Context

Controller already has a strict relay boundary: it may display route signs,
relay router-authorized envelopes, and sync the host visible plan, but it must
not read sealed bodies or invent progress from chat. The current prompts and
router action metadata protect authority well, but they do not consistently
protect the user's reading experience from internal names such as packet ids,
ledger names, event names, hashes, action ids, and diagnostic paths.

The current status summary is written by Router and consumed by Controller or
future UI surfaces. It should remain machine-readable, but it also needs a
small progress-fact section that a chat surface or UI can show without turning
technical state into a long prose explanation.

## Goals / Non-Goals

**Goals:**

- Add one plain-language user-reporting rule to the Controller core card.
- Add one per-action plain-language reminder to Router-generated Controller
  actions.
- Add a compact `progress_summary` object to `current_status_summary.json`
  with route depth, per-level node counts and current indexes, total completed
  and total nodes, elapsed seconds, and coarse state.
- Preserve all existing machine-readable status fields and sealed-body
  exclusion rules.
- Validate that the new user-visible status path does not leak internal
  metadata and that progress facts remain compact.

**Non-Goals:**

- Do not add language detection or translation tables.
- Do not rewrite route sign Mermaid output.
- Do not change worker progress prompts.
- Do not expose sealed packet/result/report bodies through status.
- Do not change Controller authority, PM authority, route advancement, or
  completion rules.

## Decisions

- Put the strongest human-facing rule in the Controller core card because that
  is the long-lived role instruction the foreground Controller reads.
  Alternative considered: add the instruction to each role card. Rejected
  because this is a Controller communication duty, not a worker/reviewer duty.
- Add the repeated reminder in the common Router action construction path so
  every Controller action receives the same boundary without duplicating prompt
  text across individual action builders.
  Alternative considered: manually add text only to visible display actions.
  Rejected because Controller may mention waits, blockers, or actions outside
  the display-gate path.
- Keep status summary facts structured instead of generating a prose
  `plain_status` sentence. This avoids language lock-in and lets chat/UI
  surfaces decide how to render the facts.
- Reuse the active route/frontier information already loaded for
  `current_status_summary.json`. Do not inspect sealed body content, role
  reports, or chat history to compute progress facts.

## Risks / Trade-offs

- [Risk] The repeated action reminder could become another internal field shown
  to users. -> Mitigation: mark it as policy metadata and assert it is not part
  of `display_text`.
- [Risk] Progress facts could become stale against the frontier or route tree.
  -> Mitigation: build them from the same route/frontier inputs as the existing
  status summary and cover the freshness/leakage hazards in FlowGuard and unit
  tests.
- [Risk] Route trees may have uneven depth. -> Mitigation: summarize the active
  path only; `level_count` is the active path depth and each level carries its
  own sibling count and completed sibling count.
- [Risk] Runtime elapsed time may be unavailable for old runs. -> Mitigation:
  expose `elapsed_seconds: null` when no valid start timestamp can be derived.
