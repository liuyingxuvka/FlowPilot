## Why

The June 3 FlowPilot run showed a control-plane repair loop where PM repeatedly
selected same-node repair, but Runtime sometimes opened the blocker as if a
fresh repair packet existed while no executable packet had been created. The
repair surface also still exposes older decision names that split the same
concept across multiple paths.

This change is needed now so every nonterminal repair has one clean current
path: PM chooses a repair scope, Runtime creates the replacement scope and
fresh executable packet first, and only then may the blocker move to
`repair_packet_open`.

## What Changes

- **BREAKING** Replace the PM repair decision menu with exactly five current
  decisions: `repair_current_scope`, `repair_parent_scope`, `redesign_route`,
  `waive_with_authority`, and `stop_for_user`.
- **BREAKING** Reject old PM repair decisions including `same_node_repair`,
  `sender_reissue`, `collect_more_evidence`, `mutate_route`, and
  `quarantine_evidence` instead of translating them.
- Make ordinary repair abandon the current node as current authority, create a
  replacement repair node, and issue a fresh executable packet for that
  replacement.
- Make parent repair abandon the nearest parent scope and its descendants as
  current authority, create a replacement parent repair node, and issue a fresh
  executable packet for that replacement.
- Make route redesign use the existing high-risk PM gate, then create a new
  route version from a PM route-plan packet/result before activating the new
  route frontier.
- Require Runtime to verify `fresh_packet_id` exists and points to a current
  open packet before any nonterminal repair blocker may become
  `repair_packet_open`.
- Keep `waive_with_authority` and `stop_for_user` as terminal decisions that do
  not create a fresh packet.

## Capabilities

### New Capabilities

- `canonical-repair-scope-rotation`: Defines the current-only PM repair menu,
  replacement-scope creation, fresh-packet gate, and terminal waiver/stop
  behavior.

### Modified Capabilities

None. This establishes the new repair-scope contract rather than preserving the
older menu as a compatibility mode.

## Impact

- Runtime mechanics in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- PM repair decision and PM disposition packet prompts.
- Core runtime, high-standard control flow, recursive route execution, route
  mutation, and output-contract tests that referenced older decision names.
- New focused FlowGuard model and runner for repair-scope rotation.
- Installed FlowPilot skill synchronization, install audit, version, changelog,
  and local git commit after validation.
