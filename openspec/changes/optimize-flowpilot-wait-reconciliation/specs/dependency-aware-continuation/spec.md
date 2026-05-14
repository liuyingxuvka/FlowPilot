## ADDED Requirements

### Requirement: Router may continue only non-dependent work while packets are pending
The Router SHALL classify pending packet or role-work dependencies as `blocking`, `advisory`, or `prep-only` and select continuation actions only when those actions do not depend on unresolved blocking work.

#### Scenario: Non-dependent work is available
- **WHEN** a blocking packet is pending for a later reviewer gate and a current metadata/status action does not depend on that packet
- **THEN** the Router may perform the metadata/status action without waiting for the packet result

#### Scenario: Dependent PM decision is not available
- **WHEN** a PM final decision depends on an unresolved blocking packet
- **THEN** the Router does not request or accept that PM final decision as complete

### Requirement: Advisory work does not freeze unrelated progress
An advisory request SHALL NOT block unrelated non-dependent actions while it is pending.

#### Scenario: Advisory request pending
- **WHEN** an advisory officer request is open and the next Router action does not depend on that officer's advice
- **THEN** the Router may continue the non-dependent action

### Requirement: Advisory work is resolved before terminal closure
Terminal closure SHALL remain blocked until every advisory request is absorbed, canceled, superseded, or explicitly carried forward by an authorized PM closure decision.

#### Scenario: Advisory request unresolved at closure
- **WHEN** terminal closure is requested and an advisory request remains unresolved
- **THEN** the Router blocks terminal closure and requests PM disposition

### Requirement: Active-holder direct returns preserve authority
Active-holder ACK, progress, and result submission SHALL be accepted only when run id, packet id, target role, holder identity, hash or envelope reference, and current route/frontier authority match the Router-issued lease.

#### Scenario: Wrong holder submits a result
- **WHEN** a role that is not the current active holder submits a direct result for a packet
- **THEN** the Router rejects the result and records a protocol blocker or recovery path

### Requirement: Role returns use only Router-authorized events
Role ACK, progress, and result returns SHALL be accepted only when the submitted event is present in the Router's current `allowed_external_events` for that run, packet or request, role, and result target. Prompt or card wording alone SHALL NOT create event authority.

#### Scenario: Stale event name is submitted
- **WHEN** a role submits a result with an event name that is not in the current `allowed_external_events`
- **THEN** the Router rejects the return and records a correction or recovery action instead of absorbing the result

### Requirement: Role-work results match the registered request
PM role-work result absorption SHALL bind the result to the registered request by run id, request id, target role, output contract id, and result target.

#### Scenario: Wrong request id returns
- **WHEN** a result envelope names a request id different from the open PM role-work request
- **THEN** the Router leaves the original request unresolved and rejects or quarantines the mismatched result

### Requirement: Prompt promises match runtime capability
PM and role cards SHALL advertise active-holder, dependency-continuation, partial-batch, or role-work return behavior only when the Router runtime and event capability registry support the same behavior.

#### Scenario: Card promises unsupported active-holder behavior
- **WHEN** a card instructs a role to use an active-holder return path that the runtime cannot authorize
- **THEN** validation blocks the card/runtime update until the capability registry, runtime, and prompt wording are aligned
