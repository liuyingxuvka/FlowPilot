## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create the OpenSpec change and route the work through FlowGuard.
- [x] 1.2 Add role-continuity and blocker-repair requirements.
- [x] 1.3 Validate the OpenSpec change.

## 2. Runtime Role Continuity

- [x] 2.1 Add current-run role continuity slots and bounded role memory summaries.
- [x] 2.2 Make same-role leases prefer the usable current-run agent.
- [x] 2.3 Attach memory seeds when a role is replaced.
- [x] 2.4 Surface role memory through handoff metadata and the role-only open-packet result.

## 3. Repair Packet Specificity

- [x] 3.1 Add blocker recommendation, target context, and stale evidence to PM repair-decision packets.
- [x] 3.2 Add explicit required-deliverable contracts to repair reissue packets.
- [x] 3.3 Add repeat blocker family context without making it an automatic hard stop.

## 4. Tests And Model Evidence

- [x] 4.1 Add focused runtime tests for same-role reuse and replacement memory.
- [x] 4.2 Add focused runtime tests for PM repair packet context and repair reissue deliverable contracts.
- [x] 4.3 Run focused tests and required FlowGuard/OpenSpec checks.
- [x] 4.4 Run required model regressions in background where practical.

## 5. Sync And Finalization

- [x] 5.1 Sync the installed local FlowPilot skill from the repository version.
- [x] 5.2 Run install freshness checks or report any blocker.
- [x] 5.3 Update FlowGuard adoption evidence and topology if required.
- [x] 5.4 Record KB postflight if the work exposed reusable lessons.
- [x] 5.5 Commit the intended local git changes without reverting peer-agent work.
