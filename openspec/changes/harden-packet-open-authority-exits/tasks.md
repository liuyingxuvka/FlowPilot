## 1. Model And Contract

- [x] 1.1 Confirm real FlowGuard import for this change.
- [x] 1.2 Add focused FlowGuard coverage for packet-open authority and formal-exit hazards.
- [x] 1.3 Validate the OpenSpec change.

## 2. Runtime And Prompt Implementation

- [x] 2.1 Add successful-open work-authority metadata to packet runtime session, envelope, ledger, and status payloads.
- [x] 2.2 Strengthen packet identity text and role cards so verified open means continue work or submit a formal existing exit.
- [x] 2.3 Strengthen PM cards so PM inability uses startup repair, startup protocol dead-end, or control-blocker repair decision instead of a PM self-blocker.

## 3. Tests And Verification

- [x] 3.1 Add focused packet runtime assertions for open-authority metadata.
- [x] 3.2 Add prompt/card coverage assertions for PM and ordinary role exits.
- [x] 3.3 Run focused FlowGuard checks, OpenSpec validation, focused pytest, and install sync/audit.

## 4. Coordination And Finalization

- [x] 4.1 Check whether Step 3 active-writer waiting and Step 4 monitor current-work ownership are already owned by parallel changes.
- [x] 4.2 Defer heavyweight meta/capability checks after user confirmed they are too heavy for this pass; stop any started background run and record no pass/fail claim.
- [ ] 4.3 Preserve compatible peer-agent changes and prepare the combined local git state requested by the user.
