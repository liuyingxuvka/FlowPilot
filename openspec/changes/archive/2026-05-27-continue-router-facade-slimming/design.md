## Context

The prior StructureMesh pass split the protocol/catalog band and reduced
`flowpilot_router.py` to about 12.5k lines. The facade still owns several large
clusters that are not true public entrypoint logic:

- startup/self-interrogation status and issue helpers;
- payload-contract builders for role, PM, display, resume, and terminal
  actions;
- system-card and system-card-bundle action selection, delivery artifact
  commits, and return reconciliation helpers.

## Goals

- Reduce `flowpilot_router.py` without changing public import names.
- Keep function ownership coarse and behavior-oriented.
- Align FlowGuard StructureMesh target modules with real files.
- Keep tests and background evidence explicit.

## Non-Goals

- Do not split one function per file.
- Do not remove `flowpilot_router.py` as the public facade.
- Do not rename event names, schema values, ledger shapes, or CLI commands.
- Do not push to GitHub or publish a remote release.

## Design

### Facade-first extraction

The facade remains the public compatibility owner. Extracted modules are internal
owners and receive the bound router facade before executing moved logic. Public
callers continue using `flowpilot_router`.

### New owner modules

- `flowpilot_router_self_interrogation.py`: self-interrogation index, issue, and
  status helpers.
- `flowpilot_router_payload_contracts.py`: payload contract builders and
  role/PM/display/terminal contract helpers.
- `flowpilot_router_system_cards.py`: system-card action selection, direct ACK
  token construction, delivery artifact commit, and card return reconciliation.

### FlowGuard evidence

The router facade StructureMesh target must add these owner modules and must keep
the facade as the public import and CLI owner. TestMesh evidence should map:

- self-interrogation to startup/router boundary tests;
- payload contracts to startup, PM role-work, closure, and boundary tests;
- system cards to router card/ACK return tests.

### Validation strategy

Run focused compile and router tests immediately after extraction, then run the
router background tier and release tier in hidden background mode. Meta and
Capability checks should be run after model evidence changes if the maintenance
pass reaches release readiness.

## Risks

- Moved functions may rely on facade globals. Mitigation: bind the router facade
  into the owner module before executing moved logic.
- Test evidence may overclaim if model ownership names drift from real files.
  Mitigation: StructureMesh must require new target modules to exist.
- Background reruns can collide with still-running artifacts. Mitigation: inspect
  final exit artifacts and process liveness before counting or rerunning.
