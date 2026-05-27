## ADDED Requirements

### Requirement: Foreground standby pruning preserves state-specific duties

Foreground Controller standby SHALL keep separate Controller-visible duties for
pending Controller work, wait-target check, wait-target blocker, wait-target
reissue, user input, daemon liveness check, terminal stop, and live daemon
watching even when internal branch logic is simplified.

#### Scenario: Wait-target states stay distinct

- **WHEN** standby detects reminder/liveness due, blocker required, or reissue
  required from controller-visible wait metadata
- **THEN** it returns the matching state-specific `foreground_required_mode`
  instead of collapsing all wait-target outcomes into one generic duty.

#### Scenario: Live daemon watching still blocks exit

- **WHEN** standby detects a live daemon with no ready Controller action and no
  wait-target duty
- **THEN** it reports a watch mode, keeps Controller attached, and does not
  authorize final foreground exit.
