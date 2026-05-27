## MODIFIED Requirements

### Requirement: Runtime modules have explicit owner boundaries
The FlowPilot runtime SHALL keep large behavior clusters behind compatibility
facades while moving cohesive implementation bodies into explicit owner modules.
Remaining owner modules above the current size budget SHOULD be split by
behavior family when their contents represent multiple independent debugging
surfaces.

#### Scenario: Remaining over-large owner is refined
- **WHEN** an owner module still mixes multiple behavior families after the
  prior runtime clarity pass
- **THEN** a follow-up polish pass may split it into focused child owners
- **AND** the original owner module remains as the compatibility facade unless
  public-entrypoint evidence proves no facade is needed.
