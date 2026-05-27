## Context

The current FlowPilot protocol has the right raw ingredients: officer reports
must list `model_obligations`, `ordinary_test_evidence`, `missing_test_kinds`,
`conformance_boundary`, `residual_blindspots`, and background-test completion
details. Reviewers and final ledgers already reject stale or skipped evidence.

The weak point is ownership. A FlowGuard officer can say which tests are
missing, and a worker can report what was changed, but PM is not required to
create a structured before/after test obligation view and route each gap to a
specific next action.

## Goals / Non-Goals

**Goals:**

- Make PM the explicit owner of test-obligation disposition.
- Preserve FlowGuard officer ownership of model obligations and gap analysis.
- Preserve worker ownership of packet-scoped test maintenance and execution.
- Require reviewers to block node completion when PM has not dispositioned test
  gaps.
- Make final evidence ledgers carry the same test obligation rows instead of
  collapsing them into broad "tests passed" claims.

**Non-Goals:**

- Do not make FlowGuard models as deep as one state per line of code.
- Do not require officers to write ordinary test code by default.
- Do not force every missing test into a new route node; PM may use same-node
  worker test packets, TestMesh, Model-Test Alignment, waiver with authority,
  or blocker disposition depending on risk.
- Do not change frozen acceptance contracts, release policy, or public API.

## Design

### Test Obligation Matrix

PM writes a `test_obligation_matrix` object in the node acceptance plan before
worker dispatch. It has two passes:

- `pre_worker`: derived from root requirements, product/process FlowGuard
  model obligations, child-skill standards, acceptance slice, and known
  validation commands.
- `post_worker`: updated after worker/officer results return, based on changed
  paths, result evidence, newly discovered gaps, stale evidence, failed tests,
  and skipped or background validations.

Each row names the obligation id, source, required test kind, current evidence,
freshness status, owner role, and PM disposition. Disposition values are:
`covered`, `worker_test_packet_required`, `testmesh_required`,
`model_test_alignment_required`, `waived_with_authority`, `deferred_to_named_node`,
or `blocked`.

### Role Responsibilities

- PM owns matrix creation, update, and final disposition.
- Product FlowGuard Officer and Process FlowGuard Officer own model obligations,
  missing test kinds, conformance boundary, residual blindspots, and model
  counterexample interpretation.
- Workers own packet-scoped test code maintenance, test execution, and evidence
  return when PM assigns a worker test packet or current-node packet includes
  test obligations.
- Reviewer owns blocking review when PM tries to close a node while matrix rows
  are missing, stale, skipped, failed, running without exit/meta artifacts, or
  undispositioned.
- Controller remains a relay and mechanical validator only.

### Escalation

PM uses the smallest sufficient path:

- direct worker packet for ordinary test maintenance inside the current packet
  boundary;
- TestMesh when evidence is broad, slow, layered, stale, skipped, progress-only,
  or release-only;
- Model-Test Alignment when model obligations, code contracts, and ordinary
  tests do not line up;
- same-node repair or sender reissue when a result omitted required evidence;
- route mutation only when the current node cannot semantically contain the
  missing validation work.

### Validation

Add a focused FlowGuard process model that rejects node completion before:

- pre-worker matrix creation;
- worker/officer report absorption;
- post-worker matrix update;
- PM disposition of every missing test kind;
- required worker test packet, TestMesh, or Model-Test Alignment completion;
- reviewer check of the PM-built package.

Add ordinary tests that check the runtime cards and contract registry expose the
new required phrases and conditional sections.

## Risks / Trade-offs

- The matrix could become ceremony if every row is boilerplate. Mitigation:
  require source, evidence, freshness, and disposition fields, and let PM mark
  irrelevant rows as `covered` or `waived_with_authority` with reason instead
  of spawning unnecessary work.
- Validation could become too heavy. Mitigation: route broad or layered
  validation through TestMesh rather than forcing every node to run full release
  checks.
- Parallel agents may be editing nearby model-test alignment files. Mitigation:
  add a focused model/test pair and avoid modifying currently dirty alignment
  source rows unless required.
