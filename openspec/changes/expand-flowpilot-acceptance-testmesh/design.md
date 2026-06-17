## Context

The acceptance-item registry implementation currently has focused runtime tests, model checks, fake-project rehearsal, topology checks, and install validation. That proves the scoped feature path, but it leaves release-grade confidence dependent on dispersed evidence and manual interpretation. The existing repository already owns slow-test and tiering concerns through FlowGuard TestMesh and the `scripts/run_test_tier.py` hierarchy.

The next step is to turn the acceptance-registry validation claim into an explicit TestMesh artifact with child ownership and finite payload cells, then add targeted tests for fake AI/work-package payload classes that can otherwise hide behind a green happy path.

## Goals / Non-Goals

**Goals:**

- Define a parent acceptance-registry TestMesh with child partitions for registry compilation, route ownership, node acceptance plans, work packets, PM disposition, terminal replay, route mutation, and fake AI chaos payloads.
- Add focused negative and recovery cases for acceptance item ids, terminal segment targets, PM disposition item closure, and route mutation currentness.
- Preserve current evidence freshness by keeping slow/timed-out tier evidence visible instead of claiming a parent pass from progress-only output.
- Keep the validation route compatible with existing FlowPilot runtime and TestMesh surfaces.

**Non-Goals:**

- Add a new FlowPilot runtime authority, ledger, packet kind, or compatibility path.
- Run every release tier in the foreground before the child TestMesh structure exists.
- Refactor the existing medium-priority structure split candidate reported by model-test alignment.

## Decisions

1. **Use a new acceptance TestMesh parent instead of expanding every broad router tier.**
   - Rationale: The risk is not that every router test is missing; the risk is that parent confidence hides which acceptance-registry child cell was actually covered.
   - Alternative considered: Run `router`, `integration`, or `release` tiers directly. This gives useful evidence, but it does not produce child ownership or payload-cell coverage and can time out as one opaque parent command.

2. **Represent fake AI/work-package validation as finite payload cells.**
   - Rationale: The prior miss came from fake AI answering against static fixtures rather than the opened packet body. Payload cells make this class testable: missing, extra, stale, duplicate, wrong-owner, and wrong-target cases must be named.
   - Alternative considered: Add one more end-to-end fake project scenario only. That improves confidence but still risks missing payload-shape variants.

3. **Keep runtime code unchanged unless a new test exposes a current-contract miss.**
   - Rationale: The acceptance registry implementation is already green; this change is primarily validation hardening.
   - Alternative considered: Add new runtime state for acceptance test evidence. Rejected because existing packets, results, route nodes, ledgers, and TestMesh artifacts can carry the evidence.

4. **Treat slow quality-gate foreground timeout as a TestMesh evidence issue.**
   - Rationale: A timeout from a thick parent command is neither pass nor functional failure. The parent claim must consume current child evidence or explicitly show release-scope gaps.
   - Alternative considered: Increase the foreground timeout indefinitely. Rejected because it does not fix evidence granularity.

## Risks / Trade-offs

- Slow child suites may still be expensive to run -> Split the highest-risk cells first and preserve release-scope gaps when not every tier is current.
- More validation artifacts can become stale -> Rebuild/check topology and run install checks after changing model runners or result paths.
- Fake AI payload tests can become overfit to fixtures -> Derive expected fields from current packet bodies and contract catalog functions rather than duplicating sealed body literals.
- Existing peer-agent changes can overlap nearby terminal replay work -> Keep this change scoped to acceptance TestMesh artifacts and avoid editing peer OpenSpec directories.
