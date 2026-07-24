## ADDED Requirements

### Requirement: Release readiness proves resource bounds and identity parity
A release that changes runtime persistence or validation evidence SHALL require
current resource-bounded FlowGuard evidence, focused and full TestMesh proof,
current authoritative model-system activation, clean consumer installation,
current SkillGuard maintenance closure, and equality of source commit, local
version, installed release identity, remote default branch, annotated tag, and
GitHub Release target.

#### Scenario: Frozen release candidate passes
- **WHEN** source, toolchain, owner inventory, version, model revision, and final validation plan are frozen and all required evidence passes
- **THEN** the clean FlowPilot consumer projection is installed and audited
- **AND** the published tag and GitHub Release resolve to the same commit and version as the installed projection

#### Scenario: SkillGuard changes during development
- **WHEN** the installed SkillGuard authority changes before FlowPilot maintenance begins
- **THEN** FlowPilot re-resolves the current SkillGuard source/version and freezes maintenance against that current identity
- **AND** stale SkillGuard evidence cannot authorize install or release
