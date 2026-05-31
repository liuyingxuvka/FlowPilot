## 1. Protocol Boundary

- [x] 1.1 Confirm the current runtime path is `flowpilot_new.py lease-agent -> ack -> submit-result`.
- [x] 1.2 Remove `controller_relay` as a required packet/result field and body-open precondition.
- [x] 1.3 Remove current user-facing `relay-envelope` command exposure.
- [x] 1.4 Update packet-chain audit/report wording so missing relay is not a blocker.

## 2. Cards and Models

- [x] 2.1 Update role cards and packet identity prompt to stop requiring `open-packet`, `run-packet`, or Controller relay authority.
- [x] 2.2 Update packet-open authority FlowGuard model and expected hazards.
- [x] 2.3 Add or update focused tests so the lease/ACK/result path is the expected current protocol.

## 3. Validation and Sync

- [x] 3.1 Run targeted FlowGuard/model checks for packet-open authority and new-only runtime.
- [x] 3.2 Run focused runtime/card tests affected by the relay removal.
- [x] 3.3 Validate the OpenSpec change.
- [x] 3.4 Rebuild/check FlowGuard project topology if required by changed model surfaces.
- [x] 3.5 Sync repository-owned FlowPilot skill files into the local installed skill.
- [x] 3.6 Run local install sync audit and install check after sync.
- [x] 3.7 Record FlowGuard adoption evidence and KB postflight.
