## Why

FlowPilot has now adopted FlowGuard as the kernel, but prompt surfaces, runtime
cards, derived-view registries, and maintenance docs can still carry stale
wording from older control-plane designs. These residues are risky because they
can teach agents to use retired paths even when the executable model and tests
now reject those paths.

## What Changes

- Audit active prompt, card, registry, and structure surfaces for wording that
  still instructs FlowPilot roles to use retired recovery, direct-dispatch,
  ACK-as-completion, chat-body, or compatibility-facade authority.
- Patch only active behavior-bearing surfaces where the old wording is
  incorrect or ambiguous under the FlowGuard-kernel contract.
- Preserve explicit legacy compatibility evidence, negative fixtures, and
  historical notes when they are clearly marked as rejected, retired, or
  test-only evidence.
- Keep this cleanup independent from peer-owned maintenance convergence work
  and avoid broad StructureMesh splits or repo-wide rewrites.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: active prompts and cards must not present
  retired legacy control paths as valid instructions.
- `flowpilot-derived-view-registries`: registry and derived-view text must
  distinguish canonical owner authority from compatibility exports.
- `repository-maintenance-guardrails`: maintenance cleanup must classify
  prompt/structure legacy residues before editing and must preserve peer-agent
  worktree boundaries.

## Impact

- Affected areas may include `skills/flowpilot/`, runtime card assets,
  FlowPilot prompt-boundary simulations, OpenSpec specs/tasks, and focused
  tests.
- No public API, dependency, release, push, or tag action is in scope.
- Compatibility facades and legacy negative fixtures remain in scope only as
  evidence, not as active runtime guidance.
