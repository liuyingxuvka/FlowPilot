## ADDED Requirements

### Requirement: Active surfaces use requested-responsibility topology

FlowPilot active source, prompt, template, documentation, model, and test surfaces SHALL describe current role work as requested runtime responsibilities rather than a fixed runtime roles, fixed worker pair, or fixed role count.

#### Scenario: Startup and resume avoid fixed runtime roles requirements
- **WHEN** a current startup, resume, heartbeat, or recovery surface describes role setup or restoration
- **THEN** it names the currently required requested responsibilities or the runtime-provided responsibility value
- **AND** it MUST NOT require PM, reviewer, Route-scope FlowGuard operator, Product-scope FlowGuard operator, Worker A, and Worker B as an unconditional current cohort.

#### Scenario: Worker labels are not fixed topology
- **WHEN** worker or helper work is described for a current run
- **THEN** the wording uses requested worker responsibility, addressed role binding, or packet holder language
- **AND** Worker A/Worker B names must not appear as current runtime keys unless a file is explicitly documenting historical or unsupported-run behavior.

### Requirement: Process/Product-scope FlowGuard operators are not current authority

FlowPilot SHALL NOT use `Route-scope FlowGuard operator`, `Product-scope FlowGuard operator`, `process_flowguard_operator`, or `product_flowguard_operator` as a current responsibility, prompt recipient, packet owner, or test expectation.

#### Scenario: FlowGuard operator process-model work is requested
- **WHEN** the runtime needs development-process, route, evidence-freshness, or workflow modeling
- **THEN** it requests `flowguard_operator`
- **AND** evidence policies and tests name that responsibility rather than an old Route-scope FlowGuard operator.

#### Scenario: FlowGuard operator product-model work is requested
- **WHEN** the runtime needs product-function architecture modelability or product behavior modeling
- **THEN** it requests `flowguard_operator`
- **AND** evidence policies and tests name that responsibility rather than an old Product-scope FlowGuard operator.

### Requirement: Validation and closure are system outcomes

FlowPilot SHALL treat validation and closure as current router/system/PM ledger outcomes, not as Validator or Closure Officer role bindings.

#### Scenario: Review acceptance leads to system validation
- **WHEN** accepted review evidence allows validation to proceed
- **THEN** the runtime records system validation through current ledger authority
- **AND** it MUST NOT issue or require a Validator role packet.

#### Scenario: Terminal closure uses current closure authority
- **WHEN** final closure is attempted
- **THEN** closure uses current final ledger, requirement-evidence, and final-preflight authority
- **AND** it MUST NOT issue or require a Closure Officer role packet.

### Requirement: Fresh runtime guidance does not teach old Router authority

FlowPilot current-authority prompts and docs SHALL present `flowpilot_new.py` and lifecycle guard foreground duty as the fresh formal runtime path.

#### Scenario: Old Router command appears in active text
- **WHEN** a current active prompt or public doc mentions `flowpilot_router.py`, Router daemon files, Controller action ledgers, `controller-standby`, or patrol timers
- **THEN** that text must classify the path as old-run diagnostic, legacy reference, or explicit unsupported-run repair
- **AND** it MUST NOT instruct fresh runtime operation to attach to old Router authority.
