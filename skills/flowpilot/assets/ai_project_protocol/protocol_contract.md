# AI Project Protocol Contract

## Core Rule

The project black-box ledger is the truth. Chat memory, an agent's local memory,
old run folders, and progress messages are useful context only when they are
converted into ledger records with fresh evidence.

The protocol model is:

`ProjectInput x ProjectState -> Set(ProjectOutput x ProjectState)`

Every meaningful action must be represented as a state transition in the ledger.

## Stable Responsibilities

The system has stable responsibilities, not fixed permanent people:

- Router: chooses the next legal action.
- Planner: creates route versions and task packets.
- Worker: executes a scoped packet.
- Reviewer: independently checks a result packet.
- FlowGuard operator: models the risk and reports executable evidence.

Any of these responsibilities may be served by a newly leased background agent.
An agent lease can be closed, replaced, retried, or superseded. The protocol
must not require a fixed number of always-alive agents.

## Black-Box Ledger

The ledger stores:

- user goal and acceptance contract;
- route versions and active route pointer;
- agent leases and heartbeats;
- task packet envelopes and bodies;
- result packet envelopes and bodies;
- review reports;
- FlowGuard work orders, route decisions, and evidence;
- final backward closure records.

The router makes decisions from ledger state and packet envelopes. Workers get
only their own packet body and approved references. Reviewers get the submitted
result, claimed evidence, and review criteria. This separation is the prompt
isolation boundary.

## Dynamic Agent Lease Contract

ACK means the agent is alive. ACK does not mean the work is done.

Progress means the agent may still be working. Progress does not mean the work
is done.

Completion requires all of these:

- the lease is active when the result is submitted;
- the result packet matches the task packet and route version;
- the result packet has a valid envelope and body;
- claimed evidence is fresh for the current route/source state;
- an independent reviewer accepts the result;
- required FlowGuard checks pass or explicitly scope a remaining gap.

Output from a closed, expired, or superseded lease is not authoritative.

## Packet Isolation

A task packet has an envelope and a body.

The envelope says where the work belongs: packet id, route version,
responsibility, allowed tools, required output type, timeout, evidence inputs,
and review requirement.

The body says what the worker should do. It may contain details that other
workers should not see.

A result packet also has an envelope and a body.

The result envelope says who produced it, which task packet it answers, which
route version it belongs to, what changed, what evidence was produced, and when
that evidence was produced.

The body contains the actual result.

## FlowGuard Route Scheduler

The FlowGuard operator must say what is being modeled before it starts:

- target product behavior;
- development process;
- dynamic agent lifecycle;
- task/result packet lifecycle;
- route mutation;
- evidence freshness;
- review isolation;
- final backward closure.

The route scheduler then selects the matching FlowGuard skill.
A model of the target product cannot be used as proof that the development process is safe.
A model of the development process cannot replace product behavior checks.

## Final Backward Closure

The project can close only after a backward chain exists:

1. user goal;
2. active route version;
3. accepted task/result packets;
4. independent reviews;
5. FlowGuard route decisions and checks;
6. fresh executable validation;
7. explicit skipped, blocked, stale, or out-of-scope gaps.

If the chain breaks, the project is not complete.

## Failure Cases That Must Stay Blocked

- Missing ACK.
- ACK with no result.
- Result packet with the wrong shape.
- Result from a closed agent lease.
- Result from an old route version silently accepted into a new route.
- Worker self-review.
- Review that does not check evidence.
- FlowGuard modeling the wrong target.
- Stale evidence reused as fresh evidence.
- Final closure claim without the backward chain.
