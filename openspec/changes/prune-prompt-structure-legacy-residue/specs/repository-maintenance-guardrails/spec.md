## ADDED Requirements

### Requirement: Maintenance Cleanup Classifies Legacy Residue Before Editing
Repository maintenance SHALL classify old-logic hits as active residue,
compatibility evidence, historical documentation, peer-owned scope, or deferred
structural debt before modifying files.

#### Scenario: Historical evidence remains
- **WHEN** a file mentions old logic only to document rejected behavior, known-bad fixtures, or compatibility proof
- **THEN** maintenance SHALL preserve it or clarify its status instead of deleting it as residue

#### Scenario: Active residue is patched narrowly
- **WHEN** active runtime or prompt guidance still teaches a retired control path
- **THEN** maintenance SHALL patch the narrow guidance and run focused validation for the touched surface

### Requirement: Shared Worktree Boundaries Stay Visible
Repository maintenance SHALL preserve peer-agent work and avoid staging,
rewriting, or claiming unrelated in-progress changes.

#### Scenario: Peer-owned change overlaps
- **WHEN** a residue candidate is in a file actively modified by another agent or by an in-progress OpenSpec change
- **THEN** maintenance SHALL either make a minimal non-overlapping patch after re-reading the file or report the candidate as peer-owned/skipped
