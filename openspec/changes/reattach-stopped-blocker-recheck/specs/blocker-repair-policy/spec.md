## MODIFIED Requirements

### Requirement: Stopped repair blockers do not loop through PM
FlowPilot PM `stop_for_user` blockers SHALL remain hard user/Controller
decision waits during ordinary patrol/resume and SHALL NOT loop through PM
repair reissue unless the user explicitly requests a supported recovery
resolution.

#### Scenario: User requests recheck recovery after repair
- **WHEN** the user explicitly confirms that Controller or user repair has
  addressed the stopped blocker cause
- **THEN** FlowPilot may use `reattach_required_recheck` to issue the required
  owner recheck instead of reissuing another PM repair-decision packet.
