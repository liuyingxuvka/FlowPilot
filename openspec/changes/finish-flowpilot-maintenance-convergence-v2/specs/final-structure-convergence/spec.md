## MODIFIED Requirements

### Requirement: Local Install And Git Sync Complete The Change

Final structure convergence SHALL end with local installed FlowPilot freshness,
clean intended local git scope, and no extra local work branches after v2
maintenance convergence evidence is current.

#### Scenario: Final sync is complete

- **GIVEN** source changes under `skills/flowpilot` or repository-owned support
  scripts
- **WHEN** final validation completes
- **THEN** repository-owned install sync, install check, and installed freshness
  audit SHALL pass
- **AND** the local result SHALL be committed on `main`
- **AND** no tag, push, release, deployment, or binary package SHALL be
  performed unless explicitly requested.

#### Scenario: Git scope excludes unverified peer work

- **GIVEN** the shared worktree contains files not owned by the convergence
  pass
- **WHEN** local git is finalized
- **THEN** unverified peer-agent work SHALL either be integrated with direct
  evidence and staged intentionally
- **OR** remain unstaged and named in the final report.
