## ADDED Requirements

### Requirement: Final closure cannot repair skipped parent closure by fallback
FlowPilot final preflight SHALL require all effective parent/module closure
reviews to have been closed in normal frontier order before terminal return.
If a skipped or multi-gap parent closure state is detected, final preflight
SHALL hard-block rather than repair by fallback, old-state promotion, or
multi-review scheduling.

#### Scenario: Terminal replay waits for parent review absorption
- **WHEN** terminal backward replay or final-preflight is requested
- **AND** any effective parent/module node lacks accepted parent backward review
  evidence or PM absorption
- **THEN** FlowPilot SHALL block terminal/final closure
- **AND** FlowPilot SHALL expose only the current legal frontier action when the
  route has not advanced illegally

#### Scenario: Skipped parent closure is corruption
- **WHEN** final preflight discovers that downstream route work already
  advanced while an earlier parent/module closure review was missing
- **THEN** FlowPilot SHALL produce a hard control-plane blocker
- **AND** FlowPilot SHALL NOT auto-create compatibility review packets for the
  skipped parent/module nodes
