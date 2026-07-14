## REMOVED Requirements

### Requirement: Material Scan Phase Writes Stay Synchronized
**Reason**: The dedicated material-scan phase, event, packet family, and frontier state are retired from the single current contract. Keeping their synchronization requirement would preserve a second successful workflow.

**Migration**: PM reads ordinary non-sealed project files directly and uses the existing research or PM role-work packet/result/disposition path when additional evidence work is needed. Runtime shall reject the retired material events and actions without translation.
