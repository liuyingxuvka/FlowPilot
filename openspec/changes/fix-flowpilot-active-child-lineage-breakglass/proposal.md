# Fix FlowPilot Active Child Lineage Breakglass

## Why

The June 27 FlowPilot run exposed a narrower gap than the earlier parent
repair hardening. A child route node could be superseded by a valid repair
replacement, but parent repair and parent backward replay still copied the old
`child_node_ids` list. That let parent review keep composing from stale child
evidence even after the child had an accepted replacement.

The same run also showed that repeated same-root blockers did not reach
break-glass because resolved-looking blockers with `cleared_by_outcome_id` were
excluded from the repair-loop count before the root cause had been proven
closed.

## What Changes

- Add one strict active child lineage resolver for route-node children.
- Use that resolver before route-node repair replacement and before parent
  backward replay.
- Reject unresolved, cyclic, missing, or still-superseded child lineage instead
  of falling back to old child evidence.
- Surface active child lineage and active repair child result ids in parent
  replay packets.
- Keep same-root blockers countable until current lineage evidence proves the
  root cause closed.
- Upgrade existing PM, Controller, FlowGuard, and Reviewer guidance so old child
  ids are never accepted as current evidence.
- Add executable Cartesian coverage for active child resolution, parent replay,
  blocker counting, and break-glass threshold behavior.

## Non-Goals

- No compatibility path for old packets or old child ids.
- No fallback to historical evidence when active lineage cannot be resolved.
- No new repair decision family.
- No broad new evidence ledger.
- No continuation of old FlowPilot runs as current authority; future runs start
  clean and must use the current single path.
