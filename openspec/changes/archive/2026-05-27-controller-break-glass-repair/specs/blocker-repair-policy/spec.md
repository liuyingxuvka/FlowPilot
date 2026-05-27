## ADDED Requirements

### Requirement: Normal repair remains default before break-glass
FlowPilot SHALL keep PM/control-blocker/packet repair as the default recovery
path and SHALL allow Controller break-glass only after evidence shows the normal
control repair lane itself is unavailable, contradictory, looping, or unable to
produce a legal next action.

#### Scenario: Available PM repair blocks break-glass
- **WHEN** a control blocker can be delivered to the correct first handler or PM
  and a legal PM repair transaction can be recorded
- **THEN** Controller MUST NOT use break-glass and MUST follow the normal
  blocker repair policy

#### Scenario: Broken normal lane can trigger break-glass
- **WHEN** the control blocker or PM repair path is itself the failing mechanism,
  such as missing contract authority, impossible event authority, unavailable
  packet routing, or contradictory Router action state
- **THEN** Controller may open a break-glass incident instead of routing through
  the broken normal lane

#### Scenario: Break-glass does not resolve blocker by itself
- **WHEN** break-glass temporarily compensates for a FlowPilot control-plane
  defect
- **THEN** existing blockers, route gates, and repair transactions remain
  unresolved until the normal authorized flow can process or supersede them
