## Context

The current router file is much smaller than the original monolith, but most of
its remaining size is compatibility glue. A read-only AST inventory found 899
top-level functions in `flowpilot_router.py`; 852 are tiny wrappers. That means
the largest remaining structural debt is not business logic but old function
name preservation.

## Goals

- Make `flowpilot_router.py` a readable skeleton.
- Keep supported CLI/runtime entrypoints stable.
- Remove the old assumption that every private helper remains public.
- Preserve behavior while internal owner modules are progressively rewired.
- Keep the split observable through FlowGuard StructureMesh and tests.

## Non-Goals

- Do not rename event names, schema values, ledger shapes, or CLI commands.
- Do not split one function per file.
- Do not push to GitHub, tag, or publish a release.
- Do not hide behavior changes behind a weakened model invariant.

## Public API Policy

The public router surface is now an allowlist. It includes the CLI command
surface and the runtime entrypoints still used by supported callers, such as
`main`, `parse_args`, `next_action`, `apply_action`,
`apply_controller_action`, `record_external_event`,
`record_controller_action_receipt`, `run_until_wait`,
`run_router_daemon`, `stop_router_daemon`, `foreground_controller_standby`,
`controller_patrol_timer`, `validate_artifact`, and
`write_role_output_envelope`.

Private helper names are no longer considered public compatibility contracts.
During the final split, an explicit owner-export registry may broker internal
owner lookups so the refactor remains behavior-preserving, but that registry is
not the public API.

## Structure

1. **Router skeleton**
   - Owns CLI bootstrap.
   - Owns the public API allowlist.
   - Imports child owners and installs explicit internal owner exports.
   - Does not contain hundreds of hand-written compatibility wrappers.

2. **Owner-export registry**
   - Maps transitional internal helper names to their owner modules.
   - Binds owners to the router skeleton only when a lookup is used.
   - Keeps old private helpers out of the documented public contract.

3. **Real owner modules**
   - Own behavior bodies such as startup, controller runtime, work packets,
     events/repair, route frontier, route artifacts, system cards, terminal
     ledger, and artifact validation.
   - Oversized owners are split by behavior family once the skeleton is stable.

## FlowGuard Evidence

StructureMesh must model the parent as a skeleton, not as a broad compatibility
facade. The model should require:

- every public entrypoint has an explicit owner;
- private legacy helpers are either removed from public entrypoints or owned by
  a child through the owner-export registry;
- no duplicate state, side-effect, or config ownership;
- no missing child owner paths;
- no overclaim that old private helper names are public compatibility promises;
- routine and release evidence remain visible separately.

## Validation Strategy

Run focused compile/import checks after the skeleton conversion, then the
router boundary/runtime tests that exercise the public allowlist and internal
owner lookups. Run StructureMesh/TestMesh/model-alignment checks before broad
regressions. Run Meta and Capability regressions after code/model convergence.
Use hidden/background artifacts for long tiers and inspect final exit files.
