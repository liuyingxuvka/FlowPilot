## Context

The current AI project protocol kernel is intentionally small. It models the
core contract: a result can only become authoritative when the lease, packet,
route version, independent review, FlowGuard target, evidence freshness, and
final backward chain all line up.

That is necessary but not enough for the user's target system. The target
system will run for many rounds with dynamic background agents. A worker may
ACK and disappear, a closed lease may later return output, a route may mutate
while old packets are still open, and a weak reviewer or wrong FlowGuard
operator can accidentally turn a progress signal into a completion claim.

This change adds a stress layer around the protocol kernel without replacing
the kernel or the old FlowPilot router. The stress layer is a test and evidence
boundary: it exercises fake agents and FlowGuard-backed state transitions until
the protocol proves that bad long-run paths are blocked and recoverable good
paths can still finish.

## Goals / Non-Goals

**Goals:**

- Represent fake AI agents as leases that can ACK, progress, submit output,
  stall, die, close, or return late.
- Exercise multi-round scenarios where the same project ledger sees several
  leases, route versions, reviews, and evidence generations.
- Prove that only current-route, current-lease, fresh-evidence, independently
  reviewed, correctly modeled results can be accepted.
- Prove recovery paths: a dead or closed worker can be replaced by a new lease
  and a new packet, while the old worker's later output remains blocked.
- Provide seeded random long-run checks that are deterministic enough to rerun
  from the same seed when a failure appears.
- Preserve a historical bad-case replay pack so known old failure families stay
  visible and executable.
- Publish a TestMesh-style evidence object that separates child validation
  rows and refuses to call the parent stress gate green if any child is stale,
  skipped, failed, or progress-only.

**Non-Goals:**

- Do not replace the current FlowPilot router.
- Do not write a new UI beyond documentation/assets needed for the protocol
  kernel.
- Do not mutate or depend on old `.flowpilot/` runtime state.
- Do not push, tag, release, deploy, or publish remotely.
- Do not change the frozen acceptance contract of already completed changes.

## Decisions

### Use a deterministic fake-agent harness

The fake agents are plain deterministic state transitions rather than calls to
real LLMs. This makes each failure reproducible, cheap, and safe to run inside
unit tests. Real background agents are too nondeterministic for a first-line
regression harness.

Alternative considered: use real background agents as the primary test. That
would better mimic production behavior, but it would be slow, flaky, and hard
to reproduce. Real agents can later be tested above this harness once the
protocol boundary is already enforced.

### Keep the stress model adjacent to the kernel model

The stress model will live under `simulations/` beside
`ai_project_protocol_model.py` and import the same concepts where practical.
It remains a separate model because its purpose is multi-round evidence, not
the minimal kernel contract.

Alternative considered: expand the existing kernel model. That risks turning
the small contract model into a bulky scenario runner. Keeping a separate
stress model preserves the kernel as the readable protocol core.

### Treat TestMesh as a generated evidence report

The stress runner will write a JSON result that includes child evidence rows:
focused kernel compatibility, deterministic multi-round scenarios, seeded
random long runs, historical replay, FlowGuard exploration, background model
regressions, and install-surface parity. The parent gate passes only when all
required child rows are current and passing.

Alternative considered: put all checks into one pytest file. That would be
easy, but it would hide which layer failed and could accidentally make a broad
parent test mask a stale or skipped child.

### Make FlowGuard target selection explicit

A FlowGuard operator packet must name what it is modeling: product behavior,
development process, packet lifecycle, dynamic agent lifecycle, evidence
lifecycle, or final closure. The stress checks include wrong-target cases
because the user specifically called out that FlowGuard's sub-skills must be
used in the correct place, not just invoked somewhere.

Alternative considered: model FlowGuard as a single pass/fail flag. That would
miss a core failure family: a green model for the wrong object can create false
completion confidence.

## Risks / Trade-offs

- Random checks can become flaky if they depend on uncontrolled time or external
  services → Use seeded pseudo-random events with no network or wall-clock
  dependency.
- A stress harness can grow into a second implementation of the runtime → Keep
  it as a finite protocol simulator and evidence checker, not a router.
- A broad stress result can hide stale child evidence → Include named child
  rows and require current pass status for each parent confidence claim.
- Generated result files can become stale after source changes → Tests will run
  the runner and assert that the source and result artifact agree.
- Background regressions can be mistaken for complete while still running →
  Final validation must inspect exit and metadata artifacts before claiming
  pass.

## Migration Plan

1. Add the new OpenSpec capability and keep it active until implementation is
   complete.
2. Add protocol stress documentation and examples beside the existing protocol
   assets.
3. Add the deterministic stress harness, FlowGuard model exploration, TestMesh
   report, and result writer.
4. Add focused pytest coverage for scenario names, bad-path blocking,
   replacement success, seeded random reproducibility, historical replay, and
   evidence rows.
5. Update install checks and version notes.
6. Run focused checks, strict OpenSpec validation, heavyweight background model
   regressions, local install sync/audit/check, and local git commit.

Rollback is simple because this change is additive: revert the OpenSpec change,
new stress assets, new simulation files, test additions, and version/install
metadata updates.

## Open Questions

No user decision is required before implementation. The first version will use
deterministic fake agents and background project regressions; live real-agent
tests can be added as a later capability after the deterministic layer is
stable.
