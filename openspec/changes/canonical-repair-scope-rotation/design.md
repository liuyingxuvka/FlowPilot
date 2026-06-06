## Context

FlowPilot is a current-contract runtime. Repository rules forbid adding
compatibility shims, legacy aliases, prose guessing, missing-field defaults, or
dual-authority paths unless a named migration is approved. The June 3 ledger
showed 27 same-node repair transactions without `fresh_packet_id`, all around
one route node; the first-node repair had succeeded only when a fresh packet
was actually produced.

The existing runtime already has most primitives needed for a minimal repair:
route nodes, parent/child route metadata, route versioning, PM gates,
repair transactions, packet status, and strict route-plan parsing. The fix
should reuse those surfaces instead of adding a new repair ledger or redundant
recovery router.

## Goals / Non-Goals

**Goals:**

- Keep one PM repair menu with five current decisions.
- Ensure every nonterminal PM repair atomically produces a replacement current
  scope and a fresh executable packet.
- Retain append-only history while removing old nodes, packets, and route
  versions from current routing authority.
- Keep mandatory repair transaction fields minimal:
  `source_id`, `blocker_id`, and `fresh_packet_id`.
- Let PM inherit old work through replacement packet context instead of
  redoing from zero or reusing blocked evidence as completion.
- Require FlowGuard/reviewer gates for route redesign before the new route is
  activated.

**Non-Goals:**

- No compatibility parser for old repair decision names.
- No same-node repair-in-place path.
- No sender-reissue or collect-more-evidence PM menu entry.
- No PM-visible quarantine action; quarantine remains Runtime cleanup.
- No new global repair table beyond existing repair transactions.
- No deletion of historical ledger rows.

## Decisions

### Five Current PM Decisions

`repair_current_scope` replaces ordinary local repair. It creates a replacement
repair node for the current route node and issues that replacement node's next
required packet.

`repair_parent_scope` handles cases where a child-local fix is not enough. It
finds the nearest parent route node, supersedes that parent and descendants as
current authority, creates one replacement parent repair node, and issues its
next required packet.

`redesign_route` handles route-shape failure. It stays high risk and is staged
behind the existing PM decision gate. The staged effect may only apply from a
strict current route plan result.

`waive_with_authority` is terminal. It clears the blocker only when the PM
provides an authority reference; it creates no packet.

`stop_for_user` is terminal. It stops the blocker and target packet; it creates
no packet.

### Fresh Packet Gate

Runtime records a repair transaction before opening the blocker, but the
transition is only legal if `fresh_packet_id` is nonempty and resolves to a
current open packet. If the packet is missing, stale, superseded, accepted,
quarantined, or on an old route version, Runtime raises a control-plane error
instead of marking the blocker repaired.

### Replacement Scope Instead Of Same-Node Reset

The old same-node reset mutated the existing node, cleared its accepted/context
ids, and depended on a later helper to create some packet. That allowed a
blocker to become `repair_packet_open` even when no packet existed. The new
path uses replacement route nodes so there is a single activation point:
supersede old scope, create replacement scope, issue fresh packet, then mark the
blocker open.

### Parent And Route Repair

Parent repair reuses existing parent/child route fields. If a child has no
parent, Runtime rejects `repair_parent_scope` rather than guessing.

Route redesign reuses strict route plan parsing and materialization. PM text is
not enough; the route plan must be a current structured packet/result that
FlowGuard and Reviewer can inspect before activation.

## Risks / Trade-offs

- Rejecting old decision names will block older in-flight PM packets. This is
  intentional because the user requested no compatibility path; blocked PM
  packets must be reissued with the current menu.
- Parent repair depends on explicit parent/child route metadata. If a route is
  flat, PM must choose `repair_current_scope` or `redesign_route`.
- Route redesign is stricter than old `mutate_route`; this may require PM to
  produce a real route plan before progress resumes.

## Validation

- Add a focused FlowGuard model that makes the old hazards fail:
  same-node repair without packet, old decision names, activation without
  FlowGuard scan, parent repair keeping descendants current, and route redesign
  without a route plan.
- Add runtime tests for all five current PM decisions.
- Add negative tests for removed old decisions.
- Replay a June 3-shaped ledger fragment where the old same-node path produced
  an empty `fresh_packet_id`.
- Run install sync and install audit after repository tests pass.
