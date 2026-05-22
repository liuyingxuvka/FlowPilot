## 1. Routing And Baseline

- [x] 1.1 Confirm real FlowGuard import, current git/coordination state, and the current deferred StructureMesh candidate list.
- [x] 1.2 Select the external-event data table because it is clean and the model shows it is a table-only false split target.

## 2. StructureMesh Classification

- [x] 2.1 Add explicit skip metadata for the external-event data table.
- [x] 2.2 Teach the full diagnostic to count explicit StructureMesh skips separately from deferred split gaps.
- [x] 2.3 Add focused assertions proving the skipped table has no functions/classes, remains over threshold, keeps external contract evidence, and no longer appears as a deferred split candidate.

## 3. Validation And Sync

- [x] 3.1 Run compile and focused diagnostic tests.
- [x] 3.2 Rerun model-test alignment plus coverage sweep/inventory.
- [x] 3.3 Run install/audit freshness checks and report whether local skill sync was needed.
- [x] 3.4 Record FlowGuard adoption evidence, KB postflight notes, and local git status.
