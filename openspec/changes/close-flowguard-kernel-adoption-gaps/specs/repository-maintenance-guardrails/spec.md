## ADDED Requirements

### Requirement: Adoption closure preserves peer-agent work boundaries
Repository maintenance SHALL keep FlowGuard-kernel adoption closure separate
from peer-owned OpenSpec changes and pre-existing dirty files.

#### Scenario: Peer OpenSpec work remains unclaimed
- **WHEN** a sibling OpenSpec change is in progress and has fresh task updates
- **THEN** this change does not mark, rewrite, or complete that sibling
  change's task list
- **AND** final local-git evidence distinguishes this change's files from
  peer-owned or pre-existing dirty files

### Requirement: Adoption closure requires current local acceptance evidence
Repository maintenance SHALL finish FlowGuard-kernel adoption closure only after
current OpenSpec, FlowGuard, background-regression, install-freshness, and local
git evidence are available.

#### Scenario: Final acceptance evidence is current
- **WHEN** this change's source edits are complete
- **THEN** strict OpenSpec validation passes
- **AND** focused runtime-owner tests pass
- **AND** FlowGuard model-test alignment and full diagnostic evidence pass for
  the touched surfaces
- **AND** background meta and capability FlowGuard checks have final log
  artifacts and successful exit files
- **AND** repository-owned install sync, install check, and freshness audit pass
- **AND** local git status is reported without hiding unrelated peer changes
