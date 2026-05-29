# AI Project Protocol Stress Testing

This file describes the deterministic stress layer for the clean AI project
protocol kernel. It is a rehearsal boundary, not a replacement runtime.

The stress layer answers this question:

Can the protocol still protect the project ledger when several background AI
leases, route versions, reviewers, FlowGuard work orders, and evidence
generations interact across multiple rounds?

## Fake AI Actors

Fake AI actors are deterministic protocol actors. They do not call external AI
services. They simulate the outcomes that matter to the ledger:

- worker ACK;
- worker progress without output;
- valid result packet;
- wrong-shaped result packet;
- timeout;
- closed lease;
- late output from a closed lease;
- independent review;
- self-review;
- weak review that does not inspect evidence;
- correct or incorrect FlowGuard modeled target;
- fresh or stale evidence;
- route mutation with old packets still visible;
- final backward closure or closure gap.

ACK is liveness only. Progress is liveness only. Neither can close a packet.

## Multi-Round Scenarios

The deterministic scenario set covers both good recovery and bad long-run
paths:

- replacement worker succeeds after a dead worker;
- missing ACK;
- ACK without output;
- wrong-shaped result;
- closed worker returns late output;
- route mutation receives old-route output;
- weak review accepts without checking evidence;
- worker reviews itself;
- stale evidence is reused after a source change;
- FlowGuard models the wrong thing;
- stale and current results appear in the same route segment;
- final backward closure is missing;
- background progress exists without final exit evidence.

The key good path is not "one worker always succeeds." The key good path is:
old bad work can be closed or quarantined, a replacement lease can receive a
current packet, and only the replacement's current, reviewed, fresh result can
be accepted.

## FlowGuard Target Discipline

Every FlowGuard work order must name the thing being modeled before it starts:

- target product behavior;
- development process;
- packet lifecycle;
- dynamic agent lifecycle;
- evidence lifecycle;
- review isolation;
- final closure.

A green model for the wrong target is a blocked path. For example, a product
behavior model cannot prove that the development process was safe, and a
development-process model cannot replace product behavior validation.

## TestMesh Evidence

The stress runner writes a result artifact with named child evidence rows:

- focused kernel compatibility;
- deterministic multi-round scenarios;
- seeded random long-run checks;
- historical bad-case replay;
- FlowGuard stress-model exploration;
- background Meta and Capability regressions;
- local install-surface parity.

The routine stress gate can pass from the focused deterministic children. The
release stress gate needs the background and install rows too.

Missing, stale, skipped, failed, progress-only, or not-run evidence cannot
satisfy the release gate.

## Historical Bad Cases

The replay pack keeps known old failure families executable:

- ACK without output;
- closed-agent late output;
- route mutation with stale output;
- stale evidence reuse;
- progress-only background evidence;
- wrong FlowGuard modeled target;
- weak review;
- self-review;
- final closure gap.

These cases stay as blocked examples so future refactors cannot silently turn
old failure modes back into accepted completion evidence.
